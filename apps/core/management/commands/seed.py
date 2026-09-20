"""
Management command: seed
Loads initial development data (safe fake data only — no real personal info).
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load initial development seed data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding development data...")
        # Phase 0A: no real models yet — placeholder
        # Future phases will add: Agency, CustomUser, etc.
        self.stdout.write(self.style.SUCCESS("Seed complete (phase 0A: no data yet)."))
