---
phase: 01-provider-hardening
plan: 01
type: summary
completed: 2026-05-03
tests: 64 passed
---

# Phase 01 Plan 01 Summary

## What Was Done

### New package: `price_monitor/parsers/`

| Module | Purpose | Source |
|--------|---------|--------|
| `__init__.py` | Shared data classes (`Offer`, `ExternalPrice`) + helpers (`parse_int`, `parse_usd`, `decode_js_string`, `first_query_value`) | Extracted from `monitor.py` |
| `_fetch.py` | Rate-limited HTTP fetching with exponential backoff retry | New |
| `_external.py` | Shared Level.Travel / Travelata extraction (hotel name, min price) | Extracted from `monitor.py` |
| `bgoperator.py` | Biblio-Globus offer parsing + hotel name extraction | Extracted from `monitor.py` |
| `leveltravel.py` | Level.Travel external price parsing | New thin wrapper |
| `travelata.py` | Travelata external price parsing | New thin wrapper |

### Backward-compatible wrappers in `monitor.py`

All 6 public parsing functions now delegate to `parsers/`:
- `parse_offers()` → `parsers.bgoperator.parse_offers()`
- `extract_hotel_name()` → `parsers.bgoperator.extract_hotel_name()`
- `parse_external_price()` → `parsers.leveltravel` / `parsers.travelata`
- `extract_external_hotel_name()` → `parsers._external`
- `extract_external_min_price()` → `parsers._external`
- `fetch_html()` → `parsers._fetch.fetch_with_retry()` with rate limiting

Zero breaking changes — all 58 existing tests pass without modification.

### Rate limits + retry (PROV-03)

- Per-provider cooldown: 10s between requests (configurable via `rate_limit_seconds`)
- Exponential backoff: 1s → 2s → 4s on 5xx/429/connection errors
- Max 3 retries before giving up
- All providers share the same `_fetch.fetch_with_retry()` helper

### HTML fixtures (PROV-01)

3 fixture files in `tests/fixtures/`:
- `bgoperator.html` — typical offer row
- `leveltravel.html` — JSON-LD hotel + minPrice script
- `travelata.html` — title + minPrice script

### New tests (6 in `tests/test_parsers.py`)

- Parser extraction: bgoperator, leveltravel, travelata (4 tests)
- Rate limit enforcement (1 test)
- Retry backoff behavior (1 test)

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `price_monitor/parsers/__init__.py` | New | +55 |
| `price_monitor/parsers/_fetch.py` | New | +85 |
| `price_monitor/parsers/_external.py` | New | +50 |
| `price_monitor/parsers/bgoperator.py` | New | +70 |
| `price_monitor/parsers/leveltravel.py` | New | +15 |
| `price_monitor/parsers/travelata.py` | New | +15 |
| `price_monitor/monitor.py` | 6 function bodies → delegates | -110 / +20 |
| `tests/fixtures/*.html` | 3 fixture files | +30 |
| `tests/test_parsers.py` | 6 new tests | +115 |

## Requirements Satisfied

- [x] PROV-01: HTML fixtures for all 3 providers
- [x] PROV-02: Modular parser package
- [x] PROV-03: Rate limits + retry budgets
