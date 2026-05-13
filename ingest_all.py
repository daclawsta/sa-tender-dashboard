import sqlite3
import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

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
        for item in root.findall(".//item"):
            title = item.findtext("title","").strip()
            desc = item.findtext("description","").strip()
            link = item.findtext("link","").strip()
            pub_date = parse_date(item.findtext("pubDate",""))
            cat = item.findtext("category","Other")
            ext_id = link.rstrip("/").split("/")[-1] if link else f"RSS-{abs(hash(title))%100000:05d}"
            items.append({
                "external_id": f"RSS-{ext_id}", "title": title, "description": desc,
                "agency": "Tenders SA", "status": "open", "value_amount": None,
                "value_currency": "AUD", "published_date": pub_date, "closing_date": None,
                "location": "South Australia", "category": cat, "source": "rss", "url": link
            })
        return items, None
    except Exception as e:
        return [], str(e)

def fetch_ocds():
    try:
        r = requests.get(OCDS_URL, params={"perPage":50}, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = []
        for rel in data.get("releases",[])[:50]:
            tender = rel.get("tender",{})
            val = tender.get("value",{})
            items.append({
                "external_id": rel.get("ocid",""),
                "title": tender.get("title","Untitled"),
                "description": tender.get("description",""),
                "agency": tender.get("procuringEntity",{}).get("name","SA Government"),
                "status": tender.get("status","open"),
                "value_amount": val.get("amount"),
                "value_currency": val.get("currency","AUD"),
                "published_date": rel.get("date","").split("T")[0] if rel.get("date") else None,
                "closing_date": None,
                "location": "South Australia",
                "category": tender.get("mainProcurementCategory","Other"),
                "source": "ocds",
                "url": tender.get("documents",[{}])[0].get("url","") if tender.get("documents") else ""
            })
        return items, None
    except Exception as e:
        return [], str(e)

def ingest():
    conn = get_db()
    c = conn.cursor()
    total_new = 0
    sources = [("RSS", fetch_rss), ("OCDS", fetch_ocds)]
    for name, fetcher in sources:
        items, err = fetcher()
        if err:
            print(f"{name} error: {err}")
            continue
        new = 0
        for t in items:
            c.execute("""
                INSERT OR IGNORE INTO tenders
                (external_id, title, description, agency, status, value_amount, value_currency,
                 published_date, closing_date, location, category, source, url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (t["external_id"], t["title"], t["description"], t["agency"], t["status"],
                  t["value_amount"], t["value_currency"], t["published_date"],
                  t["closing_date"], t["location"], t["category"], t["source"], t["url"]))
            if c.rowcount: new += 1
        total_new += new
        print(f"{name}: {new} new, {len(items)} fetched")
    conn.commit()
    conn.close()
    print(f"Total new tenders: {total_new}")
    return total_new

if __name__ == "__main__":
    ingest()
