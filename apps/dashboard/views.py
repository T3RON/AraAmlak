"""Dashboard views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.models import get_current_agency


@login_required
def home_view(request):
    """Main dashboard with real stats from the current agency."""
    from apps.crm.models import Request, RequestStatus
    from apps.listings.models import Listing, ListingStatus

    agency = get_current_agency()

    if agency:
        listing_qs = Listing.objects.filter(agency=agency)
        active_listings = listing_qs.filter(status=ListingStatus.ACTIVE).count()
        total_listings = listing_qs.count()
        new_requests = Request.objects.filter(
            agency=agency, status=RequestStatus.NEW
        ).count()
        total_requests = Request.objects.filter(agency=agency).count()
    else:
        active_listings = total_listings = new_requests = total_requests = 0

    ctx = {
        "active_listings": active_listings,
        "total_listings": total_listings,
        "new_requests": new_requests,
        "total_requests": total_requests,
        "agency": agency,
    }
    return render(request, "dashboard/home.html", ctx)
