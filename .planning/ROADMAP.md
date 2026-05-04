# Roadmap: Personal Tour Price Tracker Bot

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-03)
- 🔵 **v2.0 Production Hardening** — Phases 1–3 (active)

---

## v2.0 Phases

### Phase 1: Provider Hardening
**Goal**: Parser tests use real stored fixtures instead of inline HTML mocks. Provider parsing is modular with per-provider rate limits and retry.

**Depends on**: v1.0 (shipped)
**Requirements**: PROV-01, PROV-02, PROV-03

**Success Criteria**:
1. Biblio-Globus, Level.Travel, and Travelata have stored HTML fixture files used by tests.
2. Parser logic is split into `price_monitor/parsers/bgoperator.py`, `leveltravel.py`, `travelata.py` with a shared base.
3. Each provider has configurable rate limit (min seconds between requests) and retry budget (max attempts on failure).
4. All existing 58 tests pass, new parser-specific tests added.

**Plans**: 1 plan
Plans:
- [x] 01-01-PLAN.md — Create parser package, fixtures, rate limits, retry, backward-compatible wrappers.

### Phase 2: Analytics & Insights
**Goal**: Admin receives weekly price charts, trend summaries, configurable anomaly presets, and auto-pruning of old price history.

**Depends on**: Phase 1
**Requirements**: ANLY-01, ANLY-02, ANLY-03, ANLY-04

**Success Criteria**:
1. Admin receives a PNG price chart once per week via Telegram with price history per search target and night duration.
2. Telegram `/trend` command shows compact price direction summaries.
3. Admin can select anomaly preset (conservative/balanced/aggressive) from Telegram settings.
4. Price history older than configurable retention days is auto-pruned.
5. matplotlib added to `requirements.txt`.

**Plans**: 1 plan
Plans:
- [x] 02-01-PLAN.md — Trend summaries, retention pruning, anomaly presets, weekly matplotlib chart.

### Phase 3: Operations
**Goal**: Docker healthcheck, documented backup/restore, and CI pipeline for tests and image builds.

**Depends on**: Phase 2
**Requirements**: OPER-01, OPER-02, OPER-03

**Success Criteria**:
1. `docker compose ps` shows healthy status for the container.
2. `README.md` includes backup/restore commands for the SQLite volume.
3. CI config (GitHub Actions or similar) runs `pytest` and builds Docker image on push.

**Plans**: TBD

**Plans**: 1 plan
Plans:
- [x] 03-01-PLAN.md — Docker HEALTHCHECK, backup/restore docs, GitHub Actions CI pipeline.

---

## v1.0 Phases (Shipped)

<details>
<summary>✅ v1.0 MVP — SHIPPED 2026-05-03 (5 phases, 7 plans, 58 tests)</summary>

- [x] Phase 1: SQLite State and Single-Container Foundation
- [x] Phase 2: Admin Telegram Control UI and Authorization
- [x] Phase 3: Price Tracking Summaries and Target Alerts
- [x] Phase 4: Duration Anomaly Analytics
- [x] Phase 5: Currency Early Warnings and Operational Hardening

</details>

## Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Provider Hardening | v2.0 | 1/1 | Complete |
| 2. Analytics & Insights | v2.0 | 1/1 | Complete |
| 3. Operations | v2.0 | 1/1 | Complete |
