# Code Intelligence ظ¤ ╪ت╪▒╪د ╪د┘à┘╪د┌ر

## ┘╪د┘à ┘╛╪▒┘ê┌ء┘ç ╪»╪▒ ┌»╪▒╪د┘

```
I-amlak
```

(CBM ┘╪د┘à ┘╛╪▒┘ê┌ء┘ç ╪▒╪د ╪د╪▓ ┘à╪│█î╪▒ ╪▒█î╪┤┘ç ┘à█îظî╪│╪د╪▓╪»: `I:\amlak` ظْ `I-amlak`)

## ┘ê╪╢╪╣█î╪ز ┌»╪▒╪د┘

| ┘█î┘╪» | ┘à┘é╪»╪د╪▒ |
|------|-------|
| ┘╛╪▒┘ê┌ء┘ç | `I-amlak` |
| ┘╪│╪«┘ç CBM | 0.11.0 |
| ╪ز╪╣╪»╪د╪» node | 612 |
| ╪ز╪╣╪»╪د╪» edge | 2094 |
| ┘ê╪╢╪╣█î╪ز | `ready` |
| ╪د█î┘╪»┌ر╪│ظî╪┤╪»┘ç ╪»╪▒ | 2026-09-20 |

## ┘╪╡╪ذ

╪ذ╪د█î┘╪▒█î ╪»╪▒ ┘à╪│█î╪▒ ╪▓█î╪▒ ┘╪╡╪ذ ╪┤╪»┘ç:
```
C:\Users\acer\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe
```

PATH ┌ر╪د╪▒╪ذ╪▒ ╪ذ┘çظî╪▒┘ê╪▓ ╪┤╪»┘ç╪ؤ ╪»╪│╪ز┘ê╪▒ ┌ر┘ê╪ز╪د┘ç: `codebase-memory-mcp`

## ╪»╪│╪ز┘ê╪▒┘ç╪د█î ┘╛╪▒┌ر╪د╪▒╪ذ╪▒╪»

```powershell
# ╪ذ╪▒╪▒╪│█î ┘ê╪╢╪╣█î╪ز ╪د█î┘╪»┌ر╪│
codebase-memory-mcp cli index_status --project=I-amlak

# ┘┘ç╪▒╪│╪ز ┘╛╪▒┘ê┌ء┘çظî┘ç╪د
codebase-memory-mcp cli list_projects

# ╪ش╪│╪ز╪ش┘ê█î ╪ز╪د╪ذ╪╣/┌ر┘╪د╪│
codebase-memory-mcp cli search_graph --project=I-amlak --name-pattern=".*format_toman.*"

# ┘à╪│█î╪▒ ┘╪▒╪د╪«┘ê╪د┘█î (╪ذ╪ذ█î┘ ┌┘ç ┌ر╪│█î ╪د█î┘ ╪ز╪د╪ذ╪╣ ╪▒╪د ╪╡╪»╪د ┘à█îظî╪▓┘╪»)
codebase-memory-mcp cli trace_path --project=I-amlak --function-name=verify_otp --direction=inbound

# ╪«┘ê╪د┘╪»┘ ┌ر╪» █î┌ر ╪ز╪د╪ذ╪╣ ┘à╪┤╪«╪╡ (╪ذ┘çظî╪ش╪د█î ╪«┘ê╪د┘╪»┘ ┌ر┘ ┘╪د█î┘)
codebase-memory-mcp cli get_code_snippet --project=I-amlak --qualified-name="I-amlak.apps.core.currency.format_toman"

# ╪ذ╪▒╪▒╪│█î ┘╛┘ê╪┤╪┤ ╪د█î┘╪»┌ر╪│
codebase-memory-mcp cli check_index_coverage --project=I-amlak --paths="apps/core/currency.py"

# ╪ز╪║█î█î╪▒╪د╪ز ╪ز╪ث╪س█î╪▒┌»╪░╪د╪▒ ┘é╪ذ┘ ╪د╪▓ ┌ر╪د┘à█î╪ز
codebase-memory-mcp cli detect_changes --project=I-amlak

# Cypher query ┘à╪│╪ز┘é█î┘à (┘à╪س╪د┘: ╪ز┘ê╪د╪ذ╪╣ ╪ذ╪»┘ê┘ ┘╪▒╪د╪«┘ê╪د┘█îظî┌ر┘┘╪»┘ç)
codebase-memory-mcp cli query_graph --project=I-amlak --query="MATCH (f:Function) WHERE NOT EXISTS { (f)<-[:CALLS]-() } RETURN f.name LIMIT 20"

# ╪▒█î┘╪»┌ر╪│ ┌ر╪▒╪»┘ (┘╛╪│ ╪د╪▓ ╪ز╪║█î█î╪▒╪د╪ز ╪ذ╪▓╪▒┌»)
codebase-memory-mcp cli index_repository --repo-path=I:\amlak
```

## ╪ذ╪د╪▓ ┌ر╪▒╪»┘ UI ┌»╪▒╪د┘ (╪ز╪╣╪د┘à┘█î)

```powershell
codebase-memory-mcp --ui=true --port=9749
```

╪│┘╛╪│ ╪»╪▒ ┘à╪▒┘ê╪▒┌»╪▒ ╪ذ╪د╪▓ ┌ر┘█î╪»:

**http://localhost:9749**

daemon ╪»╪▒ ┘╛╪│ظî╪▓┘à█î┘┘ç ╪د╪ش╪▒╪د ┘à█îظî╪┤┘ê╪»╪ؤ ╪ز┘┘ç╪د █î┌ر ╪│╪▒┘ê╪▒ HTTP ╪ذ╪▒╪د█î ┘ç┘à┘ç sessionظî┘ç╪د.

## ╪┤╪▒┘ê╪╣/╪ز┘ê┘é┘ daemon

```powershell
codebase-memory-mcp daemon start   # ╪┤╪▒┘ê╪╣ daemon ╪»╪د╪خ┘à█î
codebase-memory-mcp daemon stop    # ╪ز┘ê┘é┘ daemon
```

## ┘é┘ê╪د╪╣╪» ╪د╪│╪ز┘╪د╪»┘ç ╪ذ╪▒╪د█î ╪د█î╪ش┘╪زظî┘ç╪د

> ╪د█î┘ ┘é┘ê╪د╪╣╪» ╪»╪▒ [`AGENTS.md`](../AGENTS.md) ┘█î╪▓ ╪ت┘à╪»┘ç ╪د╪│╪ز.

### █▒. ╪┤╪▒┘ê╪╣ ┘ç╪▒ ╪ز╪│┌ر
┘é╪ذ┘ ╪د╪▓ ┘ç╪▒ ┌ر╪د╪▒:
```
get_architecture(aspects=['all'])   ظ ┘┘ç┘à ┌ر┘█î ┘à╪╣┘à╪د╪▒█î
search_graph(name_pattern="...")    ظ ┘╛█î╪»╪د ┌ر╪▒╪»┘ ┘à╪ص┘ ┌ر╪»
```
╪ذ┘çظî╪ش╪د█î ╪«┘ê╪د┘╪»┘ ┌ر┘ ┘╪د█î┘╪î ╪د╪▓ `get_code_snippet` ╪د╪│╪ز┘╪د╪»┘ç ┌ر┘.

### █▓. ┘é╪ذ┘ ╪د╪▓ ╪ز╪║█î█î╪▒ ╪د┘à╪╢╪د█î ╪ز╪د╪ذ╪╣ █î╪د ┘à╪»┘
```
trace_path(function_name="...", direction="inbound")
```
caller┘ç╪د█î ┘╪╣┘█î ╪▒╪د ╪ذ╪ذ█î┘ ╪ز╪د regression ╪د█î╪ش╪د╪» ┘╪┤┘ê╪».

### █│. ┘é╪ذ┘ ╪د╪▓ commit
```
detect_changes(project="I-amlak")
```
╪»╪د┘à┘┘ç ╪د╪س╪▒ ╪▒╪د ╪ذ╪▒╪▒╪│█î ┌ر┘. ╪ز╪│╪ز ╪د┘╛ظî┘ç╪د█î ╪ز╪ث╪س█î╪▒┘╛╪░█î╪▒ ╪▒╪د ╪د╪ش╪▒╪د ┌ر┘.

### █┤. ┘é╪ذ┘ ╪د╪▓ ╪د╪╣╪ز┘à╪د╪» ╪ذ┘ç ┘╪ز╪د█î╪ش ┌»╪▒╪د┘
```
index_status(project="I-amlak")
```
╪د┌»╪▒ ┌ر┘ç┘┘ç ╪ذ┘ê╪»: `index_repository(repo_path="I:\\amlak")`

### █╡. ╪د╪»╪╣╪د█î ┬س┌ر╪» ┘à╪▒╪»┘ç┬╗ █î╪د ┬س╪ذ█îظî╪د╪│╪ز┘╪د╪»┘ç┬╗
┘┘é╪╖ ╪ذ╪د ╪ز╪ث█î█î╪» ┘à╪│╪ز┘é█î┘à ╪د╪▓ ┘à┘╪ذ╪╣. ╪ز╪ص┘█î┘ ╪د█î╪│╪ز╪د ╪د╪▒╪ش╪د╪╣ظî┘ç╪د█î ╪▒╪┤╪ز┘çظî╪د█î (┘╪د┘à URL╪î ┘╪د┘à ╪ز╪│┌ر Celery╪î signal╪î template tag╪î getattr) ╪▒╪د ┘┘à█îظî╪ذ█î┘╪».
```
check_index_coverage(project="I-amlak", paths=["path/to/file.py"])
```

### █╢. ╪ز╪╡┘à█î┘à ┘à╪╣┘à╪د╪▒█î ┘à┘ç┘à ╪ش╪»█î╪»
```
manage_adr(project="I-amlak", mode="set_sections", section_updates={...})
```

### █╖. ┌»╪▒╪د┘ ╪ش╪د█î┌»╪▓█î┘ ╪«┘ê╪د┘╪»┘ ┌ر╪» ┘█î╪│╪ز
┘é╪ذ┘ ╪د╪▓ ┘ê█î╪▒╪د█î╪┤╪î ┘╪د█î┘ ╪▒╪د ╪ذ╪د `get_code_snippet` █î╪د `read_file` ╪ذ╪«┘ê╪د┘.

## ┘à╪ص╪»┘ê╪»█î╪زظî┘ç╪د█î ╪┤┘╪د╪«╪ز┘çظî╪┤╪»┘ç query ┬س┌ر╪» ┘à╪▒╪»┘ç┬╗

┘╪ز█î╪ش┘çظî█î query ╪▓█î╪▒:
```cypher
MATCH (f:Function) WHERE NOT EXISTS { (f)<-[:CALLS]-() } RETURN f.name LIMIT 20
```

**█▓█░ ╪ز╪د╪ذ╪╣ ╪ذ╪»┘ê┘ ┘╪▒╪د╪«┘ê╪د┘█îظî┌ر┘┘╪»┘ç (╪»╪▒ ┌»╪▒╪د┘):**
`print, toman_filter, fa_number_filter, fa_format_filter, login_view, otp_verify_view, logout_view, send_otp_sms_task, home_view, app, toggleDark, ui_context, agency_a, agency_b, user_a, user_b, superadmin`

**╪ز┘╪│█î╪▒ ┘à┘ç┘à:**
- `login_view`, `home_view`, `logout_view` ظ¤ ╪د╪▓ ╪╖╪▒█î┘é `urls.py` (╪▒╪┤╪ز┘ç URL) ┘╪▒╪د╪«┘ê╪د┘█î ┘à█îظî╪┤┘ê┘╪»╪î ┘┘ç import ┘à╪│╪ز┘é█î┘à. ┌»╪▒╪د┘ ╪د█î╪│╪ز╪د ╪د█î┘ ╪▒╪د ┘┘à█îظî╪ذ█î┘╪».
- `send_otp_sms_task` ظ¤ Celery task ╪د╪│╪ز╪ؤ ┘╪▒╪د╪«┘ê╪د┘█î ╪د╪▓ ╪╖╪▒█î┘é `.delay()` ┌ر┘ç ╪▒╪┤╪ز┘ç ┘╪د┘à task ╪د╪│╪ز.
- `toman_filter`, `fa_number_filter`, `fa_format_filter` ظ¤ template tags ┘ç╪│╪ز┘╪»╪ؤ ╪د╪▓ template HTML ╪╡╪»╪د ╪▓╪»┘ç ┘à█îظî╪┤┘ê┘╪».
- `app`, `toggleDark` ظ¤ ╪ز┘ê╪د╪ذ╪╣ Alpine.js ╪»╪▒ JavaScript ┘ç╪│╪ز┘╪».
- `agency_a`, `agency_b`, `user_a`, `user_b`, `superadmin` ظ¤ pytest fixtures ┘ç╪│╪ز┘╪»╪ؤ ╪ز┘ê╪│╪╖ framework ╪ز╪▓╪▒█î┘é ┘à█îظî╪┤┘ê┘╪».
- ┘ç█î┌ظî┌ر╪»╪د┘à ╪د╪▓ ╪د█î┘ظî┘ç╪د ┘ê╪د┘é╪╣╪د┘ï ┬س┘à╪▒╪»┘ç┬╗ ┘█î╪│╪ز┘╪».

## ┘╪د█î┘ .cbmignore

╪»╪▒ ╪▒█î╪┤┘ç ┘╛╪▒┘ê┌ء┘ç ┘é╪▒╪د╪▒ ╪»╪د╪▒╪». ╪»╪د█î╪▒┌ر╪ز┘ê╪▒█îظî┘ç╪د█î ╪ذ█îظî┘╪د█î╪»┘ç ╪د█î┘╪»┌ر╪│ ┘┘à█îظî╪┤┘ê┘╪»:
```
staticfiles/
media/
node_modules/
htmlcov/
static/vendor/
*.min.js
*.min.css
```

## ╪ت╪▒╪ز█î┘┌ر╪ز ┌»╪▒╪د┘ ┘ê git

╪ت╪▒╪ز█î┘┌ر╪ز ┌»╪▒╪د┘ (`.codebase-memory/`) ╪»╪▒ `.gitignore` ╪د╪│╪ز ┘ê ┌ر╪د┘à█î╪ز **┘┘à█îظî╪┤┘ê╪»** (┘ç╪▒ ╪ز┘ê╪│╪╣┘çظî╪»┘ç┘╪»┘ç ┌»╪▒╪د┘ ┘à╪ص┘█î ╪«┘ê╪» ╪▒╪د ┘à█îظî╪│╪د╪▓╪»). ╪╖╪ذ┘é ╪ذ╪«╪┤ ┬سTeam-Shared Graph Artifact┬╗ ╪»╪▒ README ╪▒╪│┘à█î╪î ╪ذ┘ç ╪د╪┤╪ز╪▒╪د┌رظî┌»╪░╪د╪▒█î ╪د╪▓ ╪╖╪▒█î┘é Git LFS ┘█î╪د╪▓ ╪ذ┘ç ╪ذ╪▒╪▒╪│█î ┘ç╪▓█î┘┘ç ╪»╪د╪▒╪».
