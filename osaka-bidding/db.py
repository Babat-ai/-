import sqlite3
from pathlib import Path

from models import BidItem

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "bids.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def upsert_bids(conn: sqlite3.Connection, items: list[BidItem]) -> list[BidItem]:
    """案件を保存し、今回新たに検知した案件だけを返す（重複は無視）。"""
    new_items = []
    for item in items:
        cur = conn.execute(
            """
            INSERT INTO bids (municipality, source_id, title, url, category, announced_date, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (municipality, source_id) DO NOTHING
            """,
            (
                item.municipality,
                item.source_id,
                item.title,
                item.url,
                item.category,
                item.announced_date,
                item.deadline,
            ),
        )
        if cur.rowcount > 0:
            new_items.append(item)
    conn.commit()
    return new_items


def fetch_unnotified(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bids WHERE notified_at IS NULL ORDER BY municipality, announced_date"
    ).fetchall()


def mark_notified(conn: sqlite3.Connection, ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(
        f"UPDATE bids SET notified_at = datetime('now', 'localtime') WHERE id IN ({placeholders})",
        ids,
    )
    conn.commit()


def fetch_all_bids(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bids ORDER BY announced_date DESC, first_seen_at DESC"
    ).fetchall()
