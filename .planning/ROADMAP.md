# Roadmap: Personal Tour Price Tracker Bot

## Milestones

| Milestone | Status | Phases | Tests | Shipped |
|-----------|--------|--------|-------|---------|
| v1.0 MVP | ✅ Shipped | 5 | 58 | 2026-05-03 |
| v2.0 Production Hardening | ✅ Shipped | 3 | 72 | 2026-05-04 |
| v3.0 Competition & Discovery | ✅ Shipped | 3 | 87 | 2026-05-04 |
| v4.0 Tech Debt Cleanup | ✅ Shipped | 1 | 87 | 2026-05-04 |
| v5.0 Recommendation & Polish | ✅ Shipped | 2 | 89 | 2026-05-04 |
| v5.1 Weekly Summary | ✅ Shipped | 1 | 89 | 2026-05-05 |

**Status: All milestones complete.** No active phase. Next milestone undefined.

### Phase 1: SQLite State and Single-Container Foundation — v1.0 ✅

### Phase 2: Admin Telegram Control UI and Authorization — v1.0 ✅

### Phase 3: Price Tracking Summaries and Target Alerts — v1.0 ✅

### Phase 4: Duration Anomaly Analytics — v1.0 ✅

### Phase 5: Currency Early Warnings and Operational Hardening — v1.0 ✅

### Phase 1: Provider Hardening — v2.0 ✅

### Phase 2: Analytics & Insights — v2.0 ✅

### Phase 3: Operations — v2.0 ✅

### Phase 4: Cross-Provider Comparison — v3.0 ✅

### Phase 5: New Arrivals Detection — v3.0 ✅

### Phase 6: GHCR Publishing — v3.0 ✅

### Phase 7: Tech Debt Cleanup — v4.0 ✅

### Phase 8: AI Recommendation Engine — v5.0 ✅

### Phase 9: Report Polish — v5.0 ✅

---

## v1.0 MVP

<details>
<summary>✅ v1.0 MVP — SHIPPED 2026-05-03 (5 phases, 7 plans, 58 tests)</summary>

- [x] Phase 1: SQLite State and Single-Container Foundation
- [x] Phase 2: Admin Telegram Control UI and Authorization
- [x] Phase 3: Price Tracking Summaries and Target Alerts
- [x] Phase 4: Duration Anomaly Analytics
- [x] Phase 5: Currency Early Warnings and Operational Hardening

</details>

## v2.0 Production Hardening

<details>
<summary>✅ v2.0 — SHIPPED 2026-05-04 (3 phases, 3 plans, 72 tests)</summary>

- [x] Phase 1: Provider Hardening — Real HTML fixtures, modular parsers (`price_monitor/parsers/`), rate limits + retry
- [x] Phase 2: Analytics & Insights — Weekly price charts (matplotlib), trend summaries, retention, anomaly presets
- [x] Phase 3: Operations — Docker healthcheck, backup/restore docs, CI pipeline

</details>

## v3.0 Competition & Discovery

<details>
<summary>✅ v3.0 — SHIPPED 2026-05-04 (3 phases, 3 plans, 87 tests)</summary>

- [x] Phase 4: Cross-provider comparison — Fuzzy hotel matching, comparison block in reports
- [x] Phase 5: New arrivals detection — Alerts for new departure dates and hotel/room combos
- [x] Phase 6: GHCR — CI publishes Docker image to GitHub Container Registry

</details>

## v4.0 Tech Debt Cleanup

<details>
<summary>✅ v4.0 — SHIPPED 2026-05-04 (1 phase, 1 plan, 87 tests)</summary>

- [x] Phase 7: SQLite WAL mode, periodic VACUUM, legacy JSON path removal, Telegram retry with exponential backoff

</details>

## v5.0 Recommendation & Polish

<details>
<summary>✅ v5.0 — SHIPPED 2026-05-04 (2 phases, 2 plans, 89 tests)</summary>

- [x] Phase 8: AI Recommendation Engine — buy/wait/hold verdicts, reference price, min-checks threshold
- [x] Phase 9: Report Polish — Compact format, dedup prices, auto-competitor search, cross-hotel comparison, trend report

</details>

## v5.1 Weekly Summary

<details>
<summary>✅ v5.1 — SHIPPED 2026-05-05 (1 phase, 1 plan, 89 tests)</summary>

- [x] Phase: Weekly price summary report with aggregated insights

</details>

---

*Last updated: 2026-05-06*
