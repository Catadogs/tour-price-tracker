---
phase: 02-admin-telegram-control-ui-and-authorization
plan: 01
type: summary
completed: 2026-05-03
tests: 32 passed
---

# Phase 02 Plan 01 Summary

## What Was Done

### Task 1: Hardened URL Validation (QUAL-06)

- Added `_is_allowed_host()` helper with exact host matching (`bgoperator.ru`, `level.travel`, `travelata.ru` plus `www.` prefix variants).
- Replaced substring matching `any(allowed in host for allowed in allowed_hosts)` — now rejects lookalike domains:
  - `bgoperator.ru.evil.com` ❌
  - `evil-bgoperator.ru` ❌
  - `not-bgoperator.ru` ❌
  - `fake-level.travel.evil.com` ❌
  - `travelata.ru.scam.ru` ❌
- Legitimate URLs with `www.` prefix still accepted (`www.bgoperator.ru` ✓).

### Task 2: Added Telegram Tests (QUAL-05)

Added 7 new tests:
- `test_normalize_search_url_rejects_lookalike_domains` — 7 lookalike URLs rejected
- `test_normalize_search_url_accepts_www_prefix` — www variants accepted
- `test_is_authorized_blocks_unrecognized_chat` — admin-only access enforced
- `test_is_authorized_allows_all_when_chat_id_unset` — open access when unconfigured
- `test_main_keyboard_structure` — all 12 callback_data values verified
- `test_settings_keyboard_structure` — all 11 callback_data values verified
- `test_format_settings_contains_key_fields` — output contains all setting fields

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `price_monitor/monitor.py` | Added `_is_allowed_host()`, updated `normalize_search_url()` | +6 |
| `tests/test_price_monitor.py` | Added 7 test functions + imports | +120 |

## Verification

- All 32 tests pass (25 existing + 7 new)
- No regressions in storage, parsing, or existing Telegram tests

## Requirements Satisfied

- [x] QUAL-05: Telegram formatting and menu helpers have tests
- [x] QUAL-06: Provider URL validation rejects lookalike domains
