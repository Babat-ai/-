import html
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import db

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "osaka-bidding"

JST = timezone(timedelta(hours=9))

PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大阪府 入札情報ダッシュボード</title>
<style>
  body {{ font-family: -apple-system, "Hiragino Sans", sans-serif; margin: 0; padding: 1.5rem; background: #f7f7f8; color: #1a1a1a; }}
  h1 {{ font-size: 1.3rem; margin-bottom: 0.25rem; }}
  .updated {{ color: #666; font-size: 0.85rem; margin-bottom: 1rem; }}
  .controls {{ margin-bottom: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }}
  input, select {{ padding: 0.4rem 0.6rem; border: 1px solid #ccc; border-radius: 6px; font-size: 0.9rem; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  th, td {{ text-align: left; padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
  th {{ background: #eef0f4; position: sticky; top: 0; }}
  tr:hover {{ background: #fafafa; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .muni-tag {{ display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; background: #e5e7eb; font-size: 0.75rem; }}
  .empty {{ padding: 2rem; text-align: center; color: #888; }}
</style>
</head>
<body>
<h1>大阪府 入札情報ダッシュボード</h1>
<p class="updated">最終更新: {updated_at} / 全{count}件</p>
<div class="controls">
  <input type="search" id="search" placeholder="案件名で検索">
  <select id="muni-filter">
    <option value="">全自治体</option>
    {muni_options}
  </select>
</div>
<table id="bids-table">
<thead>
<tr><th>自治体</th><th>案件名</th><th>区分</th><th>公告日</th><th>締切</th></tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<div id="empty" class="empty" style="display:none">該当する案件がありません</div>
<script>
const search = document.getElementById('search');
const muniFilter = document.getElementById('muni-filter');
const rows = Array.from(document.querySelectorAll('#bids-table tbody tr'));
const empty = document.getElementById('empty');

function applyFilter() {{
  const q = search.value.trim().toLowerCase();
  const muni = muniFilter.value;
  let visible = 0;
  for (const row of rows) {{
    const title = row.dataset.title;
    const rowMuni = row.dataset.muni;
    const match = (!q || title.includes(q)) && (!muni || rowMuni === muni);
    row.style.display = match ? '' : 'none';
    if (match) visible++;
  }}
  empty.style.display = visible === 0 ? 'block' : 'none';
}}
search.addEventListener('input', applyFilter);
muniFilter.addEventListener('change', applyFilter);
</script>
</body>
</html>
"""

ROW_TEMPLATE = """<tr data-title="{title_lower}" data-muni="{municipality}">
<td><span class="muni-tag">{municipality}</span></td>
<td><a href="{url}" target="_blank" rel="noopener">{title}</a></td>
<td>{category}</td>
<td>{announced_date}</td>
<td>{deadline}</td>
</tr>"""


def render(rows) -> str:
    municipalities = sorted({row["municipality"] for row in rows})
    muni_options = "\n    ".join(
        f'<option value="{html.escape(m)}">{html.escape(m)}</option>' for m in municipalities
    )
    row_html = "\n".join(
        ROW_TEMPLATE.format(
            title_lower=html.escape(row["title"].lower()),
            municipality=html.escape(row["municipality"]),
            url=html.escape(row["url"] or ""),
            title=html.escape(row["title"]),
            category=html.escape(row["category"] or ""),
            announced_date=html.escape(row["announced_date"] or ""),
            deadline=html.escape(row["deadline"] or ""),
        )
        for row in rows
    )
    updated_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    return PAGE_TEMPLATE.format(
        updated_at=updated_at, count=len(rows), muni_options=muni_options, rows=row_html
    )


def main() -> int:
    conn = db.connect()
    rows = db.fetch_all_bids(conn)
    conn.close()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "index.html").write_text(render(rows), encoding="utf-8")
    print(f"dashboard: {len(rows)}件を {OUTPUT_DIR / 'index.html'} に出力しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
