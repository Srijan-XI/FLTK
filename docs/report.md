# FreelancerToolkit — Bug Fix Report

**Date:** 2026-03-12  
**Scope:** Full codebase review and fix pass — `d:\CODE-TOOLS\FreelancerToolkit`  
**Test result (after fixes):** ✅ 57 / 57 passed

---

## Summary of Changes

| # | Severity | File(s) | Issue | Fixed |
|---|---|---|---|---|
| 1 | 🔴 Critical | `helpers.py` | `_save()` truncated file on crash (data loss) | ✅ Atomic writes |
| 2 | 🔴 Critical | `helpers.py` | `_load()` silently swallowed corrupt JSON | ✅ Logs + raises |
| 3 | 🟠 High | `helpers.py` | `profitability_report()` crashed on `null` totals | ✅ Null-safe casts |
| 4 | 🟠 High | `helpers.py` | `convert_quote_to_invoice()` had no status guard | ✅ Raises `ValueError` |
| 5 | 🟠 High | `app.py` | `SECRET_KEY` fell back silently in production | ✅ Enforced in prod |
| 6 | 🟡 Medium | `helpers.py` | `get_upcoming_followups()` bypassed `get_clients()` | ✅ Uses `get_clients()` |
| 7 | 🟡 Medium | `helpers.py` | `expenses.json` bare string literals, no constant | ✅ `EXPENSES_FILE` const |
| 8 | 🟡 Medium | `helpers.py` | `get_expense_summary()` unsafe `e["amount"]` access | ✅ Defensive `.get()` |
| 9 | 🟡 Medium | `routes.py` | `convert_quote` route didn't handle new `ValueError` | ✅ `try/except` |
| 10 | 🟢 Low | `pytest.ini` | pytest only found 1 test file (no config) | ✅ `pytest.ini` added |
| 11 | 🟢 Low | `tests/conftest.py` | No conftest — import paths fragile | ✅ `conftest.py` added |
| 12 | 🟢 Low | `tests/test_quotes.py` | Tests called helper without required status | ✅ Tests updated |
| 13 | 🟢 Low | `app.py` | No application-level logging configured | ✅ `basicConfig` added |

---

## Detailed Fix Notes

### Fix 1 & 2 — Atomic Writes + Corrupt JSON Detection (`helpers.py`)

**Before:**
```python
def _save(filename, data):
    with open(path, "w") as f:          # ← file truncated here
        json.dump(data, f, indent=2)    # ← crash here = empty file

def _load(filename):
    except (json.JSONDecodeError, IOError):
        return []                        # ← silently returns [] on corruption
```

**After (`_save`):**
```python
fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
os.replace(tmp_path, path)   # atomic rename — target only replaced on success
```

**After (`_load`):**
```python
except json.JSONDecodeError as exc:
    log.error("_load: corrupt JSON in '%s': %s — file NOT overwritten.", path, exc)
    raise ValueError(f"Data file '{filename}' is corrupt. ...")
```

- A disk-full or process-kill during a write can no longer corrupt existing data files.
- Corrupt files now surface immediately as a `ValueError` with a clear message instead
  of silently clearing all records.

---

### Fix 3 — Null-Safe `profitability_report()` (`helpers.py:1979`)

**Before:**
```python
total_billed = round(sum(i["total"] for i in client_invoices), 2)
#                         ^^^^^^^^^^  TypeError if "total" is null
```

**After:**
```python
total_billed = round(sum(float(i.get("total", 0) or 0) for i in client_invoices), 2)
```

Applied to `total_billed`, `total_paid`, `total_hours`, and `budgeted_hours`.
Prevents the `/reports` page from crashing after a partial data restore.

---

### Fix 4 — Status Guard on `convert_quote_to_invoice()` (`helpers.py:1086`)

**Before:** Only the route checked quota status. Calling the helper directly could
create an invoice from a `draft` or `rejected` quote.

**After:** The helper itself raises `ValueError` for three conditions:
1. Quote not found
2. Quote already converted
3. Quote status is not `"accepted"`

The route (`routes.py`) is simplified to a single `try/except ValueError`.

---

### Fix 5 — `SECRET_KEY` Enforcement (`app.py`)

**Before:**
```python
app.secret_key = os.environ.get("SECRET_KEY", "fltk-dev-secret-key")
# ← hardcoded fallback used silently in production
```

**After:**
```python
if not _secret and not _debug:
    raise RuntimeError("SECRET_KEY environment variable must be set in production.")
app.secret_key = _secret or "fltk-dev-secret-do-not-use-in-prod"
```

Production deployments (`FLASK_DEBUG=0`) now **fail fast** with a clear error if no
`SECRET_KEY` is set. Local development (`FLASK_DEBUG=1`, the default) is unaffected.

---

### Fix 6 — `get_upcoming_followups()` Consistency (`helpers.py:1880`)

**Before:**
```python
clients = {c["id"]: c["name"] for c in _load("clients.json")}
```

**After:**
```python
clients = {c["id"]: c["name"] for c in get_clients()}
```

Now honours any normalisation / default-filling logic inside `get_clients()`.

---

### Fix 7 & 8 — `EXPENSES_FILE` Constant + Null-Safe Amounts (`helpers.py`)

Added `EXPENSES_FILE = "expenses.json"` constant (matching the pattern of every other
data file). All six expense functions updated to use it.

`get_expense_summary()` now uses `float(e.get("amount", 0) or 0)` throughout —
consistent with the defensive pattern used everywhere else in the module.

---

### Fix 9 — Route Handles `ValueError` (`routes.py:1000`)

`convert_quote()` now uses a single `try/except ValueError` that displays the
exception message as a flash error. This is simpler and handles all error cases from
the helper in one place.

---

### Fix 10 & 11 — Test Configuration (`pytest.ini`, `tests/conftest.py`)

**Problem:** Running `py -3.13 -m pytest tests/` only collected `test_wft_sdlc.py`
(1 test) due to import path resolution quirks with no project-level pytest config.

**Fix:** Added `pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
```

And `tests/conftest.py` (marker file). Now all test files are always discovered.
**Test count went from 1 → 57 collected.**

---

### Fix 12 — Updated `test_quotes.py`

Tests that called `convert_quote_to_invoice()` without first marking the quote as
`"accepted"` would now fail. Updated to:
1. Call `h.update_quote_status(quote_id, "accepted")` before converting.
2. Added `test_convert_to_invoice_requires_accepted_status` — verifies the status
   guard raises on draft quotes.
3. Added `test_convert_already_converted_quote_raises` — verifies double-conversion
   is blocked.

---

## Files Changed

| File | Change type |
|---|---|
| `modules/wft/helpers.py` | Bug fixes (6 locations) |
| `modules/wft/routes.py` | Simplified `convert_quote` route |
| `app.py` | SECRET_KEY enforcement + logging |
| `pytest.ini` | New — test discovery config |
| `tests/conftest.py` | New — marks test root |
| `tests/test_quotes.py` | Updated + 2 new test cases |

---

## Remaining Recommendations (Not Auto-Fixed)

These are architectural concerns that require a deliberate decision and potentially
breaking changes — not applied in this pass:

| # | Item | Effort | Risk |
|---|---|---|---|
| R1 | Add CSRF protection via Flask-WTF | Medium | Requires form token in every template |
| R2 | File-level locking for multi-worker safety | Medium | Only relevant with Gunicorn/multiple threads |
| R3 | Log warning in `analytics()` when date parsing silently skips entries | Low | Cosmetic |
| R4 | Validate `backup_restore` file MIME type server-side (not just extension) | Low | Security edge case |

---

*All 57 tests pass. No regressions introduced.*
