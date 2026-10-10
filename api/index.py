import os
import sys
from pathlib import Path

# Ensure project root is available on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.wsgi import application  # noqa: E402
from django.core.management import call_command  # noqa: E402

# Serverless startup hook for Vercel
# If keeping SQLite temporarily, automatically migrate and initialize tables on container cold start
if os.getenv("VERCEL") and not os.getenv("DATABASE_URL"):
    marker_file = "/tmp/.db_initialized"
    if not os.path.exists(marker_file):
        try:
            call_command("migrate", interactive=False)
            call_command("generate_sample_data", count=40)
            call_command("run_analytics_engine")
            with open(marker_file, "w") as f:
                f.write("ready")
        except Exception as exc:
            print(f"[Vercel Startup] Initialization failed: {exc}", file=sys.stderr)

app = application
