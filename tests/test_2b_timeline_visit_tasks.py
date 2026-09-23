"""
Tests for phase 2B: Interaction timeline, Visit, Task, Notification.

Covers:
- Interaction: create, kind filter, at-least-one-target constraint, timeline ordering
- Visit: schedule creates Interaction, complete_visit sets outcome
- Task: create, complete, overdue detection
- Notification: create, mark-read, unread badge tag
- Celery beat: send_due_task_reminders idempotency (one reminder per task)
- Tenant isolation across all new models
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.crm.models import (
    Contact,
    ContactType,
    Interaction,
    InteractionKind,
    Notification,
    NotificationKind,
    Task,
    TaskStatus,
    Visit,
    VisitOutcome,
    VisitStatus,
)
from apps.crm.services import (
    add_interaction,
    complete_task,
    complete_visit,
    create_task,
    get_timeline,
    notify,
    schedule_visit,
)
from apps.listings.models import DealType, Listing

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_contact(agency, name="مراجعه‌کننده تست", **kwargs):
    defaults = {"agency": agency, "full_name": name, "contact_type": ContactType.BUYER}
    defaults.update(kwargs)
    return Contact.all_objects.create(**defaults)


def make_listing(agency, **kwargs):
    defaults = {
        "agency": agency,
        "code": "T-1001",
        "property_type": "apartment",
        "deal_type": DealType.SALE,
        "city": "تهران",
        "district": "سعادت‌آباد",
        "area": 120,
        "sale_price": 2_700_000_000,
    }
    defaults.update(kwargs)
    return Listing.all_objects.create(**defaults)


def make_task(agency, user, **kwargs):
    defaults = {
        "agency": agency,
        "title": "تماس پیگیری",
        "assignee": user,
        "due_at": timezone.now() + timedelta(days=1),
    }
    defaults.update(kwargs)
    return Task.all_objects.create(**defaults)


# ─── Interaction ──────────────────────────────────────────────────────────────


def test_interaction_created(agency, user):
    contact = make_contact(agency)
    it = add_interaction(
        agency, user, InteractionKind.NOTE, contact=contact, summary="یادداشت تست"
    )
    assert it.pk is not None
    assert it.kind == InteractionKind.NOTE
    assert it.performed_by == user
    assert it.contact == contact


def test_interaction_requires_a_target(agency, user):
    with pytest.raises(ValueError):
        add_interaction(agency, user, InteractionKind.NOTE, summary="بدون هدف")


def test_interaction_db_constraint_no_target(agency, user):
    """DB-level CheckConstraint must reject an interaction with no target FK."""
    it = Interaction(agency=agency, kind=InteractionKind.NOTE, summary="بدون هدف")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            it.save()


def test_interaction_str(agency, user):
    contact = make_contact(agency)
    it = add_interaction(
        agency, user, InteractionKind.CALL, contact=contact, summary="تماس تلفنی"
    )
    assert "تماس تلفنی" in str(it)


def test_get_timeline_filters_and_orders(agency, user):
    contact = make_contact(agency)
    old = add_interaction(
        agency, user, InteractionKind.CALL, contact=contact, summary="قدیمی",
        occurred_at=timezone.now() - timedelta(days=2),
    )
    new = add_interaction(
        agency, user, InteractionKind.SMS, contact=contact, summary="جدید"
    )
    result = list(get_timeline(contact=contact))
    assert result[0].pk == new.pk
    assert result[1].pk == old.pk

    only_calls = list(get_timeline(contact=contact, kind=InteractionKind.CALL))
    assert only_calls == [old]


# ─── Visit ────────────────────────────────────────────────────────────────────


def test_schedule_visit_creates_interaction(agency, user):
    listing = make_listing(agency)
    contact = make_contact(agency)
    when = timezone.now() + timedelta(days=1)

    visit, interaction = schedule_visit(
        agency, user, listing=listing, contact=contact, scheduled_at=when
    )

    assert visit.pk is not None
    assert visit.status == VisitStatus.SCHEDULED
    assert interaction is not None
    assert interaction.kind == InteractionKind.VISIT
    assert interaction.listing == listing
    assert interaction.contact == contact


def test_complete_visit_sets_outcome_and_timestamp(agency, user):
    listing = make_listing(agency)
    contact = make_contact(agency)
    visit, _ = schedule_visit(
        agency, user, listing=listing, contact=contact,
        scheduled_at=timezone.now() - timedelta(hours=1),
    )

    complete_visit(visit, outcome=VisitOutcome.INTERESTED, note="علاقه‌مند بود")

    visit.refresh_from_db()
    assert visit.status == VisitStatus.COMPLETED
    assert visit.completed_at is not None
    assert visit.outcome == VisitOutcome.INTERESTED
    assert "علاقه‌مند بود" in visit.note

    interactions = list(get_timeline(listing=listing, kind=InteractionKind.VISIT))
    assert len(interactions) == 2  # scheduled + completed


def test_visit_str(agency, user):
    listing = make_listing(agency)
    contact = make_contact(agency)
    visit, _ = schedule_visit(
        agency, user, listing=listing, contact=contact,
        scheduled_at=timezone.now() + timedelta(days=1),
    )
    assert "بازدید" in str(visit)


# ─── Task ──────────────────────────────────────────────────────────────────────


def test_create_task(agency, user):
    task = create_task(
        agency, user, title="پیگیری مشتری", assignee=user,
        due_at=timezone.now() + timedelta(days=2),
    )
    assert task.pk is not None
    assert task.status == TaskStatus.PENDING
    assert task.reminder_sent_at is None


def test_complete_task(agency, user):
    task = make_task(agency, user)
    complete_task(task)
    task.refresh_from_db()
    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None


def test_complete_task_cancelled(agency, user):
    task = make_task(agency, user)
    complete_task(task, cancelled=True)
    task.refresh_from_db()
    assert task.status == TaskStatus.CANCELLED


def test_task_str(agency, user):
    task = make_task(agency, user)
    assert "پیگیری" in str(task)


# ─── Notification ───────────────────────────────────────────────────────────────


def test_notify_creates_notification(agency, user):
    notif = notify(user, kind=NotificationKind.WARNING, title="تست اعلان", body="متن")
    assert notif.pk is not None
    assert notif.user == user
    assert notif.agency == agency
    assert notif.is_read is False


def test_notification_str(agency, user):
    notif = notify(user, title="تست اعلان")
    assert "تست اعلان" in str(notif)


def test_unread_badge_tag(agency, user):
    from apps.core.templatetags.core_tags import unread_notifications_badge

    notify(user, title="یک")
    notify(user, title="دو", )
    Notification.objects.filter(user=user, title="دو").update(is_read=True)

    ctx = {"user": user}
    assert unread_notifications_badge(ctx, user) == 1


# ─── Celery beat: due task reminders ─────────────────────────────────────────────


def test_send_due_task_reminders_idempotent(agency, user):
    from apps.crm.tasks import send_due_task_reminders

    overdue = make_task(
        agency, user, due_at=timezone.now() - timedelta(hours=2),
    )
    future = make_task(
        agency, user, title="آینده", due_at=timezone.now() + timedelta(days=2),
    )

    result1 = send_due_task_reminders.apply().get()
    assert result1["sent"] == 1

    overdue.refresh_from_db()
    assert overdue.reminder_sent_at is not None
    assert Notification.objects.filter(user=user).count() == 1

    # Second run must not re-send (idempotency guard).
    result2 = send_due_task_reminders.apply().get()
    assert result2["sent"] == 0
    assert Notification.objects.filter(user=user).count() == 1

    # Future task never gets a reminder.
    future.refresh_from_db()
    assert future.reminder_sent_at is None


# ─── Tenant isolation ─────────────────────────────────────────────────────────────


def test_tenant_isolation_interactions(agency, agency_b, user, user_b):
    contact_a = make_contact(agency)
    contact_b = make_contact(agency_b, name="مشتری ب")
    add_interaction(agency, user, InteractionKind.NOTE, contact=contact_a, summary="الف")
    add_interaction(agency_b, user_b, InteractionKind.NOTE, contact=contact_b, summary="ب")

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    assert Interaction.objects.count() == 1
    assert Interaction.objects.first().summary == "الف"
    set_current_agency(agency_b)
    assert Interaction.objects.count() == 1
    assert Interaction.objects.first().summary == "ب"


def test_tenant_isolation_visits(agency, agency_b, user, user_b):
    listing_a = make_listing(agency)
    listing_b = make_listing(agency_b, code="B-2002")
    contact_a = make_contact(agency)
    contact_b = make_contact(agency_b, name="مشتری ب")

    schedule_visit(
        agency, user, listing=listing_a, contact=contact_a,
        scheduled_at=timezone.now() + timedelta(days=1),
    )
    schedule_visit(
        agency_b, user_b, listing=listing_b, contact=contact_b,
        scheduled_at=timezone.now() + timedelta(days=1),
    )

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    assert Visit.objects.count() == 1
    set_current_agency(agency_b)
    assert Visit.objects.count() == 1


def test_tenant_isolation_tasks(agency, agency_b, user, user_b):
    make_task(agency, user)
    make_task(agency_b, user_b, title="وظیفه ب")

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    assert Task.objects.count() == 1
    set_current_agency(agency_b)
    assert Task.objects.count() == 1


def test_tenant_isolation_notifications(agency, agency_b, user, user_b):
    notify(user, title="الف")
    notify(user_b, title="ب")

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    assert Notification.objects.count() == 1
    assert Notification.objects.first().title == "الف"


# ─── Views ──────────────────────────────────────────────────────────────────────


class _AnonymousClient:
    """Minimal wrapper — we use Django test client directly in tests below."""


def test_timeline_view_lists_interactions(client, agency, user):
    client.force_login(user)
    contact = make_contact(agency)
    add_interaction(agency, user, InteractionKind.NOTE, contact=contact, summary="نمایش")

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    resp = client.get("/crm/timeline/")
    assert resp.status_code == 200
    assert "نمایش".encode() in resp.content


def test_task_toggle_htmx(client, agency, user):
    client.force_login(user)
    task = make_task(agency, user)

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    resp = client.post(
        f"/crm/tasks/{task.pk}/toggle/",
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    task.refresh_from_db()
    assert task.status == TaskStatus.DONE


def test_my_day_view(client, agency, user):
    client.force_login(user)
    make_task(agency, user, due_at=timezone.now() - timedelta(hours=1))

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    resp = client.get("/crm/my-day/")
    assert resp.status_code == 200
    assert "سررسیدشده".encode() in resp.content


def test_notifications_mark_read(client, agency, user):
    client.force_login(user)
    notify(user, title="خوانده نشده")

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    resp = client.post("/crm/notifications/mark-read/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert Notification.objects.filter(user=user, is_read=False).count() == 0


def test_visit_complete_view_htmx(client, agency, user):
    client.force_login(user)
    listing = make_listing(agency)
    contact = make_contact(agency)
    visit, _ = schedule_visit(
        agency, user, listing=listing, contact=contact,
        scheduled_at=timezone.now() - timedelta(hours=2),
    )

    from apps.core.models import set_current_agency

    set_current_agency(agency)
    resp = client.post(
        f"/crm/visits/{visit.pk}/complete/",
        data={"outcome": VisitOutcome.INTERESTED},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    visit.refresh_from_db()
    assert visit.status == VisitStatus.COMPLETED
    assert visit.outcome == VisitOutcome.INTERESTED


# ─── Migration sanity ─────────────────────────────────────────────────────────────


def test_makemigrations_no_pending_for_crm():
    """CRM schema must be in sync with its migrations."""
    from io import StringIO

    out = StringIO()
    try:
        call_command("makemigrations", "crm", "--check", "--dry-run", stdout=out, stderr=out)
    except SystemExit:
        pass
    output = out.getvalue()
    assert "No changes detected" in output, output
