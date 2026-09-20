"""
Custom user model for Ara Amlak.

Authenticates by phone number + OTP (no username/password for regular users).
Superadmin can also use Django admin password login.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class UserRole(models.TextChoices):
    SUPERADMIN = "superadmin", _("سوپرادمین")
    OWNER = "owner", _("مالک آژانس")
    AGENT = "agent", _("مشاور")
    VIEWER = "viewer", _("مشاهده‌گر")


class CustomUserManager(BaseUserManager):
    """Manager for phone-based user authentication."""

    def create_user(self, phone: str, full_name: str = "", **extra_fields):
        if not phone:
            raise ValueError(_("شماره موبایل الزامی است"))
        phone = self._normalize_phone(phone)
        user = self.model(phone=phone, full_name=full_name, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, full_name: str = "", **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPERADMIN)
        user = self.create_user(phone, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize Iranian phone numbers to 09XXXXXXXXX format."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        # Convert Persian/Arabic digits to ASCII
        from apps.core.currency import to_persian_digits  # noqa: F401
        _PERSIAN_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        phone = phone.translate(_PERSIAN_TO_ASCII)
        # +98 → 0
        if phone.startswith("+98"):
            phone = "0" + phone[3:]
        elif phone.startswith("98") and len(phone) == 12:
            phone = "0" + phone[2:]
        return phone


class CustomUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom user model.
    - Login via phone + OTP.
    - Superadmin has agency=None and is_staff=True.
    - Timestamps from TimeStampedModel.
    """

    phone = models.CharField(_("شماره موبایل"), max_length=15, unique=True)
    full_name = models.CharField(_("نام کامل"), max_length=150, blank=True)
    email = models.EmailField(_("ایمیل"), blank=True)
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("آژانس"),
    )
    role = models.CharField(
        _("نقش"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.AGENT,
    )
    is_active = models.BooleanField(_("فعال"), default=True)
    is_staff = models.BooleanField(_("کارمند سیستم"), default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")

    def __str__(self) -> str:
        return f"{self.full_name or self.phone}"

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.full_name.split()[0] if self.full_name else self.phone
