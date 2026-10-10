import os
import sys
from pathlib import Path

# Ensure project root is available on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.wsgi import application  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402

# Serverless startup hook for Vercel
# Ensures database tables and seed data exist on cold start (whether SQLite in /tmp or fresh Cloud Postgres)
if os.getenv("VERCEL"):
    try:
        tables = connection.introspection.table_names()
        if "accounts_user" not in tables:
            print("[Vercel Startup] Missing tables detected. Executing migrations...", file=sys.stderr)
            call_command("migrate", interactive=False)
            call_command("generate_sample_data", count=40)
            call_command("run_analytics_engine")
            print("[Vercel Startup] Database successfully initialized with demo records!", file=sys.stderr)
    except Exception as exc:
        print(f"[Vercel Startup] Database initialization warning: {exc}", file=sys.stderr)

app = application
