# Personal Tour Price Tracker Bot

## What This Is

Personal Tour Price Tracker Bot is a single-user Telegram bot for monitoring vacation tour prices, spotting price anomalies, and warning about currency-driven price hikes before operators recalculate RUB prices. The project is a personal admin-only tool, not a multi-user SaaS product.

v1.0 shipped: the existing Dockerized Python price monitor is now a durable, admin-controlled personal bot with SQLite storage, hardened Telegram authorization, readable price summaries, duration anomaly detection, and daily currency early-warning alerts.

## Core Value

The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.

## Requirements

### Validated

- ✓ Dockerized Python monitor exists and runs as a long-lived service via `docker/price-monitor/Dockerfile` and `docker-compose.yml`.
- ✓ Telegram Bot API integration exists for sending messages and handling inline controls in `price_monitor/monitor.py`.
- ✓ Biblio-Globus offer parsing exists through `parse_offers()` in `price_monitor/monitor.py`.
- ✓ External reference price parsing exists for Level.Travel and Travelata style pages through `parse_external_price()` in `price_monitor/monitor.py`.
- ✓ Runtime settings can be edited from Telegram and persisted through `TelegramControlBot` and settings helpers.
- ✓ Scheduled and manual checks exist through `main()`, `run_check()`, and Telegram `/check` handling.
- ✓ Target price alerts, price history, best-offer selection, and night-duration comparison logic exist in `price_monitor/monitor.py`.
- ✓ Docker volume persistence exists for runtime state under `/data`.
- ✓ Replace JSON-backed settings, snapshots, and price history with local SQLite while keeping the app monolithic. — v1.0 (Phase 1: `storage.py` facade, threading.RLock, idempotent schema init)
- ✓ Keep deployment simple: one Docker image, one application process, one mounted volume for the SQLite database. — v1.0 (Phase 1: `BG_DB_PATH` env var, single `bg-price-monitor` service)
- ✓ Harden single-user Telegram authorization so only the configured admin can change settings or trigger checks. — v1.0 (Phase 2: fail-secure `is_authorized`, exact-domain `_ALLOWED_HOSTS` frozenset)
- ✓ Improve Telegram inline menu for managing watched hotels, filters, departure dates, nights, target price, and check frequency. — v1.0 (Phase 2: SQLite-backed settings mutations through `apply_pending_action`)
- ✓ Send readable Telegram summaries with current best price, date and duration breakdown, and anomaly highlights. — v1.0 (Phase 3: `format_report`, `format_changes`, `format_new_minimums`)
- ✓ Trigger immediate Telegram alerts when the parsed minimum price is less than or equal to the configured target price. — v1.0 (Phase 3: `format_target_alerts`, 58 tests passing)
- ✓ Detect duration anomalies for the same departure date, including cases where more nights are cheaper or meaningfully better value. — v1.0 (Phase 4: `format_duration_anomalies` replacing hardcoded `format_strong_diff_line`)
- ✓ Monitor USD/RUB and EUR/RUB exchange rates daily and send preemptive warnings when a significant intraday jump may cause next-day tour price increases. — v1.0 (Phase 5: `price_monitor/currency.py`, CBR integration, `currency_observations` SQLite table)
- ✓ Preserve and expand test coverage around parsers, Telegram formatting, SQLite persistence, anomaly detection, and currency alerts. — v1.0 (58 tests across all subsystems)

### Active

- [ ] Add stored real-world HTML fixtures for Biblio-Globus, Level.Travel, and Travelata (PROV-01 — v2)
- [ ] Split provider-specific parsing into focused modules (PROV-02 — v2)
- [ ] Add trend charts or compact historical summaries in Telegram (ANLY-01 — v2)
- [ ] Add retention settings for historical prices (ANLY-02 — v2)
- [ ] Add Docker healthcheck or lightweight liveness signal (OPER-01 — v2)
- [ ] Document backup and restore commands for the SQLite volume (OPER-02 — v2)
- [ ] Add CI to run tests and build the Docker image (OPER-03 — v2)

### Out of Scope

- Multi-user accounts, roles, or per-user sessions — target audience is one admin.
- External message brokers such as RabbitMQ, Redis, Kafka, or Celery — background checks must run in the same process.
- Heavy databases such as PostgreSQL or MySQL — SQLite is the required storage layer.
- Separate worker containers or distributed services — deployment must stay as one app container plus mounted data volume.
- Public web dashboard — Telegram is the presentation interface for v1.
- Paid travel booking, checkout, or operator account integration — the bot monitors and alerts; it does not book tours.
- SQLite WAL mode / VACUUM scheduling — low-severity tech debt deferred to v2.

## Context

v1.0 shipped 2026-05-03. Codebase: ~3,247 LOC Python across `price_monitor/monitor.py`, `price_monitor/storage.py`, `price_monitor/currency.py`, and `tests/`. 58 tests pass. Tech stack: Python 3.11, SQLite (stdlib), requests, beautifulsoup4, Docker.

All concerns from initial planning are resolved:
- ✓ `MonitorConfig` test construction in sync with fields (Phase 1)
- ✓ URL allowlisting uses exact-domain `_ALLOWED_HOSTS` frozenset, not substring matching (Phase 2)
- ✓ JSON persistence replaced with atomic SQLite writes (Phase 1)
- ✓ Telegram access fails-secure when `TELEGRAM_CHAT_ID` unset (Phase 2)
- Price history pruning: deferred to v2 (ANLY-02)

Known tech debt (low-severity, v2):
- SQLite WAL mode not enabled
- No VACUUM scheduling
- Legacy `settings_path`/`state_path`/`history_path` fields in `MonitorConfig` kept for compatibility
- No retry logic for provider fetches or Telegram delivery

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
*Last updated: 2026-05-03 after v1.0 milestone*
