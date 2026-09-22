"""
Tests for phase 2A: Contact, ContactPhone, ConsentRecord, Request (extended).

Covers:
- Contact: create, __str__, tenant isolation
- ContactPhone: linked to Contact
- Contact.merge_into(): reassigns requests and phones, soft-deletes source
- ConsentRecord: created, is_active=True
- ConsentRecord.revoke(): sets revoked_at, is_active=False
- ConsentRecord: append-only (revoke does not delete)
- Request: auto expires_at in 60 days
- Request.contact FK: optional link
- Request tenant isolation (existing)
"""

import pytest
from django.utils import timezone

from apps.crm.models import (
    ConsentRecord,
    ConsentSource,
    Contact,
    ContactPhone,
    ContactType,
    PhoneLabel,
    Request,
    RequestStatus,
)
from apps.listings.models import DealType

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_contact(agency, name="علی رضایی", **kwargs):
    defaults = {"agency": agency, "full_name": name, "contact_type": ContactType.BUYER}
    defaults.update(kwargs)
    return Contact.all_objects.create(**defaults)


def make_request(agency, contact=None, **kwargs):
    defaults = {
        "agency": agency,
        "client_name": "مشتری تست",
        "deal_type": DealType.SALE,
        "status": RequestStatus.NEW,
        "priority": "normal",
    }
    if contact:
        defaults["contact"] = contact
    defaults.update(kwargs)
    return Request.all_objects.create(**defaults)


# ─── Contact ──────────────────────────────────────────────────────────────────


def test_contact_created(agency):
    c = make_contact(agency)
    assert c.pk is not None
    assert "علی رضایی" in str(c)


def test_contact_type_display(agency):
    c = make_contact(agency, contact_type=ContactType.OWNER)
    assert "مالک" in str(c)


def test_contact_phone_normalized_field(agency):
    make_contact(agency, phone_normalized="09123456789")
    assert Contact.all_objects.filter(phone_normalized="09123456789").exists()


def test_contact_tenant_isolation(agency, agency_b):
    from apps.core.models import set_current_agency
    make_contact(agency, name="کاربر الف")
    make_contact(agency_b, name="کاربر ب")

    set_current_agency(agency)
    try:
        assert Contact.objects.count() == 1
        assert Contact.objects.first().full_name == "کاربر الف"
    finally:
        set_current_agency(None)


# ─── ContactPhone ─────────────────────────────────────────────────────────────


def test_contact_phone_created(agency):
    c = make_contact(agency)
    cp = ContactPhone.objects.create(
        contact=c,
        phone="09123456789",
        phone_normalized="09123456789",
        label=PhoneLabel.MOBILE,
        is_primary=True,
    )
    assert cp.pk is not None
    assert c.phones.count() == 1


def test_contact_phone_str(agency):
    c = make_contact(agency)
    cp = ContactPhone.objects.create(
        contact=c, phone="09123456789", label=PhoneLabel.WORK
    )
    assert c.full_name in str(cp)


# ─── Contact.merge_into() ─────────────────────────────────────────────────────


def test_merge_into_reassigns_requests(agency):
    source = make_contact(agency, name="منبع")
    target = make_contact(agency, name="هدف")
    req = make_request(agency, contact=source)

    source.merge_into(target)

    req.refresh_from_db()
    assert req.contact == target

    source.refresh_from_db()
    assert source.is_active is False
    assert source.merged_into == target


def test_merge_into_reassigns_phones(agency):
    source = make_contact(agency)
    target = make_contact(agency, name="هدف")
    ContactPhone.objects.create(contact=source, phone="09111111111")

    source.merge_into(target)

    assert ContactPhone.objects.filter(contact=target).count() == 1
    assert ContactPhone.objects.filter(contact=source).count() == 0


def test_merge_into_reassigns_consents(agency):
    source = make_contact(agency)
    target = make_contact(agency, name="هدف")
    ConsentRecord.objects.create(
        contact=source,
        agency=agency,
        source=ConsentSource.IN_PERSON,
    )

    source.merge_into(target)

    assert ConsentRecord.objects.filter(contact=target).count() == 1


# ─── ConsentRecord ────────────────────────────────────────────────────────────


def test_consent_created(agency):
    c = make_contact(agency)
    consent = ConsentRecord.objects.create(
        contact=c,
        agency=agency,
        source=ConsentSource.IN_PERSON,
    )
    assert consent.pk is not None
    assert consent.is_active is True


def test_consent_revoke_sets_revoked_at(agency):
    c = make_contact(agency)
    consent = ConsentRecord.objects.create(
        contact=c, agency=agency, source=ConsentSource.IN_PERSON
    )
    consent.revoke("درخواست شخصی")

    consent.refresh_from_db()
    assert consent.revoked_at is not None
    assert consent.is_active is False
    assert "درخواست شخصی" in consent.revoke_reason


def test_consent_revoke_does_not_delete(agency):
    c = make_contact(agency)
    consent = ConsentRecord.objects.create(
        contact=c, agency=agency, source=ConsentSource.IN_PERSON
    )
    consent.revoke()
    assert ConsentRecord.objects.filter(pk=consent.pk).exists()


def test_consent_revoke_idempotent(agency):
    """Revoking twice should not change revoked_at."""
    c = make_contact(agency)
    consent = ConsentRecord.objects.create(
        contact=c, agency=agency, source=ConsentSource.IN_PERSON
    )
    consent.revoke()
    first_revoked_at = consent.revoked_at
    consent.revoke()  # second call
    assert consent.revoked_at == first_revoked_at


# ─── Request (extended) ───────────────────────────────────────────────────────


def test_request_auto_expires_at(agency):
    """expires_at should be set automatically to ~60 days from now."""
    req = make_request(agency)
    assert req.expires_at is not None
    delta = req.expires_at - timezone.now()
    assert 58 < delta.days <= 60


def test_request_contact_fk(agency):
    c = make_contact(agency)
    req = make_request(agency, contact=c)
    assert req.contact == c
    assert c.requests.count() == 1


def test_request_contact_optional(agency):
    """Request can be created without a contact (legacy flow)."""
    req = make_request(agency)
    assert req.contact is None
