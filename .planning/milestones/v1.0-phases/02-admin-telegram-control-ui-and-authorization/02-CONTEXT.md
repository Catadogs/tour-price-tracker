# Phase 2: Admin Telegram Control UI and Authorization - Context

**Gathered:** 2026-05-03
**Status:** Ready for execution

<domain>
## Phase Boundary

Phase 2 hardens the existing Telegram admin controls and authorization. The inline keyboard menu, settings editing, and authorization check already exist in `price_monitor/monitor.py`. This phase focuses on two gaps:

1. **URL validation hardening (QUAL-06):** `normalize_search_url` uses substring matching for host allowlisting, which accepts lookalike domains like `bgoperator.ru.evil.com`.
2. **Telegram test coverage (QUAL-05):** No focused tests exist for `is_authorized`, `main_keyboard`, `settings_keyboard`, `format_settings`, or URL validation edge cases.

No new Telegram features are added — the existing UI fully satisfies TG-01 through TG-07 and TG-09.

</domain>

<decisions>
## Implementation Decisions

### URL validation hardening
- **D-01:** Replace substring host matching with exact host or suffix match against allowed hosts.
- **D-02:** Allowed hosts: `bgoperator.ru`, `level.travel`, `travelata.ru` (and their `www.` prefixed variants).
- **D-03:** Keep the same error messages and exception type (`ValueError`) to avoid breaking TelegramControlBot's existing error handling.

### Test scope
- **D-04:** Add tests for `normalize_search_url` lookalike domain rejection.
- **D-05:** Add tests for `is_authorized` behavior (configured chat id, unset chat id).
- **D-06:** Add tests for `main_keyboard` and `settings_keyboard` structure.
- **D-07:** Add tests for `format_settings` output format.
- **D-08:** Keep tests focused and non-flaky; no integration tests against real Telegram API.

### Files scope
- **D-09:** `price_monitor/monitor.py` — only `normalize_search_url` changes.
- **D-10:** `tests/test_price_monitor.py` — new test functions.
- **D-11:** No new modules, no Docker/config changes.

</decisions>

<requirements>
## Requirements Covered

- [ ] **QUAL-05**: Telegram formatting and menu helpers have tests for key output and authorization behavior.
- [ ] **QUAL-06**: Provider URL validation rejects lookalike domains and unauthorized URL shapes.

Already satisfied by existing code (no changes needed):
- [x] **TG-01**: Inline keyboard menu for viewing/managing settings
- [x] **TG-02**: Add watched hotel/search URL
- [x] **TG-03**: Manage room/hotel filters
- [x] **TG-04**: Set departure date range
- [x] **TG-05**: Set night durations
- [x] **TG-06**: Set target price
- [x] **TG-07**: Set check frequency
- [x] **TG-09**: Unauthorized chat rejection

</requirements>
