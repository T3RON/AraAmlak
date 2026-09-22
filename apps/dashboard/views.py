"""Dashboard views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.core.models import get_current_agency


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
    else:
        active_listings = total_listings = 0
        new_requests = total_requests = matches_today = published_today = 0

    ctx = {
        "active_listings": active_listings,
        "total_listings": total_listings,
        "new_requests": new_requests,
        "total_requests": total_requests,
        "matches_today": matches_today,
        "published_today": published_today,
        "agency": agency,
    }
    return render(request, "dashboard/home.html", ctx)
