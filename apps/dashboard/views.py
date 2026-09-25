"""Dashboard views."""

import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from apps.core.models import get_current_agency


def _listings_by_status_chart(agency) -> list[dict]:
    """Donut chart: listings per status for the agency."""
    from apps.listings.models import Listing, ListingStatus

    rows = (
        Listing.all_objects.filter(agency=agency)
        .values("status")
        .annotate(n=Count("pk"))
    )
    counts = {row["status"]: row["n"] for row in rows}
    palette = {
        "active": ("#34c759", "فعال"),
        "draft": ("#0a84ff", "پیش‌نویس"),
        "reserved": ("#ff9500", "رزرو شده"),
        "sold": ("#8e8e93", "فروخته/اجاره"),
        "expired": ("#ff3b30", "منقضی"),
    }
    return [
        {"label": palette[st][1], "value": counts.get(st, 0), "color": palette[st][0]}
        for st in ListingStatus.values
        if counts.get(st, 0) > 0
    ]


def _requests_last_months_chart(agency, months: int = 6) -> dict:
    """Bar chart: new CRM requests per month, last N Jalali-labelled months."""
    from apps.crm.models import Request

    today = timezone.localdate()
    labels, values = [], []
    for back in range(months - 1, -1, -1):
        first = (today.replace(day=1) - datetime.timedelta(days=back * 30))
        first = first.replace(day=1)
        nxt = (first + datetime.timedelta(days=32)).replace(day=1)
        n = Request.all_objects.filter(
            agency=agency, created_at__date__gte=first, created_at__date__lt=nxt
        ).count()
        labels.append(f"{first.year}/{first.month:02d}")
        values.append(n)
    return {"labels": labels, "values": values}


@login_required
def home_view(request):
    """Main dashboard with real stats from the current agency."""
    from apps.crm.models import Request, RequestStatus
    from apps.listings.models import Listing, ListingStatus
    from apps.matching.models import Match
    from apps.publishing.models import JobStatus, PublishJob

    agency = get_current_agency()

    if agency:
        listing_qs = Listing.all_objects.filter(agency=agency)
        active_listings = listing_qs.filter(status=ListingStatus.ACTIVE).count()
        total_listings = listing_qs.count()
        new_requests = Request.all_objects.filter(
            agency=agency, status=RequestStatus.NEW
        ).count()
        total_requests = Request.all_objects.filter(agency=agency).count()
        today = timezone.localdate()
        matches_today = Match.all_objects.filter(
            agency=agency, created_at__date=today
        ).count()
        published_today = PublishJob.all_objects.filter(
            agency=agency,
            status=JobStatus.SUCCESS,
            published_at__date=today,
        ).count()
        status_chart = _listings_by_status_chart(agency)
        requests_chart = _requests_last_months_chart(agency)
    else:
        active_listings = total_listings = 0
        new_requests = total_requests = matches_today = published_today = 0
        status_chart = []
        requests_chart = {"labels": [], "values": []}

    chart_data = {
        "statusChart": status_chart,
        "requestsChart": requests_chart,
    }

    ctx = {
        "active_listings": active_listings,
        "total_listings": total_listings,
        "new_requests": new_requests,
        "total_requests": total_requests,
        "matches_today": matches_today,
        "published_today": published_today,
        "agency": agency,
        # dict — the json_script filter serializes it exactly once
        "chart_data": chart_data,
    }
    return render(request, "dashboard/home.html", ctx)
