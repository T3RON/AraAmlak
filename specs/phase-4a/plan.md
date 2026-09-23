# Plan — 4A

1. `apps/messaging/segments.py`, `rendering.py` (خالص، بدون Django).
2. `apps/messaging/providers/` — base, transport (urllib, mockable), kavenegar, melipayamak, dev (Console/Fake), registry.
3. models + migration `messaging/0001_initial`.
4. services + tasks (send, poll, check config, OTP).
5. views/forms/urls/templates (HTMX، RTL، Apple-style).
6. permissions: `messaging.view/send/templates/settings`.
7. tests: pure + DB/view/isolation.

## موارد تأییدنشده
- کدهای وضعیت کاوه‌نگار غیر از 1/4/10/100 و `account/info.json`.
- معنی RetStatus غیر از 1 در ملی‌پیامک.
- نیاز به ارسال واقعی با پنل تست.
