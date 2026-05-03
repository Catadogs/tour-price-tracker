# Retrospective

## v1.0 — Personal Tour Price Tracker MVP

**Milestone:** v1.0 MVP  
**Shipped:** 2026-05-03  
**Phases:** 5 (SQLite foundation → Telegram UI → Tracking summaries → Duration anomalies → Currency warnings)  
**Tests:** 58 passing across 4 test files  
**LOC:** ~3,247 Python

---

### What Was Built

| Phase | Deliverable |
|-------|-------------|
| 1 | SQLite storage facade (`storage.py`), schema init, threading.RLock, Docker wiring for `/data/price_monitor.sqlite3` |
| 2 | Fail-secure `is_authorized()`, exact-domain `_ALLOWED_HOSTS` frozenset, SQLite-backed settings mutations through `apply_pending_action` |
| 3 | `format_report`, `format_changes`, `format_new_minimums`, `format_target_alerts` — full Telegram reporting pipeline with 14 tests |
| 4 | `format_duration_anomalies` — generalized pairwise anomaly detection replacing hardcoded 12/13-night comparison |
| 5 | `price_monitor/currency.py` — CBR integration, `currency_observations` SQLite table, preemptive Telegram currency warnings |

---

### What Worked

- **SQLite facade pattern** (`storage.py` with threading.RLock) cleanly replaced JSON persistence without touching the monolith's external interface.
- **Immutable dataclass + `dataclasses.replace`** pattern made config mutations safe across phases without introducing state bugs.
- **Exact-domain allowlist** (`frozenset` + `parsed.hostname`) was the right fix for URL validation — the substring approach would have passed lookalike domains silently.
- **Pure function test structure** — testing `format_duration_anomalies`, `format_target_alerts`, etc. as pure functions made Phase 4/5 tests easy to write and deterministic.
- **CBR JSON mirror** (`cbr-xml-daily.ru/daily_json.js`) worked as the exchange-rate source without requiring API keys.

### What Was Inefficient

- **Phase 2 partial execution** — worktree isolation on Windows caused `.git/config.lock` contention between parallel agents; had to fall back to sequential wave dispatch.
- **Missing VERIFICATION.md for phases 3–5** — DeepSeek completed execution but skipped verification artifacts. The milestone audit caught this, but retroactively verifying 3 phases added overhead.
- **REQUIREMENTS.md checkbox drift** — TG-01 through TG-09 were implemented but left unchecked after Phase 2 execution. Required manual correction before milestone close.
- **Code review agent quota** — the gsd-code-reviewer agent ran out of usage mid-execution during Phase 2 review; REVIEW.md was written but required a manual resume to commit.

### Patterns Established

- `is_authorized()` returns `False` when `TELEGRAM_CHAT_ID` is unset (fail-secure by default).
- `normalize_search_url()` uses `parsed.hostname` not `parsed.netloc` and checks against a `frozenset`, not a substring scan.
- New SQLite tables go in `storage.py`; schema init is idempotent (`CREATE TABLE IF NOT EXISTS`).
- New production helpers go near related helpers in `monitor.py`; only a focused cross-cutting module (like `currency.py`) warrants a new file.
- Test helpers (`_make_bot`, `tmp_path`, `initialize_storage`) keep fixtures self-contained per test.

### Key Lessons

- **Fail-secure beats convenient defaults.** The original `is_authorized()` returned `True` when no chat ID was configured — a backwards default. Flipping to `return False` required zero architectural changes but eliminated the security gap.
- **Generalize from the second case, not the first.** `format_strong_diff_line` was hardcoded for 12/13 nights. Phase 4 replaced it with a generic pairwise comparator — the right move once a second use case existed.
- **Document the "why" for security decisions.** `# D-03: fail-secure when no admin configured` inline comment prevents the guard from being reverted by someone who doesn't understand the intent.
- **Milestone audits catch drift that phase execution misses.** The MILESTONE-AUDIT step found unchecked requirements and missing VERIFICATION.md files that would otherwise have been silently skipped.

---

*v1.0 retrospective written: 2026-05-03*
