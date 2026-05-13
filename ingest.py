"""
Tender ingestion engine.
Pulls from:
  1. National Treasury OCDS API (ocds-api.etenders.gov.za)
  2. Tenders-SA.org RSS feeds
"""
import requests
import feedparser
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from sqlalchemy.orm import Session
from database import SessionLocal, Tender
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TenderDashboardBot/1.0)"
}

# ---------------------------------------------------------------------------
# National Treasury OCDS API
# ---------------------------------------------------------------------------
OCDS_BASE = "https://ocds-api.etenders.gov.za/api/OCDSReleases"

def fetch_ocds_releases(page=1, page_size=100, date_from=None, date_to=None):
    """Fetch a page of OCDS releases. Returns list of release dicts."""
    if date_from is None:
        date_from = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = datetime.utcnow().strftime("%Y-%m-%d")

    url = OCDS_BASE
    params = {
        "PageNumber": page,
        "PageSize": min(page_size, 1000),
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        print(f"[OCDS] GET page={page} -> {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("releases", [])
    except requests.exceptions.RequestException as e:
        print(f"[OCDS] Request failed: {e}")
        return []
    except Exception as e:
        print(f"[OCDS] Parse failed: {e}")
        return []

def normalize_ocds_release(release):
    """Map an OCDS release to our Tender model fields."""
    ocid = release.get("ocid", "")
    tender_obj = release.get("tender", {}) or {}
    buyer = release.get("buyer", {}) or {}
    value = tender_obj.get("value", {}) or {}
    dates = tender_obj.get("tenderPeriod", {}) or {}
    procuring = tender_obj.get("procuringEntity", {}) or {}

    published_raw = release.get("date", "")
    closing_raw = dates.get("endDate", "")
    published_dt = None
    closing_dt = None
    if published_raw:
        try:
            published_dt = date_parser.isoparse(published_raw)
        except Exception:
            pass
    if closing_raw:
        try:
            closing_dt = date_parser.isoparse(closing_raw)
        except Exception:
            pass

    buyer_name = buyer.get("name", "")
    if not buyer_name:
        buyer_name = procuring.get("name", "")

    amount = value.get("amount")
    if amount == 0:
        amount = None

    return {
        "ocid": ocid,
        "external_id": ocid,
        "title": (tender_obj.get("title") or "Untitled").strip(),
        "description": (tender_obj.get("description") or "").strip(),
        "buyer_name": (buyer_name or "").strip(),
        "buyer_id": buyer.get("id", ""),
        "status": (release.get("tag", [""])[0] if isinstance(release.get("tag"), list) else (release.get("tag") or "")).strip(),
        "tender_stage": (tender_obj.get("status") or "").strip(),
        "procurement_method": (tender_obj.get("procurementMethod") or "").strip(),
        "value_amount": amount,
        "value_currency": (value.get("currency") or "ZAR").strip(),
        "published_date": published_dt,
        "closing_date": closing_dt,
        "source_url": tender_obj.get("url", ""),
        "source_name": "National Treasury OCDS",
        "province": (tender_obj.get("province") or "").strip(),
        "category": (tender_obj.get("category") or "").strip(),
        "reference_number": (tender_obj.get("id") or "").strip(),
        "location": (tender_obj.get("deliveryLocation") or "").strip(),
    }

# ---------------------------------------------------------------------------
# Tenders-SA.org RSS feeds
# ---------------------------------------------------------------------------
TENDERS_SA_FEEDS = [
    "https://www.tenders-sa.org/rss/tenders/all",
]

def fetch_tenders_sa_feed(feed_url):
    """Parse an RSS feed and return list of tender dicts."""
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=30)
        print(f"[RSS] GET {feed_url} -> {resp.status_code}")
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        results = []
        for entry in feed.entries:
            pub_dt = None
            if hasattr(entry, "published"):
                try:
                    pub_dt = date_parser.parse(entry.published)
                except Exception:
                    pass

            # Parse description HTML for structured fields
            desc = entry.get("summary", "")
            province_match = re.search(r'<strong>Province:</strong>\s*([^<]+)', desc)
            ref_match = re.search(r'<strong>Reference:</strong>\s*([^<]+)', desc)
            closing_match = re.search(r'<strong>Closing Date:</strong>\s*([^<]+)', desc)

            province = (province_match.group(1).strip() if province_match else "")
            ref_num = (ref_match.group(1).strip() if ref_match else "")
            closing_dt = None
            if closing_match:
                try:
                    closing_dt = date_parser.parse(closing_match.group(1).strip())
                except Exception:
                    pass

            # Clean description: strip HTML tags
            clean_desc = re.sub(r'<[^>]+>', '', desc).strip()

            results.append({
                "ocid": "",
                "external_id": entry.get("id", entry.get("guid", "")),
                "title": (entry.get("title") or "Untitled").strip(),
                "description": clean_desc,
                "buyer_name": "",
                "buyer_id": "",
                "status": "tender",
                "tender_stage": "active",
                "procurement_method": "",
                "value_amount": None,
                "value_currency": "ZAR",
                "published_date": pub_dt,
                "closing_date": closing_dt,
                "source_url": entry.get("link", ""),
                "source_name": "Tenders-SA",
                "province": province,
                "category": "",
                "reference_number": ref_num,
                "location": province,
            })
        print(f"[RSS] Parsed {len(results)} items")
        return results
    except requests.exceptions.RequestException as e:
        print(f"[RSS] Failed {feed_url}: {e}")
        return []
    except Exception as e:
        print(f"[RSS] Parse error: {e}")
        return []

# ---------------------------------------------------------------------------
# DB write helpers
# ---------------------------------------------------------------------------
def upsert_tenders(db: Session, tenders: list):
    count_new = 0
    count_updated = 0
    for t in tenders:
        if not t["external_id"]:
            continue
        existing = db.query(Tender).filter(
            Tender.source_name == t["source_name"],
            Tender.external_id == t["external_id"],
        ).first()
        if existing:
            changed = False
            for key in ["title", "description", "status", "tender_stage", "value_amount",
                        "closing_date", "source_url", "province", "category", "buyer_name"]:
                new_val = t.get(key)
                if new_val is not None and getattr(existing, key) != new_val:
                    setattr(existing, key, new_val)
                    changed = True
            if changed:
                existing.updated_at = datetime.utcnow()
                count_updated += 1
        else:
            db.add(Tender(**t))
            count_new += 1
    db.commit()
    return count_new, count_updated

# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run_ingestion(ocds_pages=3, ocds_page_size=50, lookback_days=30):
    """Pull all configured sources and upsert."""
    db = SessionLocal()
    total_new = 0
    total_updated = 0

    try:
        # --- National Treasury OCDS ---
        print("\n=== OCDS Ingestion Start ===")
        date_to = datetime.utcnow().strftime("%Y-%m-%d")
        date_from = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        for page in range(1, ocds_pages + 1):
            releases = fetch_ocds_releases(
                page=page, page_size=ocds_page_size,
                date_from=date_from, date_to=date_to
            )
            if not releases:
                break
            tenders = [normalize_ocds_release(r) for r in releases]
            n, u = upsert_tenders(db, tenders)
            total_new += n
            total_updated += u
            print(f"  Page {page}: +{n} new, ~{u} updated")
            time.sleep(0.5)

        # --- Tenders-SA RSS ---
        print("\n=== Tenders-SA RSS Ingestion Start ===")
        for feed_url in TENDERS_SA_FEEDS:
            tenders = fetch_tenders_sa_feed(feed_url)
            n, u = upsert_tenders(db, tenders)
            total_new += n
            total_updated += u
            time.sleep(0.5)

        print(f"\n=== Done === Total new: {total_new}, updated: {total_updated}")

    finally:
        db.close()

if __name__ == "__main__":
    run_ingestion()
