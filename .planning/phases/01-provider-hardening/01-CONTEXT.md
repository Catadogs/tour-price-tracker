# Phase 1: Provider Hardening — Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 hardens the provider layer: stored HTML fixtures replace inline mocks, parsers split into focused modules, and per-provider rate limits with retry budgets are added. No new features — this is a maintainability and reliability upgrade of existing parsing infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Fixtures (PROV-01)
- **D-01:** Store HTML fixtures in `tests/fixtures/` — standard pytest convention, keeps test data with tests.
- **D-02:** One fixture per provider (3 total) covering the typical page structure. Up to 5 hotel-specific fixtures can be added later.
- **D-03:** Fixtures are committed real HTML (sanitized — no secrets), used by tests instead of inline HTML strings.

### Parser structure (PROV-02)
- **D-04:** Create `price_monitor/parsers/` package with flat function modules: `bgoperator.py`, `leveltravel.py`, `travelata.py`.
- **D-05:** Each module exports the same function signatures currently in `monitor.py`: `parse_offers()` for Biblio-Globus, `parse_external_price()` for Level/Travelata.
- **D-06:** Backward compatibility: keep `parse_offers()` and `parse_external_price()` in `monitor.py` as thin wrappers that delegate to the new modules. Existing imports don't break.
- **D-07:** Existing inline HTML in tests replaced with fixture file loading (`Path.read_text()`).

### Rate limits (PROV-03)
- **D-08:** Minimum 1 hour between full check cycles (existing behavior, unchanged).
- **D-09:** Between individual provider requests within one check: minimum 10 seconds cooldown per provider.
- **D-10:** Rate limit enforced via simple timestamp tracking — `_last_request_time: dict[str, float]` per provider.
- **D-11:** Configurable via env vars: `BG_RATE_LIMIT_BGOPERATOR`, `BG_RATE_LIMIT_LEVELTRAVEL`, `BG_RATE_LIMIT_TRAVELATA` (default 10s each).

### Retry strategy (PROV-03)
- **D-12:** 3 retry attempts on HTTP 5xx, 429, or connection errors.
- **D-13:** Exponential backoff: 1s → 2s → 4s between retries.
- **D-14:** Retry logic lives in a shared helper `parsers/_fetch.py` — thin wrapper around `requests.get` used by all parsers.
- **D-15:** After 3 failures, log the error and return empty/no results (don't crash the main loop).

### Backward compatibility
- **D-16:** `monitor.py` keeps `parse_offers()`, `parse_external_price()`, `fetch_html()` as wrappers delegating to new modules.
- **D-17:** `provider_from_url()`, `is_bgoperator_url()`, `extract_hotel_name()`, `extract_external_hotel_name()`, `extract_external_min_price()` also kept as wrappers.
- **D-18:** `run_check()` unchanged — it uses the wrappers which now delegate internally.

</decisions>

<requirements>
## Requirements Covered

- [ ] **PROV-01**: Stored real-world HTML fixtures
- [ ] **PROV-02**: Modular parser modules
- [ ] **PROV-03**: Per-provider rate limits and retry budgets
</requirements>
