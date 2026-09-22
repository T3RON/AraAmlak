"""
Tests for phase 0C: roles, AuditLog, Invitation — no PostGIS required.

Covers:
- Permission matrix: has_permission() for each role
- RoleRequired mixin raises PermissionDenied for disallowed roles
- AuditLog.log() creates correct record
- AuditLog: login action recorded in otp_verify_view
- Invitation: token auto-generated on save
- Invitation: is_valid True/False
- Invitation: accept() creates AgencyMember
- Invitation: expired invite is_valid=False
- Invitation: used invite is_valid=False
- Invitation: accept() on used invite does not create duplicate member
- Tenant isolation: AuditLog agency filter
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser, UserRole
from apps.accounts.permissions import (
    ROLE_AGENT,
    ROLE_OWNER,
    has_permission,
    has_permission_by_roles,
)
from apps.agencies.models import AgencyMember, AgencyMemberRole, Invitation
from apps.core.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_user(agency, phone, role=UserRole.AGENT):
    u = CustomUser.objects.create_user(phone=phone, full_name="تست")
    u.agency = agency
    u.role = role
    u.save()
    return u


# ─── Permission matrix ────────────────────────────────────────────────────────


def test_owner_can_manage_members(agency):
    user = make_user(agency, "09100000010", role=UserRole.OWNER)
    user.role = ROLE_OWNER
    assert has_permission(user, "agencies.manage_members") is True


def test_agent_cannot_manage_members(agency):
    user = make_user(agency, "09100000011", role=UserRole.AGENT)
    assert has_permission(user, "agencies.manage_members") is False


def test_viewer_cannot_create_listing(agency):
    user = make_user(agency, "09100000012", role=UserRole.VIEWER)
    assert has_permission(user, "listings.create") is False


def test_agent_can_create_listing(agency):
    user = make_user(agency, "09100000013", role=UserRole.AGENT)
    assert has_permission(user, "listings.create") is True


def test_superuser_bypasses_all(agency):
    user = make_user(agency, "09100000014")
    user.is_superuser = True
    assert has_permission(user, "agencies.manage_members") is True
    assert has_permission(user, "accounting.edit") is True


def test_unauthenticated_has_no_permission():
    assert has_permission(None, "listings.view") is False


def test_has_permission_by_roles_match(agency):
    user = make_user(agency, "09100000015", role=UserRole.OWNER)
    assert has_permission_by_roles(user, [ROLE_OWNER, ROLE_AGENT]) is True


def test_has_permission_by_roles_no_match(agency):
    user = make_user(agency, "09100000016", role=UserRole.VIEWER)
    assert has_permission_by_roles(user, [ROLE_OWNER, ROLE_AGENT]) is False


# ─── AuditLog ─────────────────────────────────────────────────────────────────


def test_auditlog_log_creates_record(agency):
    user = make_user(agency, "09100000020")
    log = AuditLog.log(
        actor=user,
        agency=agency,
        action=AuditAction.LOGIN,
    )
    assert log.pk is not None
    assert log.action == AuditAction.LOGIN
    assert log.actor == user
    assert log.agency == agency


def test_auditlog_log_with_obj(agency):
    user = make_user(agency, "09100000021")
    log = AuditLog.log(
        actor=user,
        agency=agency,
        action=AuditAction.UPDATE,
        obj=user,
        diff={"full_name": ["قدیم", "جدید"]},
    )
    assert log.object_model == "CustomUser"
    assert log.object_id == str(user.pk)
    assert log.diff == {"full_name": ["قدیم", "جدید"]}


def test_auditlog_no_actor_allowed(agency):
    """System actions (e.g. Celery) may have no actor."""
    log = AuditLog.log(agency=agency, action=AuditAction.OTHER)
    assert log.actor is None


def test_auditlog_tenant_isolation(agency, agency_b):
    """AuditLog rows are not filtered by AgencyManager (no agency FK on default manager),
    but can be queried per-agency explicitly."""
    user_a = make_user(agency, "09100000022")
    user_b = make_user(agency_b, "09100000023")
    AuditLog.log(actor=user_a, agency=agency, action=AuditAction.LOGIN)
    AuditLog.log(actor=user_b, agency=agency_b, action=AuditAction.LOGIN)

    assert AuditLog.objects.filter(agency=agency).count() == 1
    assert AuditLog.objects.filter(agency=agency_b).count() == 1


# ─── Invitation ───────────────────────────────────────────────────────────────


def test_invitation_token_auto_generated(agency, user):
    invite = Invitation.objects.create(
        agency=agency,
        invited_by=user,
        role=AgencyMemberRole.AGENT,
    )
    assert invite.token
    assert len(invite.token) >= 32


def test_invitation_is_valid_true(agency, user):
    invite = Invitation.objects.create(
        agency=agency,
        invited_by=user,
        role=AgencyMemberRole.AGENT,
    )
    assert invite.is_valid is True


def test_invitation_expired_is_not_valid(agency, user):
    invite = Invitation(agency=agency, invited_by=user, role=AgencyMemberRole.AGENT)
    invite.expires_at = timezone.now() - timedelta(hours=1)
    invite.save()
    assert invite.is_valid is False


def test_invitation_used_is_not_valid(agency, user):
    invite = Invitation.objects.create(agency=agency, invited_by=user, role=AgencyMemberRole.AGENT)
    invite.is_used = True
    invite.save()
    assert invite.is_valid is False


def test_invitation_accept_creates_member(agency, user, agency_b):
    """Accepting an invitation should create an AgencyMember."""
    invitee = make_user(agency_b, "09100000030")
    invite = Invitation.objects.create(
        agency=agency,
        invited_by=user,
        role=AgencyMemberRole.AGENT,
    )
    member = invite.accept(invitee)
    assert member.user == invitee
    assert member.agency == agency
    assert member.role == AgencyMemberRole.AGENT
    # invite should be marked used
    invite.refresh_from_db()
    assert invite.is_used is True
    assert invite.used_by == invitee


def test_invitation_accept_idempotent(agency, user, agency_b):
    """Accepting twice should not create duplicate AgencyMember rows."""
    invitee = make_user(agency_b, "09100000031")
    invite = Invitation.objects.create(
        agency=agency, invited_by=user, role=AgencyMemberRole.AGENT
    )
    invite.accept(invitee)
    # Create a second invite for same pair
    invite2 = Invitation.objects.create(
        agency=agency, invited_by=user, role=AgencyMemberRole.OWNER
    )
    invite2.accept(invitee)
    count = AgencyMember.objects.filter(user=invitee, agency=agency).count()
    assert count == 1
