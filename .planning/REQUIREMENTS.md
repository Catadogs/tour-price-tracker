# Requirements: Personal Tour Price Tracker Bot

**Defined:** 2026-05-03
**Last updated:** 2026-05-06
**Status:** All milestones shipped (v1.0 — v5.1). 89 tests pass.

---

## v2.0 Requirements (all shipped)

### Providers

- [x] **PROV-01**: Add stored real-world HTML fixtures for Biblio-Globus, Level.Travel, and Travelata so parser tests run without network requests.
- [x] **PROV-02**: Split provider-specific parsing into focused modules (`price_monitor/parsers/`) once the SQLite and alerting migration is stable.
- [x] **PROV-03**: Add per-provider rate limits and retry budgets to avoid hammering tour operators and survive transient failures.

### Analytics

- [x] **ANLY-01**: Add compact trend summaries in Telegram showing price direction over recent checks.
- [x] **ANLY-02**: Add retention settings for historical prices — auto-prune records older than N days.
- [x] **ANLY-03**: Add configurable anomaly presets: conservative, balanced, aggressive — each with different threshold defaults.
- [x] **ANLY-04**: Send a weekly price change chart (PNG) to Telegram via `sendPhoto`, generated with matplotlib — showing price history per search target and night duration.

### Operations

- [x] **OPER-01**: Add a Docker healthcheck or lightweight liveness signal so orchestrators can detect a stuck container.
- [x] **OPER-02**: Document backup and restore commands for the SQLite volume.
- [x] **OPER-03**: Add CI pipeline to run tests and build the Docker image on push.

## Traceability

| Requirement | Phase | Milestone | Status |
|-------------|-------|-----------|--------|
| PROV-01 | Phase 1 | v2.0 | Done |
| PROV-02 | Phase 1 | v2.0 | Done |
| PROV-03 | Phase 1 | v2.0 | Done |
| ANLY-01 | Phase 2 | v2.0 | Done |
| ANLY-02 | Phase 2 | v2.0 | Done |
| ANLY-03 | Phase 2 | v2.0 | Done |
| ANLY-04 | Phase 2 | v2.0 | Done |
| OPER-01 | Phase 3 | v2.0 | Done |
| OPER-02 | Phase 3 | v2.0 | Done |
| OPER-03 | Phase 3 | v2.0 | Done |

**Coverage:** 10/10 requirements shipped.

---

## Milestone Summary

| Milestone | Requirements | Status |
|-----------|-------------|--------|
| v1.0 MVP | 17 items | ✅ Shipped |
| v2.0 Production Hardening | 10 items | ✅ Shipped |
| v3.0 Competition & Discovery | 6 items | ✅ Shipped |
| v4.0 Tech Debt Cleanup | 4 items | ✅ Shipped |
| v5.0 Recommendation & Polish | 8 items | ✅ Shipped |
| v5.1 Weekly Summary | 1 item | ✅ Shipped |
