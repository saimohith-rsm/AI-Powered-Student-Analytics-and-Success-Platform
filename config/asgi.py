import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()

try:
    from config.db_init import ensure_database_initialized
    ensure_database_initialized()
except Exception:
    pass
