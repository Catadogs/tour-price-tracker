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

## v2.0 Production Hardening (Active)

**Started:** 2026-05-03

**Phases planned:** 3 phases, 10 requirements

**Target features:**
- Provider hardening: real HTML fixtures, modular parsers (`price_monitor/parsers/`), rate limits + retry
- Analytics: weekly price charts (matplotlib → Telegram), trend summaries, retention, anomaly presets
- Operations: Docker healthcheck, backup/restore docs, CI pipeline
