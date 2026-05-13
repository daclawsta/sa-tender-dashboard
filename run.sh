#!/bin/bash
set -e
cd "$(dirname "$0")"
PYTHON=/home/daclawsta/tender-dashboard-venv/venv/bin/python3
echo "Ensuring database exists..."
$PYTHON database.py
echo "Running initial data ingestion (this may take a minute)..."
$PYTHON ingest.py
echo "Starting server on http://127.0.0.1:8080"
$PYTHON main.py
