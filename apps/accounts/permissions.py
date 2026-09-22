"""
Centralised permission matrix for Ara Amlak.

Every role-based check lives here — no scattered `if user.role == ...` in views.

Usage in a CBV:
    from apps.accounts.permissions import RoleRequired
    class MyView(RoleRequired, LoginRequiredMixin, View):
        allowed_roles = ["owner", "agent"]

Usage as a decorator:
    from apps.accounts.permissions import role_required
    @role_required("owner")
    def my_view(request): ...

Usage in templates:
    {% if request|can:"listings.create" %}
(template tag not yet implemented — use `request.user.role in [...]` for now)
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

# ─── Role constants (mirror UserRole choices) ─────────────────────────────────

ROLE_SUPERADMIN = "superadmin"
ROLE_OWNER = "owner"
ROLE_AGENT = "agent"
ROLE_ACCOUNTANT = "accountant"
ROLE_SECRETARY = "secretary"
ROLE_VIEWER = "viewer"

# ─── Permission matrix ────────────────────────────────────────────────────────
# Maps permission codename → set of roles that are allowed.
# Convention: "<app>.<action>" or "<app>.<action>.<sub>"

PERMISSION_MATRIX: dict[str, set[str]] = {
    # --- Listings ---
    "listings.view": {ROLE_OWNER, ROLE_AGENT, ROLE_ACCOUNTANT, ROLE_SECRETARY, ROLE_VIEWER},
    "listings.create": {ROLE_OWNER, ROLE_AGENT},
    "listings.edit": {ROLE_OWNER, ROLE_AGENT},
    "listings.delete": {ROLE_OWNER},
    "listings.view_owner_phone": {ROLE_OWNER, ROLE_AGENT},
    # --- CRM / Requests ---
    "crm.view": {ROLE_OWNER, ROLE_AGENT, ROLE_SECRETARY, ROLE_VIEWER},
    "crm.create": {ROLE_OWNER, ROLE_AGENT, ROLE_SECRETARY},
    "crm.edit": {ROLE_OWNER, ROLE_AGENT, ROLE_SECRETARY},
    "crm.delete": {ROLE_OWNER},
    # --- Matching ---
    "matching.view": {ROLE_OWNER, ROLE_AGENT},
    # --- Publishing ---
    "publishing.view": {ROLE_OWNER, ROLE_AGENT},
    "publishing.publish": {ROLE_OWNER, ROLE_AGENT},
    # --- Members / Agency settings ---
    "agencies.manage_members": {ROLE_OWNER},
    "agencies.invite": {ROLE_OWNER},
    "agencies.settings": {ROLE_OWNER},
    # --- Accounting (فاز ۸) ---
    "accounting.view": {ROLE_OWNER, ROLE_ACCOUNTANT},
    "accounting.edit": {ROLE_OWNER, ROLE_ACCOUNTANT},
    # --- Audit log ---
    "core.view_audit": {ROLE_OWNER},
}


def has_permission(user, perm: str) -> bool:
    """
    Return True if `user` has the given permission.

    Superadmins bypass all checks.
    Users without an agency are denied everything (except superadmin).
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, "role", None)
    if not role:
        return False
    allowed = PERMISSION_MATRIX.get(perm, set())
    return role in allowed


# ─── CBV mixin ────────────────────────────────────────────────────────────────


class RoleRequired(LoginRequiredMixin):
    """
    CBV mixin: deny access if user's role is not in `allowed_roles`.

    Combine with LoginRequiredMixin to also check authentication.

    Example:
        class MyView(RoleRequired, View):
            allowed_roles = ["owner", "agent"]
    """

    allowed_roles: list[str] = []
    permission_denied_message = _("دسترسی شما به این بخش مجاز نیست.")

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # If super() returned a redirect (not authenticated), pass it through
        if response.status_code == 302:
            return response
        if not self.allowed_roles:
            return response
        if not has_permission_by_roles(request.user, self.allowed_roles):
            raise PermissionDenied(self.permission_denied_message)
        return response


def has_permission_by_roles(user, roles: list[str]) -> bool:
    """Check if user's role is in the given list (or superadmin)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return getattr(user, "role", None) in roles


# ─── Function-based view decorator ───────────────────────────────────────────


def role_required(*roles: str):
    """
    Decorator for FBVs. Raises PermissionDenied if user lacks required role.

    Usage:
        @login_required
        @role_required("owner", "agent")
        def my_view(request): ...
    """
    from functools import wraps

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_permission_by_roles(request.user, list(roles)):
                raise PermissionDenied(_("دسترسی شما به این بخش مجاز نیست."))
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
