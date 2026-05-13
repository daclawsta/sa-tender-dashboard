import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r") as f:
        c.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
