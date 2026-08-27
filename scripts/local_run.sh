#!/usr/bin/env bash
# local_run.sh — one-shot local start (mock mode, zero AWS dependencies).
# Windows users: run the three commands manually in PowerShell:
#   py -3.11 -m venv .venv ; .\.venv\Scripts\Activate.ps1
#   python scripts\seed_demo.py
#   uvicorn app.main:app --reload --port 8000
set -euo pipefail
cd "$(dirname "$0")/.."

export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-mock}"
export VECTOR_STORE_PROVIDER="${VECTOR_STORE_PROVIDER:-local}"
export CACHE_PROVIDER="${CACHE_PROVIDER:-local}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./prometheus.db}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

python scripts/seed_demo.py
exec uvicorn app.main:app --reload --port 8000
