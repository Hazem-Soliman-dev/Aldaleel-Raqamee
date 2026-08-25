from django.db import migrations


class Migration(migrations.Migration):
    """
    Drops the three Django auth tables that are only used by the Group system.
    We do not use Groups anywhere in this project.

    Tables removed:
      - auth_user_groups        (M2M: User ↔ Group)
      - auth_group_permissions  (M2M: Group ↔ Permission)
      - auth_group              (the Group model itself)
    """

    dependencies = [
        # Ensure all built-in auth migrations are applied first
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS auth_user_groups;
                DROP TABLE IF EXISTS auth_group_permissions;
                DROP TABLE IF EXISTS auth_group;
            """,
            reverse_sql="""
                CREATE TABLE IF NOT EXISTS auth_group (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(150) NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS auth_group_permissions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id      INTEGER NOT NULL REFERENCES auth_group(id),
                    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
                    UNIQUE (group_id, permission_id)
                );
                CREATE TABLE IF NOT EXISTS auth_user_groups (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id  INTEGER NOT NULL REFERENCES auth_user(id),
                    group_id INTEGER NOT NULL REFERENCES auth_group(id),
                    UNIQUE (user_id, group_id)
                );
            """,
        ),
    ]
