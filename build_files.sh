#!/usr/bin/env bash
# Exit immediately on error
set -o errexit

echo "Installing runtime dependencies..."
python3 -m pip install -r requirements.txt

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# If a persistent database (Neon, Supabase) is provided via DATABASE_URL, run migrations at build time
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL detected. Applying migrations and seeding database..."
    python3 manage.py migrate --noinput
    python3 manage.py generate_sample_data --count 40
    python3 manage.py run_analytics_engine
fi

echo "Build complete."
