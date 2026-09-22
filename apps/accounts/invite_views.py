"""
Invitation views: create invite, list invites, accept invite.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.otp import send_otp, verify_otp
from apps.accounts.permissions import role_required
from apps.agencies.models import Invitation
from apps.core.models import AuditAction, AuditLog

User = get_user_model()


# ─── Owner: create and list invitations ───────────────────────────────────────


@login_required
@role_required("owner", "superadmin")
def invite_create_view(request):
    """Create a new invitation link for this agency."""
    from apps.agencies.models import AgencyMemberRole

    agency = request.user.agency
    if not agency:
        messages.error(request, "شما به هیچ آژانسی متصل نیستید.")
        return redirect("dashboard:home")

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", AgencyMemberRole.AGENT)
        if role not in AgencyMemberRole.values:
            role = AgencyMemberRole.AGENT

        invite = Invitation.objects.create(
            agency=agency,
            invited_by=request.user,
            phone=phone,
            role=role,
        )
        AuditLog.log(
            actor=request.user,
            agency=agency,
            action=AuditAction.INVITE,
            obj=invite,
            request=request,
            extra={"phone": phone or "—", "role": role},
        )
        invite_url = request.build_absolute_uri(
            f"/auth/invite/{invite.token}/accept/"
        )
        messages.success(request, f"لینک دعوت ساخته شد: {invite_url}")
        return redirect("accounts:invite-list")

    from apps.agencies.models import AgencyMemberRole as R
    ctx = {"roles": R.choices}
    return render(request, "accounts/invite_create.html", ctx)


@login_required
@role_required("owner", "superadmin")
def invite_list_view(request):
    """List all invitations for this agency."""
    agency = request.user.agency
    invites = Invitation.objects.filter(agency=agency).order_by("-created_at")[:50]
    return render(request, "accounts/invite_list.html", {"invites": invites})


# ─── Accept invitation (public — only needs token) ───────────────────────────


class InviteAcceptView(View):
    """
    Two-step: verify phone via OTP, then link the user to the agency.

    Step 1 (GET): Show phone input (or OTP input if phone already entered).
    Step 2 (POST phone): Send OTP.
    Step 3 (POST otp): Verify OTP, create/login user, call invite.accept().
    """

    def get(self, request, token):
        invite = self._get_valid_invite(token)
        if invite is None:
            messages.error(request, "این لینک دعوت نامعتبر یا منقضی شده است.")
            return redirect("accounts:login")
        if request.user.is_authenticated:
            return self._do_accept(request, invite, request.user)
        step = request.session.get(f"invite_{token}_step", "phone")
        ctx = {"invite": invite, "step": step, "token": token}
        if step == "otp":
            ctx["phone"] = request.session.get(f"invite_{token}_phone", "")
        return render(request, "accounts/invite_accept.html", ctx)

    def post(self, request, token):
        invite = self._get_valid_invite(token)
        if invite is None:
            messages.error(request, "این لینک دعوت نامعتبر یا منقضی شده است.")
            return redirect("accounts:login")

        step = request.session.get(f"invite_{token}_step", "phone")

        if step == "phone":
            phone = request.POST.get("phone", "").strip()
            if not phone:
                messages.error(request, "شماره موبایل را وارد کنید.")
                return redirect("accounts:invite-accept", token=token)
            if invite.phone and invite.phone != phone:
                messages.error(request, "این دعوت‌نامه برای شماره دیگری است.")
                return redirect("accounts:invite-accept", token=token)
            send_otp(phone)
            request.session[f"invite_{token}_phone"] = phone
            request.session[f"invite_{token}_step"] = "otp"
            return redirect("accounts:invite-accept", token=token)

        if step == "otp":
            phone = request.session.get(f"invite_{token}_phone", "")
            code = request.POST.get("code", "").strip()
            if not verify_otp(phone, code):
                messages.error(request, "کد نادرست یا منقضی شده است.")
                return redirect("accounts:invite-accept", token=token)
            user, _ = User.objects.get_or_create(
                phone=phone, defaults={"is_active": True}
            )
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            # Clean session
            for key in [f"invite_{token}_step", f"invite_{token}_phone"]:
                request.session.pop(key, None)
            return self._do_accept(request, invite, user)

        return redirect("accounts:login")

    @staticmethod
    def _get_valid_invite(token) -> "Invitation | None":
        invite = Invitation.objects.filter(token=token).select_related("agency").first()
        if invite and invite.is_valid:
            return invite
        return None

    @staticmethod
    @transaction.atomic
    def _do_accept(request, invite, user):  # noqa: ANN205
        member = invite.accept(user)
        # Update user agency/role if not set
        changed = False
        if not user.agency_id:
            user.agency = invite.agency
            user.role = invite.role
            changed = True
        if changed:
            user.save(update_fields=["agency", "role"])
        AuditLog.log(
            actor=user,
            agency=invite.agency,
            action=AuditAction.INVITE,
            obj=member,
            request=request,
            extra={"result": "accepted", "role": member.role},
        )
        messages.success(
            request,
            f"به آژانس «{invite.agency.name}» با نقش «{member.get_role_display()}» پیوستید.",
        )
        return redirect("dashboard:home")
