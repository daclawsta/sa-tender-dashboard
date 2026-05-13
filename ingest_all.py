"""South African eTenders ingestion — pulls real data from etenders.gov.za internal API"""
import sqlite3
import os
import urllib.request
import json
from datetime import datetime
from urllib.parse import quote

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")
API_URL = "https://www.etenders.gov.za/Home/PaginatedTenderOpportunities"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_page(status=1, start=0, length=2000):
    """Fetch tenders from the internal DataTables API."""
    params = f"draw=1&start={start}&length={length}&search[value]=&status={status}&order[0][column]=0&order[0][dir]=asc"
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def parse_tender(item):
    """Convert API item to our schema."""
    docs = item.get("supportDocument", [])
    documents = json.dumps([
        {
            "title": d.get("fileName", ""),
            "url": f"https://www.etenders.gov.za/home/Download/?blobName={d.get('supportDocumentID')}{d.get('extension', '.pdf')}&downloadedFileName={quote(d.get('fileName', ''), safe='')}"
        }
        for d in docs if d.get("supportDocumentID")
    ]) if docs else None

    api_status = item.get("status", "").lower()
    status_map = {
        "published": "open",
        "active": "open",
        "complete": "closed",
        "cancelled": "cancelled",
        "awarded": "awarded",
    }
    status = status_map.get(api_status, "open")

    return {
        "external_id": str(item.get("tender_No", item.get("id", ""))),
        "title": item.get("description", "Untitled"),
        "description": item.get("conditions", ""),
        "agency": item.get("organ_of_State", item.get("department", "Unknown")),
        "status": status,
        "value_amount": None,  # Not provided by this API
        "value_currency": "ZAR",
        "published_date": item.get("date_Published", "")[:10] if item.get("date_Published") else None,
        "closing_date": item.get("closing_Date", "")[:10] if item.get("closing_Date") else None,
        "location": item.get("province", "South Africa"),
        "category": item.get("category", ""),
        "source": "etenders_web",
        "url": None,
        "documents": documents,
    }

def ingest_etenders():
    """Ingest all currently advertised tenders from eTenders.gov.za."""
    print(f"[{datetime.now().isoformat()}] Fetching eTenders data...")

    all_records = []
    # Status 1 = Currently Advertised (the main catalog)
    for status_code, label in [(1, "currently_advertised")]:
        print(f"  Status {status_code} ({label})...")
        start = 0
        while True:
            try:
                data = fetch_page(status=status_code, start=start, length=2000)
                records = data.get("data", [])
                if not records:
                    break
                all_records.extend(records)
                print(f"    start={start}, got {len(records)} (total: {len(all_records)})")
                if len(records) < 2000:
                    break
                start += len(records)
            except Exception as e:
                print(f"    Error: {e}")
                break

    # Deduplicate by tender_No
    seen = set()
    unique = []
    for item in all_records:
        tid = item.get("tender_No", item.get("id"))
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(item)

    print(f"\nTotal unique tenders: {len(unique)}")

    conn = get_db()
    c = conn.cursor()
    inserted = 0
    for item in unique:
        t = parse_tender(item)
        try:
            c.execute("""
                INSERT OR REPLACE INTO tenders
                (external_id, title, description, agency, status, value_amount, value_currency,
                 published_date, closing_date, location, category, source, url, documents)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                t["external_id"], t["title"], t["description"], t["agency"],
                t["status"], t["value_amount"], t["value_currency"],
                t["published_date"], t["closing_date"], t["location"],
                t["category"], t["source"], t["url"], t["documents"]
            ))
            inserted += 1
        except Exception as e:
            print(f"Insert error: {e}")

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    by_status = {row["status"]: row["cnt"] for row in c.execute("SELECT status, COUNT(*) as cnt FROM tenders GROUP BY status").fetchall()}
    conn.close()

    print(f"Inserted/updated: {inserted}")
    print(f"Total in DB: {total}")
    print(f"By status: {by_status}")
    return inserted

def run_ingestion():
    """Main entry point for cron job."""
    print(f"=== SA Tender Ingestion started at {datetime.now().isoformat()} ===")
    count = ingest_etenders()
    print(f"=== Done. {count} tenders processed ===")
    return count

if __name__ == "__main__":
    run_ingestion()
