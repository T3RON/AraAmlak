# راهنمای مشارکت — آرا املاک

## شاخه‌بندی

| نوع | الگو | مثال |
|-----|------|-------|
| فاز جدید | `phase/<num>-<desc>` | `phase/1b-listing-crud` |
| باگ‌فیکس | `fix/<desc>` | `fix/otp-expiry` |
| هات‌فیکس | `hotfix/<desc>` | `hotfix/celery-reconnect` |

**قوانین:**
- هر شاخه از `main` تازه گرفته شود.
- مستقیم روی `main` کامیت یا force-push نکنید.
- هر تسک = یک کامیت مجزا.
- قبل از push، تست‌ها و lint سبز باشند.

## قالب پیام کامیت

```
<type>(<scope>): <subject>

[body — اختیاری]

Phase: <phase-number>
```

### نوع‌های مجاز
`feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`

### اسکوپ‌های مجاز
`core` `accounts` `agencies` `listings` `crm` `matching` `messaging`
`ai` `publishing` `rendering` `accounting` `dashboard` `ui` `infra` `deps` `specs`

### قوانین subject
- انگلیسی، امری، حروف کوچک، بدون نقطه پایانی
- حداکثر ۷۲ کاراکتر

### مثال‌ها
```
feat(listings): add property search with PostGIS radius filter

Phase: 2
```
```
fix(accounts): correct OTP expiry check in Redis

کد بررسی انقضا هنگام تلاش مجدد پس از ریست Redis اشتباه بود.

Phase: 1
```
```
feat(agencies)!: rename Agency.plan to Agency.tier

BREAKING CHANGE: plan field renamed to tier; run migration 0003.

Phase: 3
```

## اعتبارسنجی خودکار

`gitlint` در hook `commit-msg` این قالب را اجبار می‌کند.  
برای نصب hooks:
```bash
pip install pre-commit
pre-commit install --hook-type commit-msg
pre-commit install
```

## بررسی پیام قبل از کامیت
```bash
echo "feat(listings): add search" | gitlint --staged
```

## Pull Request

- عنوان PR = پیام اول کامیت
- توضیح کوتاه: چه تغییری، چرا، چگونه تست شد
- CI باید سبز باشد قبل از merge
- حداقل یک reviewer برای شاخه‌های phase

## CI

GitHub Actions یه‌صورت خودکار اجرا می‌شود:
1. **lint** — `ruff check .`
2. **test** — `pytest`
3. **migration-check** — `manage.py makemigrations --check`
4. **commitlint** — اعتبارسنجی پیام کامیت‌های PR
