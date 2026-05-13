import sqlite3
import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")
RSS_URL = "https://www.tenders-sa.org/rss.xml"
OCDS_URL = "https://ocds-api.etenders.gov.za/api/releases"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_date(s):
    if not s: return None
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    try: return datetime.fromisoformat(s).strftime("%Y-%m-%d")
    except: return None

def fetch_rss():
    try:
        r = requests.get(RSS_URL, timeout=15, headers={"User-Agent":"SA-Tender-Dashboard/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        ns = {"content":"http://purl.org/rss/1.0/modules/content/"}
        for item in root.findall(".//item"):
            title = item.findtext("title","").strip()
            desc = item.findtext("description","").strip()
            link = item.findtext("link","").strip()
            pub_date = parse_date(item.findtext("pubDate",""))
            agency = "Tenders SA"
            cat = item.findtext("category","Other")
            ext_id = link.rstrip("/").split("/")[-1] if link else f"RSS-{hash(title)%100000:05d}"
            items.append({
                "external_id": f"RSS-{ext_id}",
                "title": title,
                "description": desc,
                "agency": agency,
                "status": "open",
                "value_amount": None,
                "value_currency": "AUD",
                "published_date": pub_date,
                "closing_date": None,
                "location": "South Australia",
                "category": cat,
                "source": "rss",
                "url": link
            })
        return items, None
    except Exception as e:
        return [], str(e)

def ingest_rss():
    items, err = fetch_rss()
    if err:
        print(f"RSS fetch error: {err}")
        return 0, err
    if not items:
        print("RSS fetch: no items found")
        return 0, None
    conn = get_db()
    c = conn.cursor()
    inserted = 0
    for t in items:
        c.execute("""
            INSERT OR IGNORE INTO tenders
            (external_id, title, description, agency, status, value_amount, value_currency,
             published_date, closing_date, location, category, source, url)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (t["external_id"], t["title"], t["description"], t["agency"], t["status"],
              t["value_amount"], t["value_currency"], t["published_date"],
              t["closing_date"], t["location"], t["category"], t["source"], t["url"]))
        if c.rowcount:
            inserted += 1
    conn.commit()
    conn.close()
    print(f"RSS ingestion: {inserted} new, {len(items)} total fetched.")
    return inserted, None

if __name__ == "__main__":
    inserted, err = ingest_rss()
    sys.exit(0 if not err else 1)
