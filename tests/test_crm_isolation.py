"""
Tenant isolation tests for CRM Requests — requires PostGIS/Docker.
"""

import pytest

from apps.core.models import set_current_agency
from apps.crm.models import Request
from apps.listings.models import DealType


@pytest.mark.django_db
class TestRequestTenantIsolation:
    def test_manager_filters_by_current_agency(self, agency, agency_b):
        r_a = Request.all_objects.create(
            agency=agency,
            client_name="مراجعه‌کننده آژانس الف",
            deal_type=DealType.SALE,
        )
        r_b = Request.all_objects.create(
            agency=agency_b,
            client_name="مراجعه‌کننده آژانس ب",
            deal_type=DealType.SALE,
        )

        set_current_agency(agency)
        try:
            pks = list(Request.objects.values_list("pk", flat=True))
            assert r_a.pk in pks
            assert r_b.pk not in pks
        finally:
            set_current_agency(None)

    def test_all_objects_bypasses_filter(self, agency, agency_b):
        r_a = Request.all_objects.create(
            agency=agency,
            client_name="مراجعه‌کننده الف",
            deal_type=DealType.RENT,
        )
        r_b = Request.all_objects.create(
            agency=agency_b,
            client_name="مراجعه‌کننده ب",
            deal_type=DealType.RENT,
        )

        set_current_agency(agency)
        try:
            pks = list(Request.all_objects.values_list("pk", flat=True))
            assert r_a.pk in pks
            assert r_b.pk in pks
        finally:
            set_current_agency(None)
