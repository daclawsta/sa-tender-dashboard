import sqlite3
import os
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "tenders.db")
app = FastAPI(title="SA Tender Dashboard API")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/tenders")
def list_tenders(
    q: Optional[str] = Query(None, description="Search title/description"),
    status: Optional[str] = Query(None, description="Filter by status: open/closed/awarded/cancelled"),
    agency: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: str = Query("closing_date", regex="^(closing_date|published_date|value_amount|title)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    conn = get_db()
    c = conn.cursor()
    where_clauses = ["1=1"]
    params = []
    if q:
        where_clauses.append("(title LIKE ? OR description LIKE ? OR agency LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if agency:
        where_clauses.append("agency LIKE ?")
        params.append(f"%{agency}%")
    if category:
        where_clauses.append("category LIKE ?")
        params.append(f"%{category}%")
    
    where_sql = " AND ".join(where_clauses)
    
    # Count total
    count_sql = f"SELECT COUNT(*) FROM tenders WHERE {where_sql}"
    total = c.execute(count_sql, params).fetchone()[0]
    
    # Fetch page
    order_sql = f"ORDER BY {sort_by} {sort_order.upper()}"
    offset = (page - 1) * per_page
    data_sql = f"SELECT * FROM tenders WHERE {where_sql} {order_sql} LIMIT ? OFFSET ?"
    params_page = list(params) + [per_page, offset]
    rows = c.execute(data_sql, params_page).fetchall()
    conn.close()
    
    results = [dict(row) for row in rows]
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results
    }

@app.get("/api/stats")
def stats():
    conn = get_db()
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    by_status = {row["status"]: row["cnt"] for row in c.execute("SELECT status, COUNT(*) as cnt FROM tenders GROUP BY status").fetchall()}
    by_agency = {row["agency"]: row["cnt"] for row in c.execute("SELECT agency, COUNT(*) as cnt FROM tenders GROUP BY agency").fetchall()}
    conn.close()
    return {"total": total, "by_status": by_status, "by_agency": by_agency}

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    path = os.path.join(os.path.dirname(__file__), "frontend.html")
    if os.path.exists(path):
        with open(path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not built yet</h1>")
