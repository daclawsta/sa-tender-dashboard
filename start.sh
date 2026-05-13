#!/bin/bash
cd "$(dirname "$0")"
./venv/bin/python seed.py
./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload
