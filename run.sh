#!/usr/bin/env bash
# Run TAYYAR locally: http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"
PY=~/workspace/.venv-fc/bin/python
if ! "$PY" -c "import fastapi" 2>/dev/null; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  PY=.venv/bin/python
fi
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
