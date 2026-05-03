# Milestones

## v1.0 Personal Tour Price Tracker MVP (Shipped: 2026-05-03)

**Phases completed:** 5 phases, 7 plans, 10 tasks

**Key accomplishments:**

- Stdlib SQLite storage facade with one-time JSON migration, append-only price history, and corrupt database quarantine
- Monitor runtime now reads settings, latest snapshots, and append-only price history from SQLite through BG_DB_PATH.
- Single-container Docker runtime now exposes /data/price_monitor.sqlite3 as the SQLite state database and documents JSON files only as migration inputs.

---
