#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
    echo "Loi: thieu bien moi truong DATABASE_URL." >&2
    exit 1
fi

echo "Dang chay database migration (alembic upgrade head)..."
alembic upgrade head
echo "Database migration thanh cong."

echo "Dang khoi dong FastAPI uvicorn tren port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

