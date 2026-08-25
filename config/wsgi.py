import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    try:
        from django.core.management import call_command
        from django.conf import settings
        from django.db import connection

        # Run migrations if tables do not exist
        if 'products_product' not in connection.introspection.table_names():
            call_command('migrate', interactive=False, verbosity=0)
            backup_file = Path(settings.BASE_DIR) / 'backup.json'
            if backup_file.exists():
                call_command('loaddata', str(backup_file), verbosity=0)
    except Exception as e:
        print("Vercel DB initialization error:", e)
