"""
Tenant isolation tests.

Verifies that AgencyManager only returns records belonging to
the currently-set agency context, and never leaks cross-tenant data.
"""

import pytest

from apps.core.models import clear_current_agency, set_current_agency
from tests.factories import AgencyFactory, AgencyMemberFactory, BranchFactory, CustomUserFactory


@pytest.mark.django_db
class TestAgencyManagerIsolation:
    """Agency-scoped manager filters correctly by tenant."""

    def test_branch_only_returns_own_agency(self):
        """Agency A cannot see Agency B's branches through default manager."""
        agency_a = AgencyFactory()
        agency_b = AgencyFactory()
        branch_a = BranchFactory(agency=agency_a, name="شعبه الف")
        branch_b = BranchFactory(agency=agency_b, name="شعبه ب")

        set_current_agency(agency_a)
        try:
            from apps.agencies.models import Branch
            branches = Branch.objects.all()
            assert branch_a in branches
            assert branch_b not in branches
        finally:
            clear_current_agency()

    def test_branch_other_agency_invisible(self):
        """Agency B's data is invisible when agency A is set."""
        agency_a = AgencyFactory()
        agency_b = AgencyFactory()
        BranchFactory(agency=agency_b)

        set_current_agency(agency_a)
        try:
            from apps.agencies.models import Branch
            assert Branch.objects.count() == 0
        finally:
            clear_current_agency()

    def test_all_objects_returns_everything(self):
        """all_objects manager bypasses tenant filter."""
        agency_a = AgencyFactory()
        agency_b = AgencyFactory()
        BranchFactory(agency=agency_a)
        BranchFactory(agency=agency_b)

        set_current_agency(agency_a)
        try:
            from apps.agencies.models import Branch
            # Default manager: only agency_a's records
            assert Branch.objects.count() == 1
            # all_objects: all records regardless of tenant
            assert Branch.all_objects.count() == 2
        finally:
            clear_current_agency()

    def test_no_context_returns_all(self):
        """With no agency in context (superadmin), all records are returned."""
        agency_a = AgencyFactory()
        agency_b = AgencyFactory()
        BranchFactory(agency=agency_a)
        BranchFactory(agency=agency_b)

        clear_current_agency()
        from apps.agencies.models import Branch
        assert Branch.objects.count() == 2

    def test_agency_member_isolation(self):
        """AgencyMember for agency A not visible from agency B context."""
        agency_a = AgencyFactory()
        agency_b = AgencyFactory()
        user = CustomUserFactory(agency=agency_a)
        AgencyMemberFactory(user=user, agency=agency_a)

        set_current_agency(agency_b)
        try:
            from apps.agencies.models import AgencyMember
            assert AgencyMember.objects.count() == 0
        finally:
            clear_current_agency()


@pytest.mark.django_db
class TestMiddlewareSetsAgency:
    """AgencyMiddleware binds user.agency to thread-local."""

    def test_middleware_sets_agency(self, rf):
        """After middleware processes request, thread-local agency matches user's agency."""
        from apps.core.middleware import AgencyMiddleware

        agency = AgencyFactory()
        user = CustomUserFactory(agency=agency)
        user.is_authenticated = True  # simulate authenticated user

        responses = []

        def get_response(req):
            from apps.core.models import get_current_agency
            responses.append(get_current_agency())
            return type("Response", (), {"status_code": 200})()

        middleware = AgencyMiddleware(get_response)

        request = rf.get("/")
        request.user = user
        middleware(request)

        assert responses[0] == agency

    def test_middleware_clears_after_response(self, rf):
        """Thread-local is cleared after the request completes."""
        from apps.core.middleware import AgencyMiddleware
        from apps.core.models import get_current_agency

        agency = AgencyFactory()
        user = CustomUserFactory(agency=agency)
        user.is_authenticated = True

        middleware = AgencyMiddleware(lambda req: type("R", (), {"status_code": 200})())
        request = rf.get("/")
        request.user = user
        middleware(request)

        # After request, context is cleared
        assert get_current_agency() is None
