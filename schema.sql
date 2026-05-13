-- tender-dashboard SQLite schema

CREATE TABLE IF NOT EXISTS tenders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    agency          TEXT,
    status          TEXT CHECK(status IN ('open','closed','cancelled','awarded')) DEFAULT 'open',
    value_amount    REAL,
    value_currency  TEXT DEFAULT 'AUD',
    published_date  TEXT,
    closing_date    TEXT,
    location        TEXT DEFAULT 'South Australia',
    category        TEXT,
    source          TEXT CHECK(source IN ('ocds','rss','manual','mock')) DEFAULT 'mock',
    url             TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_status ON tenders(status);
CREATE INDEX IF NOT EXISTS idx_closing ON tenders(closing_date);
CREATE INDEX IF NOT EXISTS idx_agency ON tenders(agency);
CREATE INDEX IF NOT EXISTS idx_category ON tenders(category);
