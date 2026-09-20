"""
Initial data migration: enable PostgreSQL extensions.
PostGIS, pg_trgm, and unaccent are required by the project constitution.
Skipped automatically on non-PostgreSQL backends (e.g. SQLite in tests).
"""

from django.db import connection, migrations


def enable_extensions(apps, schema_editor):
    """Enable PostgreSQL-specific extensions. No-op on other backends."""
    if connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


class Migration(migrations.Migration):
    """Enable required PostgreSQL extensions."""

    initial = True
    dependencies = []

    operations = [
        migrations.RunPython(enable_extensions, migrations.RunPython.noop),
    ]
