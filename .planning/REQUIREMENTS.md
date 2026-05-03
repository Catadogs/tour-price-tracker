# Requirements: Personal Tour Price Tracker Bot v2.0

**Defined:** 2026-05-03
**Milestone:** v2.0 Production Hardening
**Core Value:** The bot must be stable, maintainable, and provide visual price insights — not just text alerts.

## v2.0 Requirements

### Providers

- [ ] **PROV-01**: Add stored real-world HTML fixtures for Biblio-Globus, Level.Travel, and Travelata so parser tests run without network requests.
- [ ] **PROV-02**: Split provider-specific parsing into focused modules (`price_monitor/parsers/`) once the SQLite and alerting migration is stable.
- [ ] **PROV-03**: Add per-provider rate limits and retry budgets to avoid hammering tour operators and survive transient failures.

### Analytics

- [ ] **ANLY-01**: Add compact trend summaries in Telegram showing price direction over recent checks.
- [ ] **ANLY-02**: Add retention settings for historical prices — auto-prune records older than N days.
- [ ] **ANLY-03**: Add configurable anomaly presets: conservative, balanced, aggressive — each with different threshold defaults.
- [ ] **ANLY-04**: Send a weekly price change chart (PNG) to Telegram via `sendPhoto`, generated with matplotlib — showing price history per search target and night duration.

### Operations

- [ ] **OPER-01**: Add a Docker healthcheck or lightweight liveness signal so orchestrators can detect a stuck container.
- [ ] **OPER-02**: Document backup and restore commands for the SQLite volume.
- [ ] **OPER-03**: Add CI pipeline to run tests and build the Docker image on push.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 1 | Pending |
| PROV-02 | Phase 1 | Pending |
| PROV-03 | Phase 1 | Pending |
| ANLY-01 | Phase 2 | Pending |
| ANLY-02 | Phase 2 | Pending |
| ANLY-03 | Phase 2 | Pending |
| ANLY-04 | Phase 2 | Pending |
| OPER-01 | Phase 3 | Pending |
| OPER-02 | Phase 3 | Pending |
| OPER-03 | Phase 3 | Pending |

**Coverage:** 10/10 v2.0 requirements mapped, 0 orphaned.

---
*Requirements defined: 2026-05-03*
