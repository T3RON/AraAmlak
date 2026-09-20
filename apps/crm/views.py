"""
CRM views — thin views that delegate to services.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.models import get_current_agency
from apps.crm.models import Request, RequestPriority, RequestStatus
from apps.crm.services import create_request, update_request


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
