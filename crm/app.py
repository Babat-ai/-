import io
import secrets
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "customers.db"
SECRET_KEY_PATH = BASE_DIR / ".secret_key"

SALE_STATUSES = ["見込み", "受注", "請求済み", "入金済み"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Initial admin account, seeded into the users table on first run.
# Only the hash is stored here, never the plain-text password.
ADMIN_USERNAME = "babat7"
ADMIN_PASSWORD_HASH = (
    "scrypt:32768:8:1$DL27jBzevT4v2SiG$5015aa6ad58f09d73eba700fe7177df3c04b9552bb"
    "14cde76d26afb0b8a42502f65fc63df0b579cb5fe432db69b447ad1746d3d5d30962fce18902"
    "20a39aeed6"
)


def _load_secret_key():
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_text().strip()
    key = secrets.token_hex(32)
    SECRET_KEY_PATH.write_text(key)
    return key


app = Flask(__name__)
app.secret_key = _load_secret_key()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with open(BASE_DIR / "schema.sql") as f:
            db.executescript(f.read())
        db.commit()
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            db.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                (ADMIN_USERNAME, ADMIN_PASSWORD_HASH),
            )
            db.commit()


def _safe_next_url(url):
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return url_for("index")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user or not g.user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        db = get_db()
        g.user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if g.user is None:
            session.clear()
    if request.endpoint not in ("login", "static") and g.user is None:
        return redirect(url_for("login", next=request.path))


@app.context_processor
def inject_current_user():
    return {"current_user": g.get("user")}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form["username"],)
        ).fetchone()
        next_url = request.form.get("next", "")
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(_safe_next_url(next_url))
        return render_template(
            "login.html",
            error="ユーザー名またはパスワードが正しくありません。",
            next=next_url,
        ), 401
    return render_template("login.html", error=None, next=request.args.get("next", ""))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account", methods=["GET", "POST"])
def account():
    error = None
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        if not check_password_hash(g.user["password_hash"], current_password):
            error = "現在のパスワードが正しくありません。"
        elif not new_password:
            error = "新しいパスワードを入力してください。"
        elif new_password != confirm_password:
            error = "新しいパスワード(確認)が一致しません。"
        if error:
            return render_template("account.html", error=error)
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), g.user["id"]),
        )
        db.commit()
        flash("パスワードを変更しました。", "success")
        return redirect(url_for("account"))
    return render_template("account.html", error=None)


@app.route("/users")
@admin_required
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    return render_template("user_list.html", users=users)


@app.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    if request.method == "POST":
        db = get_db()
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        is_admin = 1 if request.form.get("is_admin") else 0
        error = None
        if not username or not password:
            error = "ユーザー名とパスワードを入力してください。"
        elif password != confirm_password:
            error = "パスワード(確認)が一致しません。"
        elif db.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone():
            error = "そのユーザー名は既に使われています。"
        if error:
            return render_template(
                "user_form.html", error=error, username=username, is_admin=is_admin
            )
        db.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), is_admin),
        )
        db.commit()
        flash("ユーザーを追加しました。", "success")
        return redirect(url_for("list_users"))
    return render_template("user_form.html", error=None, username="", is_admin=False)


@app.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    db = get_db()
    if user_id == g.user["id"]:
        flash("自分自身は削除できません。", "error")
        return redirect(url_for("list_users"))
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if target and target["is_admin"]:
        admin_count = db.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1"
        ).fetchone()[0]
        if admin_count <= 1:
            flash("最後の管理者は削除できません。", "error")
            return redirect(url_for("list_users"))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("ユーザーを削除しました。", "success")
    return redirect(url_for("list_users"))


@app.errorhandler(403)
def forbidden(exc):
    return render_template("error.html", message="この操作を行う権限がありません。"), 403


@app.route("/")
def index():
    db = get_db()
    customer_count = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sale_count = db.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    total_amount = db.execute("SELECT COALESCE(SUM(amount), 0) FROM sales").fetchone()[0]
    month_amount = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM sales "
        "WHERE strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now', 'localtime')"
    ).fetchone()[0]
    recent_sales = db.execute(
        "SELECT sales.*, customers.company_name FROM sales "
        "JOIN customers ON customers.id = sales.customer_id "
        "ORDER BY sales.sale_date DESC, sales.id DESC LIMIT 5"
    ).fetchall()
    monthly_sales = _monthly_chart_data(db)
    return render_template(
        "dashboard.html",
        customer_count=customer_count,
        sale_count=sale_count,
        total_amount=total_amount,
        month_amount=month_amount,
        recent_sales=recent_sales,
        monthly_sales=monthly_sales,
    )


@app.route("/customers")
def list_customers():
    db = get_db()
    customers = db.execute(
        "SELECT customers.*, COALESCE(SUM(sales.amount), 0) AS total_amount "
        "FROM customers LEFT JOIN sales ON sales.customer_id = customers.id "
        "GROUP BY customers.id ORDER BY customers.id DESC"
    ).fetchall()
    return render_template("customer_list.html", customers=customers)


@app.route("/customers/new", methods=["GET", "POST"])
def new_customer():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO customers (company_name, contact_name, email, phone, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                request.form["company_name"],
                request.form["contact_name"],
                request.form["email"],
                request.form["phone"],
                request.form["notes"],
            ),
        )
        db.commit()
        return redirect(url_for("list_customers"))
    return render_template("customer_form.html", customer=None)


@app.route("/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE customers SET company_name = ?, contact_name = ?, email = ?, "
            "phone = ?, notes = ? WHERE id = ?",
            (
                request.form["company_name"],
                request.form["contact_name"],
                request.form["email"],
                request.form["phone"],
                request.form["notes"],
                customer_id,
            ),
        )
        db.commit()
        return redirect(url_for("list_customers"))
    customer = db.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return render_template("customer_form.html", customer=customer)


@app.route("/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    db.commit()
    return redirect(url_for("list_customers"))


def _yearly_chart_data(rows):
    yearly_totals = {int(r["year"]): r["total"] for r in rows if r["year"]}
    if not yearly_totals:
        return []
    max_total = max(yearly_totals.values()) or 1
    return [
        {
            "year": year,
            "total": yearly_totals.get(year, 0),
            "pct": round(yearly_totals.get(year, 0) / max_total * 100),
        }
        for year in range(min(yearly_totals), max(yearly_totals) + 1)
    ]


def _monthly_chart_data(db, customer_id=None, months=12):
    query = "SELECT strftime('%Y-%m', sale_date) AS ym, SUM(amount) AS total FROM sales"
    params = []
    if customer_id is not None:
        query += " WHERE customer_id = ?"
        params.append(customer_id)
    query += " GROUP BY ym"
    totals = {r["ym"]: r["total"] for r in db.execute(query, params).fetchall()}

    today = date.today()
    keys = []
    year, month = today.year, today.month
    for i in range(months - 1, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        keys.append((y, m))

    max_total = max([totals.get(f"{y:04d}-{m:02d}", 0) for y, m in keys] + [0]) or 1
    return [
        {
            "label": f"{y % 100:02d}/{m}",
            "total": totals.get(f"{y:04d}-{m:02d}", 0),
            "pct": round(totals.get(f"{y:04d}-{m:02d}", 0) / max_total * 100),
        }
        for y, m in keys
    ]


def _sales_workbook(rows, sheet_title, include_customer):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]
    headers = ["日付", "案件名", "金額", "ステータス", "備考"]
    if include_customer:
        headers.insert(1, "顧客")
    ws.append(headers)
    total = 0
    for r in rows:
        total += r["amount"]
        row = [r["sale_date"], r["item_name"], r["amount"], r["status"], r["memo"]]
        if include_customer:
            row.insert(1, r["company_name"])
        ws.append(row)
    ws.append([])
    total_row = [""] * (len(headers) - 2) + ["合計", total]
    ws.append(total_row)
    for i in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20
    return wb


def _send_workbook(wb, filename):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename, mimetype=XLSX_MIME)


@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    db = get_db()
    customer = db.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    if customer is None:
        return redirect(url_for("list_customers"))
    sales = db.execute(
        "SELECT * FROM sales WHERE customer_id = ? ORDER BY sale_date DESC, id DESC",
        (customer_id,),
    ).fetchall()
    total_amount = sum(s["amount"] for s in sales)

    chart_view = request.args.get("chart", "yearly")
    if chart_view not in ("yearly", "monthly"):
        chart_view = "yearly"
    if chart_view == "monthly":
        chart_data = _monthly_chart_data(db, customer_id=customer_id)
    else:
        yearly_rows = db.execute(
            "SELECT strftime('%Y', sale_date) AS year, SUM(amount) AS total "
            "FROM sales WHERE customer_id = ? GROUP BY year ORDER BY year",
            (customer_id,),
        ).fetchall()
        chart_data = _yearly_chart_data(yearly_rows)

    return render_template(
        "customer_detail.html",
        customer=customer,
        sales=sales,
        total_amount=total_amount,
        chart_data=chart_data,
        chart_view=chart_view,
    )


@app.route("/customers/<int:customer_id>/export")
def export_customer_sales(customer_id):
    db = get_db()
    customer = db.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    if customer is None:
        return redirect(url_for("list_customers"))
    sales = db.execute(
        "SELECT * FROM sales WHERE customer_id = ? ORDER BY sale_date DESC, id DESC",
        (customer_id,),
    ).fetchall()
    wb = _sales_workbook(sales, sheet_title="売上履歴", include_customer=False)
    return _send_workbook(wb, f"{customer['company_name']}_売上.xlsx")


@app.route("/sales")
def list_sales():
    db = get_db()
    sales = db.execute(
        "SELECT sales.*, customers.company_name FROM sales "
        "JOIN customers ON customers.id = sales.customer_id "
        "ORDER BY sales.sale_date DESC, sales.id DESC"
    ).fetchall()
    total_amount = sum(s["amount"] for s in sales)
    return render_template("sale_list.html", sales=sales, total_amount=total_amount)


@app.route("/sales/export")
def export_sales():
    db = get_db()
    sales = db.execute(
        "SELECT sales.*, customers.company_name FROM sales "
        "JOIN customers ON customers.id = sales.customer_id "
        "ORDER BY sales.sale_date DESC, sales.id DESC"
    ).fetchall()
    wb = _sales_workbook(sales, sheet_title="売上一覧", include_customer=True)
    return _send_workbook(wb, "売上一覧.xlsx")


@app.route("/sales/new", methods=["GET", "POST"])
def new_sale():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO sales (customer_id, item_name, amount, status, sale_date, memo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form["customer_id"],
                request.form["item_name"],
                request.form["amount"],
                request.form["status"],
                request.form["sale_date"],
                request.form["memo"],
            ),
        )
        db.commit()
        return redirect(url_for("list_sales"))
    customers = db.execute("SELECT * FROM customers ORDER BY company_name").fetchall()
    selected_customer_id = request.args.get("customer_id", type=int)
    return render_template(
        "sale_form.html",
        sale=None,
        customers=customers,
        statuses=SALE_STATUSES,
        selected_customer_id=selected_customer_id,
    )


@app.route("/sales/edit/<int:sale_id>", methods=["GET", "POST"])
def edit_sale(sale_id):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE sales SET customer_id = ?, item_name = ?, amount = ?, "
            "status = ?, sale_date = ?, memo = ? WHERE id = ?",
            (
                request.form["customer_id"],
                request.form["item_name"],
                request.form["amount"],
                request.form["status"],
                request.form["sale_date"],
                request.form["memo"],
                sale_id,
            ),
        )
        db.commit()
        return redirect(url_for("list_sales"))
    sale = db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    customers = db.execute("SELECT * FROM customers ORDER BY company_name").fetchall()
    return render_template(
        "sale_form.html",
        sale=sale,
        customers=customers,
        statuses=SALE_STATUSES,
        selected_customer_id=sale["customer_id"] if sale else None,
    )


@app.route("/sales/delete/<int:sale_id>", methods=["POST"])
def delete_sale(sale_id):
    db = get_db()
    db.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    db.commit()
    return redirect(url_for("list_sales"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
