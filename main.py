"""
Entry point: ensures DB exists and starts the FastAPI server.
"""
from database import init_db
import uvicorn

if __name__ == "__main__":
    init_db()
    print("Starting Tender Dashboard on http://127.0.0.1:8080")
    uvicorn.run("api:app", host="127.0.0.1", port=8080, reload=False)
