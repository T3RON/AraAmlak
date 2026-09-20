"""Matching app views — list matches for a CRM Request."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from apps.crm.models import Request
from apps.matching.models import Match


class RequestMatchListView(LoginRequiredMixin, DetailView):
    """
    نمایش لیست فایل‌های تطبیق‌یافته برای یک درخواست.

    URL: /matching/requests/<pk>/matches/
    """

    model = Request
    template_name = "matching/match_list.html"
    context_object_name = "crm_request"

    def get_queryset(self):
        return Request.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["matches"] = (
            Match.objects.filter(request=self.object)
            .select_related("listing")
            .order_by("-score")[:50]
        )
        return ctx
