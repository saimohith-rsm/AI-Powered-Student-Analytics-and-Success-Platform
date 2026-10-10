import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
app = application

try:
    from config.db_init import ensure_database_initialized
    ensure_database_initialized()
except Exception:
    pass
