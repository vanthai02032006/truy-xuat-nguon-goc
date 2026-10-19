#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
    echo "Loi: thieu bien moi truong DATABASE_URL." >&2
    exit 1
fi

echo "Dang chay database migration..."

alembic upgrade head

echo "Migration thanh cong."
echo "Dang khoi dong FastAPI..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

