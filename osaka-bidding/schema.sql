CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    municipality TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    category TEXT,
    announced_date TEXT,
    deadline TEXT,
    first_seen_at TEXT DEFAULT (datetime('now', 'localtime')),
    notified_at TEXT,
    UNIQUE (municipality, source_id)
);

CREATE INDEX IF NOT EXISTS idx_bids_notified_at ON bids (notified_at);
CREATE INDEX IF NOT EXISTS idx_bids_municipality ON bids (municipality);
