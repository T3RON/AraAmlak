# ╪▒╪د┘ç┘┘à╪د█î ┘à╪┤╪د╪▒┌ر╪ز ظ¤ ╪ت╪▒╪د ╪د┘à┘╪د┌ر

## ╪┤╪د╪«┘çظî╪ذ┘╪»█î

| ┘┘ê╪╣ | ╪د┘┌»┘ê | ┘à╪س╪د┘ |
|-----|------|-------|
| ┘╪د╪▓ ╪ش╪»█î╪» | `phase/<num>-<desc>` | `phase/1b-listing-crud` |
| ╪ذ╪د┌»ظî┘█î┌ر╪│ | `fix/<desc>` | `fix/otp-expiry` |
| ┘ç╪د╪زظî┘█î┌ر╪│ | `hotfix/<desc>` | `hotfix/celery-reconnect` |

**┘é┘ê╪د┘█î┘:**
- ┘ç╪▒ ╪┤╪د╪«┘ç ╪د╪▓ `main` ╪ز╪د╪▓┘ç ┌»╪▒┘╪ز┘ç ╪┤┘ê╪».
- ┘à╪│╪ز┘é█î┘à ╪▒┘ê█î `main` ┌ر╪د┘à█î╪ز █î╪د force-push ┘┌ر┘█î╪».
- ┘ç╪▒ ╪ز╪│┌ر = █î┌ر ┌ر╪د┘à█î╪ز ┘à╪ش╪▓╪د.
- ┘é╪ذ┘ ╪د╪▓ push╪î ╪ز╪│╪زظî┘ç╪د ┘ê lint ╪│╪ذ╪▓ ╪ذ╪د╪┤┘╪».

## ┘é╪د┘╪ذ ┘╛█î╪د┘à ┌ر╪د┘à█î╪ز

```
<type>(<scope>): <subject>

[body ظ¤ ╪د╪«╪ز█î╪د╪▒█î]

Phase: <phase-number>
```

### ┘┘ê╪╣ظî┘ç╪د█î ┘à╪ش╪د╪▓
`feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`

### ╪د╪│┌ر┘ê┘╛ظî┘ç╪د█î ┘à╪ش╪د╪▓
`core` `accounts` `agencies` `listings` `crm` `matching` `messaging`
`ai` `publishing` `rendering` `accounting` `dashboard` `ui` `infra` `deps` `specs`

### ┘é┘ê╪د┘█î┘ subject
- ╪د┘┌»┘█î╪│█î╪î ╪د┘à╪▒█î╪î ╪ص╪▒┘ê┘ ┌ر┘ê┌┌ر╪î ╪ذ╪»┘ê┘ ┘┘é╪╖┘ç ┘╛╪د█î╪د┘█î
- ╪ص╪»╪د┌ر╪س╪▒ █╖█▓ ┌ر╪د╪▒╪د┌ر╪ز╪▒

### ┘à╪س╪د┘ظî┘ç╪د
```
feat(listings): add property search with PostGIS radius filter

Phase: 2
```
```
fix(accounts): correct OTP expiry check in Redis

┌ر╪» ╪ذ╪▒╪▒╪│█î ╪د┘┘é╪╢╪د ┘ç┘┌»╪د┘à ╪ز┘╪د╪┤ ┘à╪ش╪»╪» ┘╛╪│ ╪د╪▓ ╪▒█î╪│╪ز Redis ╪د╪┤╪ز╪ذ╪د┘ç ╪ذ┘ê╪».

Phase: 1
```
```
feat(agencies)!: rename Agency.plan to Agency.tier

BREAKING CHANGE: plan field renamed to tier; run migration 0003.

Phase: 3
```

## ╪د╪╣╪ز╪ذ╪د╪▒╪│┘╪ش█î ╪«┘ê╪»┌ر╪د╪▒

`gitlint` ╪»╪▒ hook `commit-msg` ╪د█î┘ ┘é╪د┘╪ذ ╪▒╪د ╪د╪ش╪ذ╪د╪▒ ┘à█îظî┌ر┘╪».  
╪ذ╪▒╪د█î ┘╪╡╪ذ hooks:
```bash
pip install pre-commit
pre-commit install --hook-type commit-msg
pre-commit install
```

## ╪ذ╪▒╪▒╪│█î ┘╛█î╪د┘à ┘é╪ذ┘ ╪د╪▓ ┌ر╪د┘à█î╪ز
```bash
echo "feat(listings): add search" | gitlint --staged
```

## Pull Request

- ╪╣┘┘ê╪د┘ PR = ┘╛█î╪د┘à ╪د┘ê┘ ┌ر╪د┘à█î╪ز
- ╪ز┘ê╪╢█î╪ص ┌ر┘ê╪ز╪د┘ç: ┌┘ç ╪ز╪║█î█î╪▒█î╪î ┌╪▒╪د╪î ┌┌»┘ê┘┘ç ╪ز╪│╪ز ╪┤╪»
- CI ╪ذ╪د█î╪» ╪│╪ذ╪▓ ╪ذ╪د╪┤╪» ┘é╪ذ┘ ╪د╪▓ merge
- ╪ص╪»╪د┘é┘ █î┌ر reviewer ╪ذ╪▒╪د█î ╪┤╪د╪«┘çظî┘ç╪د█î phase

## CI

GitHub Actions █î┘çظî╪╡┘ê╪▒╪ز ╪«┘ê╪»┌ر╪د╪▒ ╪د╪ش╪▒╪د ┘à█îظî╪┤┘ê╪»:
1. **lint** ظ¤ `ruff check .`
2. **test** ظ¤ `pytest`
3. **migration-check** ظ¤ `manage.py makemigrations --check`
4. **commitlint** ظ¤ ╪د╪╣╪ز╪ذ╪د╪▒╪│┘╪ش█î ┘╛█î╪د┘à ┌ر╪د┘à█î╪زظî┘ç╪د█î PR
