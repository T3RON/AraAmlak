"""
Agencies app models: Agency, Branch, AgencyMember.
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class AgencyPlan(models.TextChoices):
    FREE = "free", _("رایگان")
    PRO = "pro", _("حرفه‌ای")
    ENTERPRISE = "enterprise", _("سازمانی")


class Agency(TimeStampedModel):
    """Top-level tenant. Each agency is an independent real-estate office."""

    name = models.CharField(_("نام"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), unique=True, max_length=80, allow_unicode=False)
    logo = models.ImageField(_("لوگو"), upload_to="agencies/logos/", blank=True, null=True)
    phone = models.CharField(_("تلفن"), max_length=20, blank=True)
    address = models.TextField(_("آدرس"), blank=True)
    plan = models.CharField(
        _("پلن"),
        max_length=20,
        choices=AgencyPlan.choices,
        default=AgencyPlan.FREE,
    )
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("آژانس")
        verbose_name_plural = _("آژانس‌ها")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Branch(TimeStampedModel):
    """A physical branch of an Agency."""

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="branches",
        verbose_name=_("آژانس"),
    )
    name = models.CharField(_("نام شعبه"), max_length=200)
    address = models.TextField(_("آدرس"), blank=True)
    location = gis_models.PointField(
        _("موقعیت جغرافیایی"), geography=True, blank=True, null=True
    )
    phone = models.CharField(_("تلفن"), max_length=20, blank=True)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("شعبه")
        verbose_name_plural = _("شعبه‌ها")
        ordering = ["agency", "name"]

    def __str__(self) -> str:
        return f"{self.agency.name} — {self.name}"


class AgencyMemberRole(models.TextChoices):
    OWNER = "owner", _("مالک")
    AGENT = "agent", _("مشاور")
    VIEWER = "viewer", _("مشاهده‌گر")


class AgencyMember(TimeStampedModel):
    """Junction table linking a CustomUser to an Agency with a role."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agency_memberships",
        verbose_name=_("کاربر"),
    )
    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name=_("آژانس"),
    )
    role = models.CharField(
        _("نقش"),
        max_length=20,
        choices=AgencyMemberRole.choices,
        default=AgencyMemberRole.AGENT,
    )
    joined_at = models.DateTimeField(_("تاریخ عضویت"), auto_now_add=True)

    class Meta:
        verbose_name = _("عضو آژانس")
        verbose_name_plural = _("اعضای آژانس")
        unique_together = [("user", "agency")]

    def __str__(self) -> str:
        return f"{self.user} @ {self.agency.name} ({self.role})"
