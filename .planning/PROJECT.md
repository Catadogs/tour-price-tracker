# Personal Tour Price Tracker Bot

## What This Is

Personal Tour Price Tracker Bot is a single-user Telegram bot for monitoring vacation tour prices, spotting price anomalies, and warning about currency-driven price hikes before operators recalculate RUB prices. The project is a personal admin-only tool, not a multi-user SaaS product.

The existing codebase already runs as a Dockerized Python price monitor with Telegram controls and provider parsing. This project turns that working monitor into a more durable, user-friendly personal tour tracking bot with SQLite storage, richer Telegram settings, anomaly analytics, and daily currency monitoring.

## Core Value

The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.

## Requirements

### Validated

- ✓ Dockerized Python monitor exists and runs as a long-lived service via `docker/price-monitor/Dockerfile` and `docker-compose.yml`.
- ✓ Telegram Bot API integration exists for sending messages and handling inline controls in `price_monitor/monitor.py`.
- ✓ Biblio-Globus offer parsing exists through `parse_offers()` in `price_monitor/monitor.py`.
- ✓ External reference price parsing exists for Level.Travel and Travelata style pages through `parse_external_price()` in `price_monitor/monitor.py`.
- ✓ Runtime settings can be edited from Telegram and persisted to JSON through `TelegramControlBot` and settings helpers in `price_monitor/monitor.py`.
- ✓ Scheduled and manual checks exist through `main()`, `run_check()`, and Telegram `/check` handling in `price_monitor/monitor.py`.
- ✓ Target price alerts, price history, best-offer selection, and night-duration comparison logic already exist in `price_monitor/monitor.py`.
- ✓ Docker volume persistence already exists for runtime state under `/data`.

### Active

- [ ] Replace JSON-backed settings, snapshots, and price history with local SQLite while keeping the app monolithic.
- [ ] Keep deployment simple: one Docker image, one application process, one mounted volume for the SQLite database.
- [ ] Improve Telegram inline menu for managing watched hotels, filters, departure dates, nights, target price, and check frequency.
- [ ] Send readable Telegram summaries with current best price, date and duration breakdown, and anomaly highlights.
- [ ] Trigger immediate Telegram alerts when the parsed minimum price is less than or equal to the configured target price.
- [ ] Detect duration anomalies for the same departure date, including cases where more nights are cheaper or meaningfully better value.
- [ ] Monitor USD/RUB and EUR/RUB exchange rates daily and send preemptive warnings when a significant intraday jump may cause next-day tour price increases.
- [ ] Harden single-user Telegram authorization so only the configured admin can change settings or trigger checks.
- [ ] Preserve and expand test coverage around parsers, Telegram formatting, SQLite persistence, anomaly detection, and currency alerts.

### Out of Scope

- Multi-user accounts, roles, or per-user sessions — target audience is one admin.
- External message brokers such as RabbitMQ, Redis, Kafka, or Celery — background checks must run in the same process.
- Heavy databases such as PostgreSQL or MySQL — SQLite is the required storage layer.
- Separate worker containers or distributed services — deployment must stay as one app container plus mounted data volume.
- Public web dashboard — Telegram is the presentation interface for v1.
- Paid travel booking, checkout, or operator account integration — the bot monitors and alerts; it does not book tours.

## Context

The current codebase is a brownfield Python project centered on `price_monitor/monitor.py`. It already includes configuration parsing, provider fetching, HTML parsing, offer filtering, history tracking, Telegram polling, Telegram formatting, JSON persistence, and the main check loop in one module.

Existing runtime state is JSON-based:

- `MonitorConfig.settings_path`, defaulting to `/data/settings.json`
- `MonitorConfig.state_path`, defaulting to `/data/last_snapshot.json`
- `MonitorConfig.history_path`, defaulting to `/data/price_history.json`

The project should migrate those concepts into SQLite without introducing a heavy database or external process. The monolith constraint is intentional: this is a personal bot, and operational simplicity matters more than horizontal scalability.

Known codebase concerns from `.planning/codebase/CONCERNS.md` should shape the roadmap:

- `price_monitor/monitor.py` is large and high-blast-radius.
- Current tests fail because `MonitorConfig` test construction is out of sync with added fields.
- URL allowlisting uses substring matching and should be hardened.
- JSON persistence is non-atomic and vulnerable to corruption.
- Telegram access is open if `TELEGRAM_CHAT_ID` is unset.
- Price history grows without pruning.

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
| Keep the product single-user/admin-only | The bot is personal automation, not a SaaS product; avoiding roles and sessions keeps scope low. | — Pending |
| Use SQLite for durable state | JSON persistence is fragile and does not fit growing price history; SQLite satisfies local storage without heavy infrastructure. | — Pending |
| Keep one process and one container | Operational simplicity is a strict requirement and enough for personal monitoring load. | — Pending |
| Use Telegram as the only v1 UI | The user requested push notifications and inline menus; a web dashboard would add scope without core value. | — Pending |
| Treat currency jumps as preemptive alerts | Tour operator RUB repricing can lag exchange movement; early warnings help the admin act before the next-day hike. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-03 after initialization*
