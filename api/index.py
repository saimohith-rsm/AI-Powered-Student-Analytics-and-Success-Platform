import os
import sys
from pathlib import Path

# Ensure project root is available on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.wsgi import application  # noqa: E402
from config.db_init import ensure_database_initialized  # noqa: E402

ensure_database_initialized()

app = application
