"""Dashboard views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home_view(request):
    """Main dashboard — stub for phase 1."""
    return render(request, "dashboard/home.html")
