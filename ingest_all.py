"""South African eTenders OCDS ingestion — pulls real data from etenders.gov.za"""
import sqlite3
import os
import urllib.request
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")
API_BASE = "https://ocds-api.etenders.gov.za/api/OCDSReleases"

# Bulk download portal (fallback if API is flaky)
BULK_PORTAL = "https://data.etenders.gov.za/Home/ReleasesFiles"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_ocds_releases(date_from: str, date_to: str, page: int = 1, page_size: int = 100):
    """Fetch releases from SA eTenders OCDS API.
    date_from and date_to must be YYYY-MM-DD strings.
    """
    url = f"{API_BASE}?PageNumber={page}&PageSize={page_size}&dateFrom={date_from}&dateTo={date_to}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)

def parse_ocds_to_tender(release: dict) -> dict | None:
    """Convert an OCDS release into our tender schema."""
    tender = release.get("tender", {})
    if not tender:
        return None

    period = tender.get("tenderPeriod", {})
    value = tender.get("value", {})
    procuring = tender.get("procuringEntity", {})

    # Try to parse dates
    closing = period.get("endDate", "")
    published = period.get("startDate", "")

    # Map OCDS status to our status enum
    ocds_status = tender.get("status", "")
    status_map = {
        "active": "open",
        "planned": "open",
        "complete": "closed",
        "cancelled": "cancelled",
        "unsuccessful": "closed",
    }
    status = status_map.get(ocds_status, "open")

    return {
        "external_id": release.get("ocid", "").replace("ocds-9t57fa-", ""),
        "title": tender.get("title", "Untitled"),
        "description": tender.get("description", ""),
        "agency": procuring.get("name", "Unknown"),
        "status": status,
        "value_amount": value.get("amount", 0),
        "value_currency": value.get("currency", "ZAR"),
        "published_date": published[:10] if published else None,
        "closing_date": closing[:10] if closing else None,
        "location": tender.get("province", "South Africa"),
        "category": tender.get("mainProcurementCategory", ""),
        "source": "ocds",
        "url": None,  # eTenders.gov.za SPA has no direct tender URLs
        "documents": json.dumps([
            {"title": d.get("title", ""), "url": d.get("url", "")}
            for d in tender.get("documents", [])
            if d.get("url")
        ]) if tender.get("documents") else None,
    }

def ingest_ocds(days_back: int = 90):
    """Ingest OCDS releases from the last N days."""
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"Fetching OCDS releases from {date_from} to {date_to}...")

    all_releases = []
    page = 1
    while True:
        try:
            data = fetch_ocds_releases(date_from, date_to, page=page, page_size=100)
            releases = data.get("releases", [])
            if not releases:
                break
            all_releases.extend(releases)
            print(f"  Page {page}: {len(releases)} releases (total so far: {len(all_releases)})")
            if len(releases) < 100:
                break
            page += 1
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    print(f"Total releases fetched: {len(all_releases)}")

    conn = get_db()
    c = conn.cursor()
    inserted = 0
    for rel in all_releases:
        t = parse_ocds_to_tender(rel)
        if not t:
            continue
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
                t["category"], t["source"], t["url"], t.get("documents")
            ))
            inserted += 1
        except Exception as e:
            print(f"  Insert error: {e}")
    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM tenders WHERE source='ocds'").fetchone()[0]
    conn.close()
    print(f"Inserted/updated: {inserted}. Total OCDS tenders in DB: {total}")
    return inserted

def run_ingestion():
    """Main entry point for cron job."""
    print(f"=== SA Tender Ingestion started at {datetime.now().isoformat()} ===")
    count = ingest_ocds(days_back=90)
    print(f"=== Done. {count} tenders processed ===")
    return count

if __name__ == "__main__":
    run_ingestion()
