"""Publishing app views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView

from apps.listings.models import Listing
from apps.publishing.models import PortalConfig, PublishJob


class ListingPublishJobListView(LoginRequiredMixin, DetailView):
    """
    نمایش لیست job‌های انتشار برای یک فایل ملک.

    URL: /publishing/listings/<pk>/jobs/
    """

    model = Listing
    template_name = "publishing/publish_job_list.html"
    context_object_name = "listing"

    def get_queryset(self):
        return Listing.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["jobs"] = (
            PublishJob.all_objects.filter(listing=self.object)
            .select_related("portal_config")
            .order_by("-created_at")[:50]
        )
        ctx["portal_configs"] = PortalConfig.objects.filter(is_active=True)
        return ctx


class PublishCreateView(LoginRequiredMixin, View):
    """
    ایجاد یک job انتشار و dispatch به Celery.

    POST: /publishing/listings/<pk>/publish/
    Body: portal_config_id
    """

    def post(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk)
        config_id = request.POST.get("portal_config_id")

        if not config_id:
            messages.error(request, "پورتال موردنظر را انتخاب کنید.")
            return redirect("publishing:job_list", pk=pk)

        config = get_object_or_404(PortalConfig, pk=config_id, is_active=True)

        from apps.publishing.tasks import publish_listing_task
        publish_listing_task.delay(listing.pk, config.pk)

        messages.success(
            request,
            f"درخواست انتشار در {config.get_portal_display()} ثبت شد.",
        )
        return redirect("publishing:job_list", pk=pk)
