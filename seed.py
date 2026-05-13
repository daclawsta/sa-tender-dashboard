import sqlite3
import os
from mock_data import MOCK_TENDERS

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r") as f:
        c.executescript(f.read())
    conn.commit()
    conn.close()

def seed_mock():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tenders = []
    for t in MOCK_TENDERS:
        tenders.append((
            t["external_id"], t["title"], t["description"], t["agency"],
            t["status"], t["value_amount"], t["value_currency"],
            t["published_date"], t["closing_date"], t["location"],
            t["category"], t["source"], t["url"]
        ))
    c.executemany("""
        INSERT OR REPLACE INTO tenders
        (external_id, title, description, agency, status, value_amount, value_currency,
         published_date, closing_date, location, category, source, url)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, tenders)
    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    init_db()
    count = seed_mock()
    print(f"Database initialized: {count} tenders seeded.")
