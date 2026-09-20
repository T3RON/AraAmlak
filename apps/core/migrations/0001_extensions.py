"""
Initial data migration: enable PostgreSQL extensions.
PostGIS, pg_trgm, and unaccent are required by the project constitution.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Enable required PostgreSQL extensions."""

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE EXTENSION IF NOT EXISTS postgis;",
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
                "CREATE EXTENSION IF NOT EXISTS unaccent;",
            ],
            reverse_sql=[
                # Extensions are shared; do not drop them on reverse
                migrations.RunSQL.noop,
                migrations.RunSQL.noop,
                migrations.RunSQL.noop,
            ],
        ),
    ]
