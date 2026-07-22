import db
from models import BidItem


def make_conn(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    conn = db.connect()
    db.init_db(conn)
    return conn


def test_upsert_bids_deduplicates_by_municipality_and_source_id(tmp_path, monkeypatch):
    conn = make_conn(tmp_path, monkeypatch)
    item = BidItem(municipality="大阪府", source_id="abc", title="工事A", url="https://example.com/a")

    first_new = db.upsert_bids(conn, [item])
    second_new = db.upsert_bids(conn, [item])

    assert len(first_new) == 1
    assert len(second_new) == 0
    assert len(db.fetch_all_bids(conn)) == 1


def test_unnotified_flow(tmp_path, monkeypatch):
    conn = make_conn(tmp_path, monkeypatch)
    item = BidItem(municipality="大阪市", source_id="xyz", title="委託B", url="https://example.com/b")
    db.upsert_bids(conn, [item])

    unnotified = db.fetch_unnotified(conn)
    assert len(unnotified) == 1

    db.mark_notified(conn, [row["id"] for row in unnotified])

    assert db.fetch_unnotified(conn) == []
