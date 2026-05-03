---
phase: 01-sqlite-state-and-single-container-foundation
plan: 02
subsystem: database
tags: [sqlite, monitor-runtime, persistence, pytest]

requires:
  - phase: 01-sqlite-state-and-single-container-foundation
    provides: SQLite storage facade from Plan 01-01
provides:
  - MonitorConfig.db_path loaded from BG_DB_PATH with /data/price_monitor.sqlite3 default
  - Monitor persistence wrappers backed by price_monitor.storage
  - run_check snapshot and append-only price history writes through SQLite
  - Runtime setting validation that skips malformed persisted values with warnings
affects:
  - monitor-runtime-storage
  - telegram-settings
  - scheduled-price-checks

tech-stack:
  added: []
  patterns:
    - Thin monitor.py wrappers call the storage facade using MonitorConfig.db_path
    - SQLite initialization happens once in main before bot polling or checks
    - Malformed runtime settings are ignored with logging.warning and env/default values preserved

key-files:
  created:
    - .planning/phases/01-sqlite-state-and-single-container-foundation/01-02-SUMMARY.md
  modified:
    - price_monitor/monitor.py
    - tests/test_price_monitor.py
    - .planning/codebase/ARCHITECTURE.md
    - .planning/codebase/STACK.md
    - .planning/codebase/CONVENTIONS.md

key-decisions:
  - "Kept storage integration as thin wrappers in monitor.py instead of refactoring parser, Telegram, or scheduler code."
  - "Kept legacy JSON path fields on MonitorConfig as migration inputs only while making BG_DB_PATH the runtime persistence path."
  - "Validated malformed persisted runtime settings inline in effective_config instead of adding Pydantic or a new config package."

patterns-established:
  - "Normal runtime uses load_snapshot(config), save_snapshot(config), load_price_history(config), and append_price_history(config, ...) against SQLite."
  - "Tests initialize SQLite explicitly with initialize_storage(config) before exercising monitor persistence helpers."

requirements-completed: [STOR-01, STOR-02, STOR-03, STOR-05, OPS-01, OPS-04, QUAL-01]

duration: 7 min
completed: 2026-05-03
---

# Phase 01 Plan 02: SQLite Monitor Runtime Summary

**Monitor runtime now reads settings, latest snapshots, and append-only price history from SQLite through BG_DB_PATH.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-03T10:39:13Z
- **Completed:** 2026-05-03T10:46:26Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `MonitorConfig.db_path` with `BG_DB_PATH` defaulting to `/data/price_monitor.sqlite3`.
- Added monitor-level `initialize_storage`, settings, snapshot, and price-history wrappers that call `price_monitor.storage`.
- Updated `main()` to initialize SQLite once before Telegram polling and scheduled checks.
- Updated `run_check()` to load snapshots/history from SQLite, append current observations to SQLite, and save latest snapshots to SQLite.
- Hardened `effective_config()` and `load_search_targets()` so malformed persisted settings are skipped without crashing the service.

## Task Commits

TDD produced RED and GREEN commits for each task:

1. **Task 1: Add BG_DB_PATH and SQLite-backed monitor wrappers**
   - `3157bdb` test: add failing sqlite monitor wrapper tests
   - `13243f1` feat: wire monitor wrappers to sqlite storage
2. **Task 2: Replace run_check persistence flow with SQLite append semantics**
   - `2c6f52a` test: add failing sqlite run_check persistence test
   - `34b5933` feat: persist run_check state in sqlite
3. **Task 3: Repair MonitorConfig tests and malformed settings handling**
   - `8545fe2` test: add failing malformed settings tests
   - `31a5ec0` feat: ignore malformed runtime settings

**Plan metadata:** pending final metadata commit

## Files Created/Modified

- `price_monitor/monitor.py` - Adds `db_path`, SQLite wrappers, startup initialization, run-check SQLite persistence, and malformed settings validation.
- `tests/test_price_monitor.py` - Repairs `MonitorConfig` construction and adds focused SQLite wrapper, run-check persistence, and malformed settings/search tests.
- `.planning/phases/01-sqlite-state-and-single-container-foundation/01-02-SUMMARY.md` - Records execution outcome, verification, deviations, and commits.
- `.planning/codebase/ARCHITECTURE.md` - Updates the generated codebase map from JSON runtime persistence to SQLite runtime persistence.
- `.planning/codebase/STACK.md` - Adds `BG_DB_PATH` and SQLite volume storage to the generated stack map.
- `.planning/codebase/CONVENTIONS.md` - Updates persistence wrapper parameter conventions to use `MonitorConfig`.

## Decisions Made

- Kept the monitor integration as a small caller-side layer over `price_monitor.storage`; no parser, Telegram, scheduler, provider, or deployment refactor was added.
- Preserved `state_path`, `settings_path`, and `history_path` on `MonitorConfig` only for storage initialization and legacy JSON migration input.
- Added simple conversion helpers in `monitor.py` for runtime setting validation rather than introducing Pydantic or a new config module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repaired stale MonitorConfig constructors during Task 1**
- **Found during:** Task 1 (Add BG_DB_PATH and SQLite-backed monitor wrappers)
- **Issue:** Task 1 required `tests/test_price_monitor.py` to pass, but existing tests instantiated `MonitorConfig` without fields required by the current config shape.
- **Fix:** Updated direct test constructors to include `db_path`, `target_price_rub`, and `history_path` while adding the RED tests for SQLite wrappers.
- **Files modified:** `tests/test_price_monitor.py`
- **Verification:** `python -m pytest tests/test_price_monitor.py -q` passed after Task 1 GREEN.
- **Committed in:** `3157bdb`

---

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking fix)
**Impact on plan:** The fix was required to satisfy Task 1 verification and matched Task 3's planned compatibility repair. No architecture or scope expansion.

## Issues Encountered

- `rg.exe` was present but returned Access denied in this workspace, so static searches used PowerShell `Select-String`.
- The run-check integration test initially hard-coded the localized primary target name; it was adjusted to assert the persisted snapshot key suffix and SQLite payload instead, avoiding the repo's existing encoding-sensitive literals.
- The worktree had unrelated pre-existing modified/untracked files such as `.planning/config.json`, `.claude/`, `.gitignore`, `docker/`, `price_monitor/__init__.py`, and `price_monitor/requirements.txt`. This plan staged only owned task and metadata files.

## User Setup Required

None - no external service configuration required.

## Verification

- `python -m pytest tests/test_price_monitor.py -q` -> 16 passed after Task 3.
- `python -m pytest -q` -> 25 passed.
- Static searches confirmed `BG_DB_PATH`, `db_path: Path`, `storage.initialize_storage`, `storage.load_runtime_settings`, `storage.save_runtime_settings`, `storage.load_snapshot`, `storage.save_snapshot`, `storage.load_price_history`, and `storage.append_price_history` in `price_monitor/monitor.py`.
- Static searches confirmed no `settings_path.read_text`, `settings_path.write_text`, `state_path.read_text`, `state_path.write_text`, `history_path.read_text`, or `history_path.write_text` normal-runtime JSON path usage in `monitor.py`.
- Static searches confirmed `append_price_history(active_config, current_snapshot, ts)` and `save_snapshot(active_config, current_snapshot)` in `run_check`.
- Static searches confirmed no normal-runtime `save_price_history(active_config.history_path` or `save_price_history(config.history_path` calls.
- Forbidden dependency search for `pydantic|BaseModel|sqlalchemy|celery|redis` returned no matches in `monitor.py`.
- Stub scan for TODO/FIXME/placeholder/coming soon/not available patterns in plan-owned files returned no matches.

## Known Stubs

None.

## Next Phase Readiness

Phase 1 runtime storage wiring is complete. The bot can now initialize SQLite, migrate legacy JSON inputs once, and use SQLite as the normal source of truth for settings, latest snapshots, and price history while staying a single-container monolith.

## Self-Check: PASSED

- Found `price_monitor/monitor.py`.
- Found `tests/test_price_monitor.py`.
- Found `.planning/phases/01-sqlite-state-and-single-container-foundation/01-02-SUMMARY.md`.
- Found task commits `3157bdb`, `13243f1`, `2c6f52a`, `34b5933`, `8545fe2`, and `31a5ec0`.

---
*Phase: 01-sqlite-state-and-single-container-foundation*
*Completed: 2026-05-03*
