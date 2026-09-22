"""
Listings views — thin views that delegate to services.

All views require login. Agency context injected by AgencyMiddleware.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.models import get_current_agency
from apps.listings.models import Listing, ListingStatus
from apps.listings.services import change_listing_status, create_listing, update_listing


class ListingListView(LoginRequiredMixin, ListView):
    """فهرست فایل‌های ملک آژانس جاری."""

    model = Listing
    template_name = "listings/list.html"
    context_object_name = "listings"
    paginate_by = 20

    def get_queryset(self):
        qs = Listing.objects.select_related("assigned_to", "branch").order_by("-created_at")
        # Filter by status / deal_type / property_type from GET params
        status = self.request.GET.get("status")
        deal_type = self.request.GET.get("deal_type")
        prop_type = self.request.GET.get("property_type")
        city = self.request.GET.get("city")
        if status:
            qs = qs.filter(status=status)
        if deal_type:
            qs = qs.filter(deal_type=deal_type)
        if prop_type:
            qs = qs.filter(property_type=prop_type)
        if city:
            qs = qs.filter(city__icontains=city)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = ListingStatus.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class ListingDetailView(LoginRequiredMixin, DetailView):
    """جزئیات یک فایل ملک."""

    model = Listing
    template_name = "listings/detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        return (
            Listing.objects
            .select_related("agency", "assigned_to", "branch")
            .prefetch_related("images", "media_files")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.listings.models import Media  # noqa: PLC0415
        ctx["media_list"] = Media.objects.filter(
            listing=self.object
        ).order_by("order", "created_at")
        return ctx


class ListingCreateView(LoginRequiredMixin, CreateView):
    """ثبت فایل ملک جدید."""

    model = Listing
    template_name = "listings/form.html"
    fields = [
        "property_type", "deal_type", "title",
        "province", "city", "district", "address",
        "area", "rooms", "floor", "total_floors", "build_year",
        "parking", "elevator", "storage", "direction",
        "sale_price", "mortgage_amount", "rent_amount", "price_negotiable",
        "owner_name", "owner_phone",
        "status", "assigned_to", "branch",
        "published_at", "expires_at",
    ]
    success_url = reverse_lazy("listings:list")

    def form_valid(self, form):
        agency = get_current_agency()
        data = form.cleaned_data
        create_listing(agency=agency, data=data, user=self.request.user)
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("ثبت فایل جدید")
        return ctx


class ListingUpdateView(LoginRequiredMixin, UpdateView):
    """ویرایش فایل ملک."""

    model = Listing
    template_name = "listings/form.html"
    fields = [
        "property_type", "deal_type", "title",
        "province", "city", "district", "address",
        "area", "rooms", "floor", "total_floors", "build_year",
        "parking", "elevator", "storage", "direction",
        "sale_price", "mortgage_amount", "rent_amount", "price_negotiable",
        "owner_name", "owner_phone",
        "status", "assigned_to", "branch",
        "published_at", "expires_at",
    ]

    def get_queryset(self):
        return Listing.objects.all()

    def get_success_url(self):
        return reverse_lazy("listings:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        update_listing(self.object, form.cleaned_data)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("ویرایش فایل")
        return ctx


def listing_status_update(request, pk):
    """
    HTMX endpoint: change listing status inline.
    POST /listings/<pk>/status/?status=<new_status>
    Returns a small HTML fragment.
    """
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    listing = get_object_or_404(Listing, pk=pk)
    new_status = request.POST.get("status", "")
    valid_statuses = [s[0] for s in ListingStatus.choices]
    if new_status in valid_statuses:
        change_listing_status(listing, new_status)

    # HTMX partial — return just the status badge
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    html = render_to_string(
        "listings/partials/status_badge.html",
        {"listing": listing},
        request=request,
    )
    return HttpResponse(html)
