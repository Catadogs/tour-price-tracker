# Milestones

## v1.0 Personal Tour Price Tracker MVP (Shipped: 2026-05-03)

**Phases completed:** 5 phases, 7 plans

**Key accomplishments:**
- Stdlib SQLite storage with one-time JSON migration, append-only price history, corrupt DB quarantine
- Telegram admin UI with inline keyboards, settings management, fail-secure authorization
- Price tracking: scheduled/manual checks, target alerts, historical minimums, adaptive intervals
- Duration anomaly detection: generalized pairwise night comparison across all departure dates
- Currency monitoring: USD/RUB + EUR/RUB via CBR, preemptive Telegram warnings

---

## v3.0 Competition & Discovery (Shipped: 2026-05-04)

**Phases completed:** 3 phases, 3 plans, 87 tests

**Key accomplishments:**
- Cross-provider comparison: fuzzy hotel matching + comparison block in reports
- New arrivals detection: alerts for new departure dates and new hotel/room combos
- GHCR: CI publishes Docker image to GitHub Container Registry

---

## v5.0 Recommendation & Polish (Shipped: 2026-05-04)

**Phases completed:** 2 phases, 2 plans, 89 tests

**Key accomplishments:**
- AI recommendation engine: buy/wait/hold verdicts with min-checks threshold
- Reference price setting for comparison against user expectations
- Report polish: compact format, dedup prices, auto-competitor search
- Cross-hotel comparison when multiple BG searches active

---

## v4.0 Tech Debt Cleanup (Shipped: 2026-05-04)

**Phases completed:** 1 phase, 1 plan, 87 tests

**Key accomplishments:**
- SQLite WAL mode enabled for better concurrent read/write
- Periodic VACUUM (weekly) for database compaction
- Legacy JSON path fields removed from MonitorConfig (now optional)
- Telegram API retry with exponential backoff on 5xx/network errors

**Started:** 2026-05-04

**Phases planned:** 3 phases, 6 requirements

**Target features:**
- Cross-provider comparison: matching hotels across BG, Level.Travel, Travelata with fuzzy names
- New arrivals: alerts for new departure dates and new hotel/room combinations
- GHCR: CI publishes Docker image to GitHub Container Registry

---

## v2.0 Production Hardening (Shipped: 2026-05-04)

**Started:** 2026-05-03

**Phases planned:** 3 phases, 10 requirements

**Target features:**
- Provider hardening: real HTML fixtures, modular parsers (`price_monitor/parsers/`), rate limits + retry
- Analytics: weekly price charts (matplotlib → Telegram), trend summaries, retention, anomaly presets
- Operations: Docker healthcheck, backup/restore docs, CI pipeline
