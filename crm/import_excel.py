import re
from datetime import date, datetime, timedelta

EXCLUDE_NAMES = {"家賃"}
ITEM_NAME = "月次売上"
IMPORT_MEMO = "Excel取込"


def _excel_serial_to_ym(n):
    d = datetime(1899, 12, 30) + timedelta(days=n)
    return d.year, d.month


def _parse_month_header(v):
    if isinstance(v, (int, float)):
        return _excel_serial_to_ym(v)
    if isinstance(v, str):
        m = re.match(r"(\d{2})年\s*(\d{1,2})月", v)
        if m:
            return 2000 + int(m.group(1)), int(m.group(2))
    return None


def parse_sheet(ws):
    header = [ws.cell(row=5, column=c).value for c in range(1, 21)]
    months = []
    for i in range(2, 14):
        ym = _parse_month_header(header[i])
        if ym:
            months.append((i + 1, ym[0], ym[1]))
    if len(months) != 12:
        raise ValueError(f"「{ws.title}」: 月の列を12個認識できませんでした({len(months)}個)")

    start_row = None
    for r in range(6, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "担当者" and ws.cell(row=r, column=2).value is None:
            start_row = r + 1
            break
    if start_row is None:
        raise ValueError(f"「{ws.title}」: データ開始位置(「担当者」の行)が見つかりませんでした")

    rows = []
    current_parent = None
    for r in range(start_row, ws.max_row + 1):
        person = ws.cell(row=r, column=1).value
        name = ws.cell(row=r, column=2).value
        biz_type = ws.cell(row=r, column=21).value
        if name is None:
            continue
        name = str(name).strip()
        if not name:
            continue
        if name in EXCLUDE_NAMES:
            if person is None:
                current_parent = None
            continue

        monthly_raw = [ws.cell(row=r, column=c).value for c, _, _ in months]
        monthly_map = {}
        for (_col, y, m), v in zip(months, monthly_raw):
            if isinstance(v, (int, float)) and v:
                monthly_map[(y, m)] = v

        if person is None:
            current_parent = name
            rows.append(
                {
                    "kind": "org",
                    "name": name,
                    "parent": None,
                    "person": None,
                    "biz_type": biz_type,
                    "monthly": monthly_map,
                }
            )
            continue

        person = str(person).strip()
        parent_for_row = None
        dept_name = name
        if current_parent and name.startswith(current_parent) and name != current_parent:
            parent_for_row = current_parent
            dept_name = name[len(current_parent):].strip()
        else:
            current_parent = None
        rows.append(
            {
                "kind": "leaf",
                "name": dept_name,
                "parent": parent_for_row,
                "person": person,
                "biz_type": biz_type,
                "monthly": monthly_map,
            }
        )
    return rows


def parse_workbook(wb):
    sheet_names = [n for n in wb.sheetnames if "売上" in n]
    if not sheet_names:
        raise ValueError("「売上」を含むシートが見つかりませんでした")
    all_rows = []
    for name in sheet_names:
        all_rows.extend(parse_sheet(wb[name]))
    return sheet_names, all_rows


def summarize(rows):
    customer_keys = set()
    sales_count = 0
    total_amount = 0
    for r in rows:
        customer_keys.add((r["name"], r["parent"]))
        sales_count += len(r["monthly"])
        total_amount += sum(r["monthly"].values())
    return {
        "customer_count": len(customer_keys),
        "sales_count": sales_count,
        "total_amount": total_amount,
    }


def import_rows(db, rows, today=None):
    today = today or date.today()
    cutoff = date(today.year, today.month, 1)
    stats = {
        "customers_created": 0,
        "customers_reused": 0,
        "sales_created": 0,
        "sales_skipped": 0,
        "total_amount": 0,
    }
    org_ids = {}

    def get_or_create_customer(name, parent_id, person, biz_type):
        existing = db.execute(
            "SELECT * FROM customers WHERE company_name = ? AND parent_id IS ?",
            (name, parent_id),
        ).fetchone()
        if existing:
            stats["customers_reused"] += 1
            if person and not existing["internal_rep"]:
                db.execute(
                    "UPDATE customers SET internal_rep = ? WHERE id = ?",
                    (person, existing["id"]),
                )
            return existing["id"]
        notes = f"業態: {biz_type}" if biz_type else ""
        cur = db.execute(
            "INSERT INTO customers (company_name, parent_id, internal_rep, notes) VALUES (?, ?, ?, ?)",
            (name, parent_id, person, notes),
        )
        stats["customers_created"] += 1
        return cur.lastrowid

    def add_sale(customer_id, year, month, amount):
        sale_date = f"{year:04d}-{month:02d}-01"
        existing = db.execute(
            "SELECT 1 FROM sales WHERE customer_id = ? AND sale_date = ? AND item_name = ?",
            (customer_id, sale_date, ITEM_NAME),
        ).fetchone()
        if existing:
            stats["sales_skipped"] += 1
            return
        status = "入金済み" if date(year, month, 1) <= cutoff else "見込み"
        db.execute(
            "INSERT INTO sales (customer_id, item_name, amount, status, sale_date, memo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (customer_id, ITEM_NAME, amount, status, sale_date, IMPORT_MEMO),
        )
        stats["sales_created"] += 1
        stats["total_amount"] += amount

    for r in rows:
        parent_id = org_ids.get(r["parent"]) if r["parent"] else None
        customer_id = get_or_create_customer(r["name"], parent_id, r["person"], r["biz_type"])
        if r["kind"] == "org":
            org_ids[r["name"]] = customer_id
        for (y, m), amount in r["monthly"].items():
            add_sale(customer_id, y, m, amount)

    db.commit()
    return stats
