#!/bin/sh
set -e

echo "Waiting for PostgreSQL database..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

echo "Applying database migrations..."
python manage.py migrate --no-input

exec "$@"
