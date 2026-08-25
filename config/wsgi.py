import os
import django
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    try:
        from django.core.management import call_command
        from django.conf import settings
        from django.contrib.auth import get_user_model

        # 1. Always run migrations first to create all tables (auth_group, auth_user, etc.)
        call_command('migrate', interactive=False, verbosity=0)

        # 2. Seed initial data if DB is empty
        try:
            from products.models import Product
            if not Product.objects.exists():
                backup_file = Path(settings.BASE_DIR) / 'backup.json'
                if backup_file.exists():
                    call_command('loaddata', str(backup_file), verbosity=0)
        except Exception as seed_err:
            print("Vercel DB seeding warning:", seed_err)

        # 3. Ensure superuser exists for admin access
        try:
            User = get_user_model()
            if not User.objects.filter(is_superuser=True).exists():
                admin_user = os.getenv('ADMIN_USERNAME', 'admin')
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
                admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                User.objects.create_superuser(admin_user, admin_email, admin_pass)
        except Exception as user_err:
            print("Vercel superuser creation warning:", user_err)

    except Exception as e:
        print("Vercel DB initialization error:", e)

application = get_wsgi_application()
