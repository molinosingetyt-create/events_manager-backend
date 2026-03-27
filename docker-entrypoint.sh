#!/bin/sh
set -e
mkdir -p "${UPLOAD_DIR:-uploads}"
alembic upgrade head
python -m scripts.seed_admin || true
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
