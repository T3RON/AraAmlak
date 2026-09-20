"""
Initial data migration: enable PostgreSQL extensions.
PostGIS, pg_trgm, and unaccent are required by the project constitution.

Uses RunPython with a connection.vendor check so it is a no-op on SQLite.
"""

from django.db import connection, migrations


def enable_extensions(apps, schema_editor):
    """Create PostgreSQL extensions if running on PostgreSQL."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


def noop_reverse(apps, schema_editor):
    """Do not drop extensions on reverse (they are shared cluster-wide)."""


class Migration(migrations.Migration):
    """Enable required PostgreSQL extensions."""

    initial = True
    dependencies = []

    operations = [
        migrations.RunPython(enable_extensions, reverse_code=noop_reverse),
    ]
