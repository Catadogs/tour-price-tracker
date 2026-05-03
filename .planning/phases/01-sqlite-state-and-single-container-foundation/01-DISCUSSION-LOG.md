# Phase 1: SQLite State and Single-Container Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 1 - SQLite State and Single-Container Foundation
**Areas discussed:** Database path and env settings, JSON migration, SQLite schema, refactoring boundary, corrupt database behavior

---

## Area Selection

User selected all five proposed discussion areas by replying: "все 5".

## Database path and env settings

| Option | Description | Selected |
|--------|-------------|----------|
| A | Add `BG_DB_PATH=/data/price_monitor.sqlite3`; keep old JSON path env vars only for migration. | yes |
| B | Hard-code `/data/price_monitor.sqlite3` without env. | |
| C | Reuse old path env vars to derive the SQLite path. | |

**User's choice:** Not explicitly answered before plan-phase was invoked.
**Notes:** Recommended option A was applied as default so planning would have concrete context.

---

## JSON migration

| Option | Description | Selected |
|--------|-------------|----------|
| A | Import existing JSON files once on first SQLite initialization, record migration completion, then stop using JSON in normal runtime. | yes |
| B | Ignore JSON and start with a clean SQLite database. | |
| C | Keep reading JSON as fallback when SQLite rows are missing. | |

**User's choice:** Not explicitly answered before plan-phase was invoked.
**Notes:** Recommended option A was applied as default.

---

## SQLite schema

| Option | Description | Selected |
|--------|-------------|----------|
| A | Simple key/value JSON tables for settings, snapshots, and append-only history payloads. | |
| B | Mixed schema: typed/indexable columns for target/provider/date/nights/price plus JSON payload for details. | yes |
| C | Fully normalized schema with separate targets/offers/history/settings tables. | |

**User's choice:** Not explicitly answered before plan-phase was invoked.
**Notes:** Recommended option B was applied as default.

---

## Refactoring boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep all SQLite code inside `price_monitor/monitor.py`. | |
| B | Add focused `price_monitor/storage.py` for SQLite and migration only. | yes |
| C | Split config, service, persistence, parser, and Telegram modules immediately. | |

**User's choice:** Not explicitly answered before plan-phase was invoked.
**Notes:** Recommended option B was applied as default to reduce blast radius while avoiding further growth of `monitor.py`.

---

## Corrupt database behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | Fail fast so data loss is never hidden. | |
| B | Rename corrupt DB to `.corrupt-<timestamp>`, initialize an empty DB, log warning, and continue. | yes |
| C | Attempt partial recovery first, then fallback. | |

**User's choice:** Not explicitly answered before plan-phase was invoked.
**Notes:** Recommended option B was applied as default.

---

## the agent's Discretion

- Function names and exact DDL details are left to planner/executor as long as the schema supports the locked requirements.
- The planner may choose thin compatibility wrappers or direct call-site replacement.

## Deferred Ideas

- Telegram menu redesign and authorization: Phase 2.
- Summary/target alert behavior: Phase 3.
- Duration anomalies: Phase 4.
- Currency monitor tables and alerts: Phase 5.
