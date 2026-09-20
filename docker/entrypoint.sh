#!/bin/sh
set -e

# Wait for postgres
echo "Waiting for database..."
while ! python -c "
import os, psycopg
try:
    psycopg.connect(os.environ.get('DATABASE_URL', ''))
    print('ok')
except Exception:
    exit(1)
" 2>/dev/null; do
  sleep 1
done
echo "Database ready."

# Run migrations
python manage.py migrate --noinput

exec "$@"
