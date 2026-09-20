"""
Agency-scoped request middleware.

Sets the thread-local current_agency from request.user.agency
so that AgencyManager can filter automatically.
"""

from apps.core.models import clear_current_agency, set_current_agency


class AgencyMiddleware:
    """Bind current agency to thread-local on each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        agency = None
        if request.user.is_authenticated and hasattr(request.user, "agency"):
            agency = request.user.agency
        set_current_agency(agency)
        try:
            response = self.get_response(request)
        finally:
            clear_current_agency()
        return response
