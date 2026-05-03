---
phase: 01-sqlite-state-and-single-container-foundation
plan: 01
subsystem: database
tags: [sqlite, storage, migration, pytest]
requires: []
provides:
  - SQLite schema initialization for metadata, runtime settings, latest snapshots, and price history
  - One-time legacy JSON import guarded by metadata.json_import_completed
  - Path-based storage API for settings, snapshots, append-only price history, and corrupt DB quarantine
affects: [monitor-runtime-storage, docker-runtime-storage, telegram-settings]
tech-stack:
  added: []
  patterns:
    - stdlib sqlite3 with short-lived explicitly closed connections
    - module-level threading.RLock for write serialization
    - typed lookup columns plus JSON payload compatibility
key-files:
  created:
    - price_monitor/storage.py
    - tests/test_storage.py
  modified: []
key-decisions:
  - "Used stdlib sqlite3 with default journaling and busy_timeout instead of adding an ORM or external database service."
  - "Kept JSON reads only in initialize_storage as one-time migration inputs guarded by metadata.json_import_completed."
  - "Added a SQLite header preflight before corrupt DB quarantine so WAL/SHM sidecars can be preserved before sqlite3 touches them on Windows."
patterns-established:
  - "Storage functions accept Path values directly and avoid importing MonitorConfig."
  - "Snapshot and history rows store indexed typed columns plus the original payload_json for compatibility."
requirements-completed: [STOR-01, STOR-02, STOR-03, STOR-04, OPS-04, QUAL-02]
duration: 7 min
completed: 2026-05-03
---

# Phase 01 Plan 01: SQLite Storage Foundation Summary

**Stdlib SQLite storage facade with one-time JSON migration, append-only price history, and corrupt database quarantine**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-03T10:26:51Z
- **Completed:** 2026-05-03T10:33:51Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `price_monitor/storage.py` with idempotent schema creation for `metadata`, `runtime_settings`, `latest_snapshots`, and `price_history`.
- Implemented one-time legacy JSON import for settings, latest snapshots, and history using `metadata.json_import_completed`.
- Added runtime settings, latest snapshot, and append-only price history APIs that round-trip the existing compatibility shapes.
- Added corrupt SQLite quarantine that renames the bad DB and sidecars with `.corrupt-YYYYMMDDHHMMSS`, then initializes a replacement database.
- Added focused `tests/test_storage.py` coverage for initialization, migration, persistence, malformed JSON, and corruption handling.

## Task Commits

TDD produced RED and GREEN commits for each task:

1. **Task 1: Build SQLite schema and initialization path**
   - `82dace6` test: add failing storage initialization tests
   - `f3b8d51` feat: initialize sqlite storage schema
2. **Task 2: Implement legacy JSON import and persistence operations**
   - `43c7e67` test: add failing sqlite persistence tests
   - `19a5478` feat: implement sqlite migration persistence
3. **Task 3: Add corrupt database quarantine fallback**
   - `b875805` test: add failing corrupt db quarantine test
   - `42b87c6` feat: quarantine corrupt sqlite databases

## Files Created/Modified

- `price_monitor/storage.py` - SQLite schema, connection helper, migration import, persistence API, and corrupt DB quarantine.
- `tests/test_storage.py` - Focused storage tests for fresh DB setup, one-time import, round trips, append-only history, malformed JSON, and corruption recovery.

## Decisions Made

- Used only Python stdlib `sqlite3`; no ORM, migration framework, broker, worker, or external database was added.
- Used default SQLite journaling with `busy_timeout` and explicit sidecar quarantine support rather than enabling WAL in this plan.
- Kept the storage module independent from `MonitorConfig`; integration remains for the next plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Explicitly closed sqlite connections before quarantine**
- **Found during:** Task 3 (Add corrupt database quarantine fallback)
- **Issue:** On Windows, `sqlite3.Connection` used as a context manager commits or rolls back but does not close the file handle, so the corrupt database stayed locked when rename was attempted.
- **Fix:** Added a `_connection()` context helper that wraps the transaction and closes every short-lived connection in `finally`.
- **Files modified:** `price_monitor/storage.py`
- **Verification:** `python -m pytest tests/test_storage.py -q` passed.
- **Committed in:** `42b87c6`

**2. [Rule 1 - Bug] Added header preflight to preserve corrupt DB sidecars**
- **Found during:** Task 3 (Add corrupt database quarantine fallback)
- **Issue:** Opening a clearly invalid database with sqlite3 could remove or alter fake WAL/SHM sidecars before quarantine assertions ran.
- **Fix:** Added a small SQLite file-header preflight so obviously non-SQLite files are quarantined before sqlite3 opens them.
- **Files modified:** `price_monitor/storage.py`
- **Verification:** `python -m pytest tests/test_storage.py -q` passed and static sidecar handling search matched.
- **Committed in:** `42b87c6`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bug fixes)
**Impact on plan:** Both fixes were needed for reliable corrupt database quarantine on Windows and did not expand scope.

## Issues Encountered

- PowerShell in this environment did not support `Get-Date -AsUTC`; switched to `(Get-Date).ToUniversalTime().ToString(...)` for timestamps.
- A static `Select-String` command with quoted brace patterns was malformed; reran the acceptance check with simpler PowerShell-safe patterns.
- Existing unrelated untracked and modified files are present from parallel execution. This plan staged and committed only `price_monitor/storage.py`, `tests/test_storage.py`, and this summary.

## User Setup Required

None - no external service configuration required.

## Verification

- `python -m pytest tests/test_storage.py -q` -> 9 passed.
- Static acceptance searches confirmed required table DDL, sqlite connection usage, write lock, JSON import/persistence operations, `ON CONFLICT`, append-only history inserts, quick check, corrupt suffix, and sidecar handling.
- Forbidden dependency search for `sqlalchemy|alembic|redis|celery|psycopg|mysql` returned no matches in `price_monitor/storage.py`.
- Stub scan for placeholder/TODO/FIXME patterns in plan-owned files returned no matches.

## Next Phase Readiness

The storage foundation is ready for the monitor integration plan. `monitor.py` can call `initialize_storage()` on startup and route runtime settings, latest snapshots, and price history through this path-based API.

## Self-Check: PASSED

- Found `price_monitor/storage.py`.
- Found `tests/test_storage.py`.
- Found `.planning/phases/01-sqlite-state-and-single-container-foundation/01-01-SUMMARY.md`.
- Found task commits `82dace6`, `f3b8d51`, `43c7e67`, `19a5478`, `b875805`, and `42b87c6`.

---
*Phase: 01-sqlite-state-and-single-container-foundation*
*Completed: 2026-05-03*
