# SA Tender Dashboard

A local dashboard for monitoring **South African** government tenders via the National Treasury eTenders OCDS API.

- **Backend:** FastAPI + SQLite
- **Frontend:** Vanilla HTML/CSS/JS (no build step)
- **Data source:** Real-time OCDS API from `ocds-api.etenders.gov.za`

## Quick start

```bash
cd /mnt/c/Users/User/Desktop/tender-dashboard
./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## How it works

1. `ingest_all.py` fetches releases from the SA eTenders OCDS API (last 90 days)
2. Data is normalised and stored in SQLite (`tenders.db`)
3. FastAPI serves search/filter/sort endpoints
4. Frontend renders a responsive table with pagination

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI |
| `GET /api/stats` | Total counts by status and agency |
| `GET /api/tenders` | List, search, filter, sort, paginate |

### Query parameters for `/api/tenders`

- `q` — search title, description, agency
- `status` — `open` / `closed` / `awarded` / `cancelled`
- `agency` — partial match
- `category` — partial match
- `page` — default 1
- `per_page` — default 10, max 100
- `sort_by` — `closing_date` | `published_date` | `value_amount` | `title`
- `sort_order` — `asc` | `desc`

## Ingestion

Run manually:
```bash
./venv/bin/python ingest_all.py
```

Or schedule via cron (runs daily at 06:00):
```bash
0 6 * * * cd /mnt/c/Users/User/Desktop/tender-dashboard && ./venv/bin/python ingest_all.py
```

The ingestion script calls `https://ocds-api.etenders.gov.za/api/OCDSReleases` with `dateFrom` and `dateTo` parameters.

## Project files

| File | Purpose |
|---|---|
| `schema.sql` | SQLite schema |
| `api.py` | FastAPI backend |
| `frontend.html` | Dashboard UI |
| `ingest_all.py` | OCDS API ingestion |
| `seed.py` | Initialises empty DB |
| `tenders.db` | Live SQLite database |

## Stack

- Python 3.11 + FastAPI + Uvicorn
- SQLite (no separate server)
- Vanilla HTML / CSS / JS

## Data source

National Treasury eTenders Portal: https://data.etenders.gov.za  
OCDS API Swagger: https://ocds-api.etenders.gov.za/swagger/index.html
