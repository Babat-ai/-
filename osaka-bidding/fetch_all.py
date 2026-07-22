import logging
import sys
import time

import db
from scrapers import ALL_SCRAPERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 自治体サイトへの負荷を抑えるため、スクレイパー間に間隔を空ける
POLITE_DELAY_SECONDS = 2


def main() -> int:
    conn = db.connect()
    db.init_db(conn)

    total_new = 0
    failed = []
    for i, scraper in enumerate(ALL_SCRAPERS):
        if i > 0:
            time.sleep(POLITE_DELAY_SECONDS)
        name = f"{scraper.municipality}/{scraper.__class__.__name__}"
        try:
            items = scraper.fetch()
        except Exception:
            logger.exception("スクレイピング失敗: %s", name)
            failed.append(name)
            continue
        new_items = db.upsert_bids(conn, items)
        logger.info("%s: 取得%d件 / 新規%d件", name, len(items), len(new_items))
        total_new += len(new_items)

    conn.close()
    logger.info("合計新規件数: %d", total_new)
    if failed:
        logger.warning("失敗したスクレイパー: %s", ", ".join(failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
