# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-03)

**Core value:** The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.
**Current focus:** Phase 1 - SQLite State and Single-Container Foundation

## Current Position

Phase: 1 of 5 (SQLite State and Single-Container Foundation)
Plan: TBD in current phase
Status: Ready to plan
Last activity: 2026-05-03 - Roadmap created from v1 requirements and brownfield codebase context.

Progress: [----------] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. SQLite State and Single-Container Foundation | TBD | - | - |
| 2. Admin Telegram Control UI and Authorization | TBD | - | - |
| 3. Price Tracking Summaries and Target Alerts | TBD | - | - |
| 4. Duration Anomaly Analytics | TBD | - | - |
| 5. Currency Early Warnings and Operational Hardening | TBD | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Keep the product single-user/admin-only; avoid roles, accounts, or SaaS abstractions.
- Use SQLite for durable settings, latest snapshots, price history, and currency observations.
- Keep one process and one Docker container; no brokers, heavy databases, or separate workers.
- Use Telegram as the only v1 interface.
- Treat currency jumps as preemptive alerts because tour operator RUB repricing can lag exchange movement.

### Pending Todos

None yet.

### Blockers/Concerns

- `price_monitor/monitor.py` is large and high-blast-radius; phase plans should keep edits tightly scoped.
- Current tests fail because `MonitorConfig` test construction is out of sync with added fields.
- Telegram control is open when `TELEGRAM_CHAT_ID` is unset.
- Provider URL allowlisting uses substring matching and must reject lookalike domains.
- JSON persistence is non-atomic today; Phase 1 replaces normal-runtime JSON state with SQLite.
- Price history currently grows without pruning; SQLite history writes should avoid the whole-file rewrite pattern.

## Session Continuity

Last session: 2026-05-03
Stopped at: Roadmap and initial project state created.
Resume file: None
