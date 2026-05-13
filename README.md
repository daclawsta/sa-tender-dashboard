# SA Tender Dashboard

A local dashboard for monitoring South Australian government tenders. FastAPI backend + vanilla HTML frontend + SQLite storage. Runs entirely offline with mock data; pluggable to live APIs when available.

## Quick start

```bash
cd /mnt/c/Users/User/Desktop/tender-dashboard
./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI (frontend.html) |
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

## Project files

| File | Purpose |
|---|---|
| `schema.sql` | SQLite schema |
| `mock_data.py` | 10 realistic SA tenders (fallback data) |
| `seed.py` | Creates DB and populates mock data |
| `api.py` | FastAPI backend |
| `frontend.html` | Dashboard UI (no build step) |
| `ingest_all.py` | Ingestion script: OCDS + RSS + mock fallback |
| `start.sh` | Convenience launch script |
| `tenders.db` | Live SQLite database |

## Ingestion / cron

A cron job polls for new tenders every hour:
- Tries OCDS API first
- Falls back to RSS
- Fails gracefully to mock data if both are down

Edit `RSS_URL` and `OCDS_URL` inside `ingest_all.py` to switch from mock to live sources.

## Stack

- Python 3.11 + FastAPI + Uvicorn
- SQLite (no separate server)
- Vanilla HTML / CSS / JS (no framework)

## Status

Currently running on mock data. Real API integration ready — update URLs in `ingest_all.py`.
