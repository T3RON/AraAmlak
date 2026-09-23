"""
CRM views — thin views that delegate to services.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View

from apps.core.models import get_current_agency
from apps.crm.models import (
    Interaction,
    InteractionKind,
    Notification,
    Request,
    RequestPriority,
    RequestStatus,
    Task,
    Visit,
    VisitOutcome,
    VisitStatus,
)
from apps.crm.services import (
    add_interaction,
    complete_task,
    complete_visit,
    create_request,
    create_task,
    get_timeline,
    schedule_visit,
    update_request,
)


class RequestListView(LoginRequiredMixin, ListView):
    """فهرست درخواست‌های آژانس جاری."""

    model = Request
    template_name = "crm/list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        qs = Request.objects.select_related("assigned_to").order_by("-created_at")
        status = self.request.GET.get("status")
        deal_type = self.request.GET.get("deal_type")
        priority = self.request.GET.get("priority")
        if status:
            qs = qs.filter(status=status)
        if deal_type:
            qs = qs.filter(deal_type=deal_type)
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = RequestStatus.choices
        ctx["priority_choices"] = RequestPriority.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class RequestCreateView(LoginRequiredMixin, CreateView):
    """ثبت درخواست جدید."""

    model = Request
    template_name = "crm/form.html"
    fields = [
        "client_name", "client_phone", "source",
        "deal_type", "property_types",
        "min_area", "max_area", "min_rooms", "max_rooms",
        "city", "district", "min_budget", "max_budget", "notes",
        "status", "priority", "assigned_to", "contacted_at",
    ]
    success_url = reverse_lazy("crm:list")

    def form_valid(self, form):
        agency = get_current_agency()
        data = form.cleaned_data
        create_request(agency=agency, data=data, user=self.request.user)
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("ثبت درخواست جدید")
        return ctx


class RequestUpdateView(LoginRequiredMixin, UpdateView):
    """ویرایش درخواست."""

    model = Request
    template_name = "crm/form.html"
    fields = [
        "client_name", "client_phone", "source",
        "deal_type", "property_types",
        "min_area", "max_area", "min_rooms", "max_rooms",
        "city", "district", "min_budget", "max_budget", "notes",
        "status", "priority", "assigned_to", "contacted_at",
    ]
    success_url = reverse_lazy("crm:list")

    def get_queryset(self):
        return Request.objects.all()

    def form_valid(self, form):
        update_request(self.object, form.cleaned_data)
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("ویرایش درخواست")
        return ctx


# ─── Timeline (تایم‌لاین) ────────────────────────────────────────────────────────


class InteractionListView(LoginRequiredMixin, ListView):
    """تایم‌لاین تعاملات آژانس با فیلتر بر اساس نوع و شیء هدف."""

    model = Interaction
    template_name = "crm/timeline.html"
    context_object_name = "interactions"
    paginate_by = 30

    def get_queryset(self):
        qs = get_timeline(kind=self.request.GET.get("kind") or None)
        for key, field in (
            ("contact", "contact"),
            ("listing", "listing"),
            ("request", "request"),
        ):
            value = self.request.GET.get(key)
            if value:
                qs = qs.filter(**{f"{field}_id": value})
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kind_choices"] = InteractionKind.choices
        ctx["current_kind"] = self.request.GET.get("kind", "")
        return ctx


class InteractionCreateView(LoginRequiredMixin, View):
    """ثبت سریع یک رویداد تایم‌لاین (یادداشت / تماس) با POST."""

    def post(self, request):
        agency = get_current_agency()
        add_interaction(
            agency,
            request.user,
            request.POST.get("kind", InteractionKind.NOTE),
            contact=_opt_fk("crm.Contact", request.POST.get("contact")),
            listing=_opt_fk("listings.Listing", request.POST.get("listing")),
            request=_opt_fk("crm.Request", request.POST.get("crm_request")),  # noqa: S106
            summary=request.POST.get("summary", "").strip(),
            detail=request.POST.get("detail", ""),
        )
        return _back_or_timeline(request)


def _opt_fk(model_label: str, raw_id):
    """Resolve an optional POST id to a model instance (or None)."""
    if not raw_id:
        return None
    from django.apps import apps

    app_label, model_name = model_label.split(".")
    model = apps.get_model(app_label, model_name)
    return model.objects.filter(pk=raw_id).first()


def _back_or_timeline(request):
    target = request.POST.get("back") or request.GET.get("back")
    if target:
        return redirect(target)
    return redirect("crm:timeline")


# ─── Visit (بازدید) ─────────────────────────────────────────────────────────────


class VisitCreateView(LoginRequiredMixin, View):
    """ثبت قرار بازدید از یک فایل برای یک مخاطب."""

    def post(self, request):
        agency = get_current_agency()
        from apps.crm.models import Contact
        from apps.listings.models import Listing

        listing = get_object_or_404(Listing, pk=request.POST.get("listing"))
        contact = get_object_or_404(Contact, pk=request.POST.get("contact"))
        scheduled_at = request.POST.get("scheduled_at")
        crm_request = _opt_fk("crm.Request", request.POST.get("crm_request"))

        schedule_visit(
            agency,
            request.user,
            listing=listing,
            contact=contact,
            scheduled_at=scheduled_at,
            request=crm_request,
            note=request.POST.get("note", ""),
        )
        return redirect(request.POST.get("back") or "crm:timeline")


class VisitCompleteView(LoginRequiredMixin, View):
    """اتمام بازدید با ثبت نتیجه (HTMX inline)."""

    def post(self, request, pk: int):
        visit = get_object_or_404(Visit, pk=pk)
        complete_visit(
            visit,
            outcome=request.POST.get("outcome", VisitOutcome.NONE),
            note=request.POST.get("note", ""),
            status=request.POST.get("status", VisitStatus.COMPLETED),
        )
        if request.headers.get("HX-Request"):
            visit.refresh_from_db()
            return render(
                request, "crm/partials/visit_row.html", {"visit": visit}
            )
        return redirect(request.POST.get("back") or "crm:timeline")


# ─── Task (وظیفه) ───────────────────────────────────────────────────────────────


class TaskListView(LoginRequiredMixin, ListView):
    """فهرست وظایف با فیلتر وضعیت."""

    model = Task
    template_name = "crm/tasks.html"
    context_object_name = "tasks"
    paginate_by = 30

    def get_queryset(self):
        qs = Task.objects.select_related("assignee").order_by("due_at")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        else:
            qs = qs.filter(status="pending")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_status"] = self.request.GET.get("status", "pending")
        ctx["now"] = timezone.now()
        return ctx


class TaskCreateView(LoginRequiredMixin, View):
    """ثبت وظیفه جدید."""

    def post(self, request):
        agency = get_current_agency()
        from apps.accounts.models import CustomUser

        assignee = get_object_or_404(CustomUser, pk=request.POST.get("assignee"))
        due_at = request.POST.get("due_at")

        create_task(
            agency,
            request.user,
            title=request.POST.get("title", "").strip(),
            assignee=assignee,
            due_at=due_at,
            description=request.POST.get("description", ""),
            priority=request.POST.get("priority") or None,
            related_contact=_opt_fk("crm.Contact", request.POST.get("contact")),
            related_listing=_opt_fk("listings.Listing", request.POST.get("listing")),
            related_request=_opt_fk("crm.Request", request.POST.get("crm_request")),
        )
        return redirect(request.POST.get("back") or "crm:tasks")


@require_POST
def task_toggle_view(request, pk: int):
    """تغییر وضعیت وظیفه بین pending/done (HTMX)."""
    task = get_object_or_404(Task, pk=pk)
    complete_task(task, cancelled=request.POST.get("cancel") == "1")
    if request.headers.get("HX-Request"):
        task.refresh_from_db()
        return render(request, "crm/partials/task_row.html", {"task": task, "now": timezone.now()})
    return redirect("crm:tasks")


class MyDayView(LoginRequiredMixin, TemplateView):
    """صفحه «امروز من»: وظایف امروز، سررسیدشده‌ها و بازدیدهای امروز."""

    template_name = "crm/my_day.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        tasks = Task.objects.filter(assignee=user).select_related("assignee")
        ctx["overdue_tasks"] = tasks.filter(
            status="pending", due_at__lt=now
        ).order_by("due_at")
        ctx["today_tasks"] = tasks.filter(
            status="pending", due_at__gte=day_start, due_at__lte=now + timezone.timedelta(days=1)
        ).order_by("due_at")

        ctx["today_visits"] = (
            Visit.objects.filter(agent=user, scheduled_at__gte=day_start)
            .select_related("listing", "contact")
            .order_by("scheduled_at")[:10]
        )
        ctx["unread_notifications"] = Notification.objects.filter(user=user, is_read=False)[:5]
        return ctx


# ─── Notification (اعلان) ──────────────────────────────────────────────────────


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "crm/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related("user")


@require_POST
def notification_mark_read_view(request):
    """علامت‌گذاری همه اعلان‌ها به‌عنوان خوانده‌شده (HTMX)."""
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    if request.headers.get("HX-Request"):
        return HttpResponse(
            '<span id="notif-badge" class="badge badge-gray">۰</span>'
        )
    return redirect("crm:notifications")
