"""
No-GIS tests for CRM models and services.

Safe to run on Windows (SQLite) without PostGIS.
"""

import pytest

from apps.crm.models import Request, RequestPriority, RequestStatus
from apps.crm.services import close_request, create_request, update_request
from apps.listings.models import DealType


@pytest.mark.django_db
class TestRequestModel:
    def test_request_creation_defaults(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="علی رضایی",
            deal_type=DealType.SALE,
        )
        assert req.status == RequestStatus.NEW
        assert req.priority == RequestPriority.NORMAL
        assert req.property_types == []

    def test_str_representation(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="فاطمه محمدی",
            deal_type=DealType.RENT,
        )
        s = str(req)
        assert "فاطمه محمدی" in s
        assert "اجاره" in s

    def test_encrypted_client_phone(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="کاربر تست",
            deal_type=DealType.SALE,
            client_phone="09130000000",
        )
        fresh = Request.all_objects.get(pk=req.pk)
        assert fresh.client_phone == "09130000000"

    def test_property_types_json_field(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="کاربر تست",
            deal_type=DealType.SALE,
            property_types=["apartment", "villa"],
        )
        fresh = Request.all_objects.get(pk=req.pk)
        assert fresh.property_types == ["apartment", "villa"]


@pytest.mark.django_db
class TestRequestServices:
    def test_create_request_service(self, agency, user):
        req = create_request(
            agency=agency,
            data={
                "client_name": "رضا کریمی",
                "deal_type": DealType.MORTGAGE_RENT,
                "city": "مشهد",
                "max_budget": 5_000_000_000,
            },
            user=user,
        )
        assert req.pk is not None
        assert req.agency == agency
        assert req.city == "مشهد"
        assert req.assigned_to == user

    def test_update_request_service(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="سارا نجفی",
            deal_type=DealType.SALE,
        )
        update_request(req, {"city": "کرج", "priority": RequestPriority.HIGH})
        req.refresh_from_db()
        assert req.city == "کرج"
        assert req.priority == RequestPriority.HIGH

    def test_close_request_service(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="محمد علوی",
            deal_type=DealType.SALE,
        )
        close_request(req)
        req.refresh_from_db()
        assert req.status == RequestStatus.CLOSED
        assert req.closed_at is not None

    def test_cancel_request_service(self, agency):
        req = Request.all_objects.create(
            agency=agency,
            client_name="زهرا امیری",
            deal_type=DealType.RENT,
        )
        close_request(req, cancelled=True)
        req.refresh_from_db()
        assert req.status == RequestStatus.CANCELLED
