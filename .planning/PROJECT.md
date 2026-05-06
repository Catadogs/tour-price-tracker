# Personal Tour Price Tracker Bot

## What This Is

Personal Tour Price Tracker Bot is a single-user Telegram bot for monitoring vacation tour prices, spotting price anomalies, and warning about currency-driven price hikes before operators recalculate RUB prices. The project is a personal admin-only tool, not a multi-user SaaS product.

All six milestones shipped (v1.0 — v5.1): the bot provides durable SQLite storage, hardened Telegram authorization, readable price summaries, duration anomaly detection, daily currency early-warning alerts, cross-provider comparison, AI-powered recommendation engine, and weekly summary reports. 89 tests pass.

## Core Value

The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.

## Requirements

### Shipped (v1.0 — v5.1)

- ✓ Dockerized Python monitor exists and runs as a long-lived service via `docker/price-monitor/Dockerfile` and `docker-compose.yml`.
- ✓ Telegram Bot API integration exists for sending messages and handling inline controls in `price_monitor/monitor.py`.
- ✓ Biblio-Globus offer parsing exists through `parse_offers()` in `price_monitor/monitor.py`.
- ✓ External reference price parsing exists for Level.Travel and Travelata style pages through `parse_external_price()` in `price_monitor/monitor.py`.
- ✓ Runtime settings can be edited from Telegram and persisted through `TelegramControlBot` and settings helpers.
- ✓ Scheduled and manual checks exist through `main()`, `run_check()`, and Telegram `/check` handling.
- ✓ Target price alerts, price history, best-offer selection, and night-duration comparison logic exist in `price_monitor/monitor.py`.
- ✓ Docker volume persistence exists for runtime state under `/data`.
- ✓ SQLite storage with threading.RLock, idempotent schema init, WAL mode, periodic VACUUM — v1.0 + v4.0
- ✓ Single Docker image, one application process, one mounted volume for the SQLite database — v1.0
- ✓ Fail-secure Telegram authorization with exact-domain `_ALLOWED_HOSTS` frozenset — v1.0/v2.0
- ✓ SQLite-backed settings mutations through `apply_pending_action` — v1.0/v2.0
- ✓ Readable Telegram summaries with best price, date/duration breakdown, anomaly highlights — v1.0
- ✓ Target price alerts when parsed minimum falls below configured target — v1.0
- ✓ Generalized pairwise duration anomaly detection — v1.0
- ✓ CBR currency monitoring (USD/RUB, EUR/RUB) with preemptive Telegram warnings — v1.0
- ✓ Real HTML fixtures for Biblio-Globus, Level.Travel, Travelata — v2.0
- ✓ Modular parsers in `price_monitor/parsers/` — v2.0
- ✓ Per-provider rate limits and retry budgets — v2.0
- ✓ Trend summaries, retention pruning, anomaly presets — v2.0
- ✓ Weekly price charts (matplotlib → Telegram) — v2.0
- ✓ Docker healthcheck — v2.0
- ✓ Backup/restore documentation — v2.0
- ✓ CI pipeline (tests + Docker build) — v2.0
- ✓ Cross-provider comparison with fuzzy hotel matching — v3.0
- ✓ New arrivals detection (departure dates, hotel/room combos) — v3.0
- ✓ GHCR Docker image publishing — v3.0
- ✓ SQLite WAL mode, periodic VACUUM, Telegram retry with backoff — v4.0
- ✓ AI recommendation engine (buy/wait/hold verdicts) — v5.0
- ✓ Report polish, auto-competitor search, cross-hotel comparison — v5.0
- ✓ Weekly summary reports — v5.1

### Out of Scope

- Multi-user accounts, roles, or per-user sessions — target audience is one admin.
- External message brokers such as RabbitMQ, Redis, Kafka, or Celery — background checks must run in the same process.
- Heavy databases such as PostgreSQL or MySQL — SQLite is the required storage layer.
- Separate worker containers or distributed services — deployment must stay as one app container plus mounted data volume.
- Public web dashboard — Telegram is the presentation interface.
- Paid travel booking, checkout, or operator account integration — the bot monitors and alerts; it does not book tours.

## Context

All six milestones shipped (v1.0 — v5.1). 89 tests pass. No active phase.

All concerns from initial planning are resolved:
- ✓ `MonitorConfig` test construction in sync with fields
- ✓ URL allowlisting uses exact-domain `_ALLOWED_HOSTS` frozenset, not substring matching
- ✓ JSON persistence replaced with atomic SQLite writes
- ✓ Telegram access fails-secure when `TELEGRAM_CHAT_ID` unset
- ✓ Price history pruning: implemented (v2.0)
- ✓ SQLite WAL mode: enabled (v4.0)
- ✓ VACUUM scheduling: weekly (v4.0)
- ✓ Legacy JSON path fields: removed from MonitorConfig (v4.0)
- ✓ Telegram retry: 3 attempts with backoff (v4.0)

## Constraints

- **Audience**: Single admin user only — avoid multi-user abstractions unless needed for Telegram authorization.
- **Architecture**: Monolith — keep checks, Telegram polling, parsing, and scheduling in one application process.
- **Storage**: SQLite — use a local database file mounted through Docker volume for settings and price history.
- **Background work**: Same process — use existing loop, `asyncio`, `threading`, or APScheduler-style scheduling, but no Celery or separate workers.
- **Deployment**: Single Dockerfile and mounted volume — keep deployment understandable and portable.
- **Security**: Admin-only Telegram control — settings changes and URL additions must require explicit admin authorization.
- **Provider fragility**: HTML parsers are brittle — parser changes need fixture-based tests and clear failure reporting.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep the product single-user/admin-only | The bot is personal automation, not a SaaS product; avoiding roles and sessions keeps scope low. | ✓ Confirmed — fail-secure auth with single `TELEGRAM_CHAT_ID` works cleanly |
| Use SQLite for durable state | JSON persistence is fragile and does not fit growing price history; SQLite satisfies local storage without heavy infrastructure. | ✓ Confirmed — `storage.py` facade with threading.RLock, zero JSON runtime dependency |
| Keep one process and one container | Operational simplicity is a strict requirement and enough for personal monitoring load. | ✓ Confirmed — single `bg-price-monitor` service, BG_DB_PATH mounted volume |
| Use Telegram as the only v1 UI | The user requested push notifications and inline menus; a web dashboard would add scope without core value. | ✓ Confirmed — inline keyboards + formatted Markdown reports cover admin needs |
| Treat currency jumps as preemptive alerts | Tour operator RUB repricing can lag exchange movement; early warnings help the admin act before the next-day hike. | ✓ Confirmed — `currency.py` monitors CBR daily, alerts at configurable threshold |
| Generalize duration anomaly detection | Hardcoded 12/13-night comparison was brittle; `format_duration_anomalies` compares all pairs. | ✓ Confirmed — Phase 4 replaced `format_strong_diff_line` with generic pairwise comparator |

---
*Last updated: 2026-05-06*
