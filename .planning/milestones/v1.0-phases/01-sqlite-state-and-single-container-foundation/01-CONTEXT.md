# Phase 1: SQLite State and Single-Container Foundation - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 replaces normal-runtime JSON persistence for settings, latest snapshots, and tour price history with a local SQLite database while preserving the current operating model: one Python process, one Docker image/container, and one mounted Docker volume. This phase does not redesign Telegram menus, add currency monitoring, or expand provider parsing; those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Database path and runtime configuration
- **D-01:** Add a new environment variable `BG_DB_PATH` for the SQLite database path.
- **D-02:** Default `BG_DB_PATH` to `/data/price_monitor.sqlite3` in container runtime.
- **D-03:** Keep the old JSON path variables `BG_STATE_PATH`, `BG_SETTINGS_PATH`, and `BG_HISTORY_PATH` only as migration inputs during Phase 1, not as normal-runtime storage.
- **D-04:** Update Docker Compose and `.env.example` to expose `BG_DB_PATH=/data/price_monitor.sqlite3`.

### JSON migration
- **D-05:** On first SQLite initialization, import existing JSON files if present: settings from `BG_SETTINGS_PATH`, latest snapshot from `BG_STATE_PATH`, and price history from `BG_HISTORY_PATH`.
- **D-06:** Record migration completion in SQLite so the import is not repeated on every restart.
- **D-07:** After migration, normal runtime must read and write SQLite only; JSON fallback should not be used for current state.
- **D-08:** Missing JSON files are valid and should produce an empty initialized database.

### SQLite schema shape
- **D-09:** Use a mixed schema: typed/indexable columns for frequently queried dimensions, plus JSON payload columns for provider-specific details.
- **D-10:** Runtime settings should be stored as typed key/value rows, with validation/defaulting before values are applied to `MonitorConfig`.
- **D-11:** Latest snapshots should be stored with columns sufficient to identify target/provider/departure/nights/offer identity and current price, plus payload for full offer details.
- **D-12:** Price history should be append-only with indexable columns including target, provider, departure date, nights, price in RUB, and observed timestamp.
- **D-13:** SQLite schema should include a small metadata/migrations table for schema version and one-time JSON import state.

### Refactoring boundary
- **D-14:** Create a focused `price_monitor/storage.py` module for SQLite connection handling, schema initialization, JSON import, and storage operations.
- **D-15:** Keep parser logic, Telegram control flow, and the main scheduler flow out of the refactor for Phase 1.
- **D-16:** `price_monitor/monitor.py` may be updated to call the new storage API, but Phase 1 should not split provider parsers, Telegram, or service orchestration into separate modules.
- **D-17:** Preserve existing public helper behavior where practical so current tests can be repaired rather than rewritten wholesale.

### Corrupt database behavior
- **D-18:** If SQLite reports corruption or cannot open the database, rename the bad file to `price_monitor.sqlite3.corrupt-<timestamp>` in the same directory, initialize a new empty database, and log an actionable warning.
- **D-19:** The service should continue running after the corrupt DB fallback rather than fail fast.
- **D-20:** The fallback must not silently delete the corrupt database file.

### the agent's Discretion
- The exact function names inside `price_monitor/storage.py` may be chosen by the planner/executor as long as the API is small, typed, and testable.
- The exact SQLite DDL may be chosen during planning, but it must support the indexable fields listed above.
- The exact migration metadata key names are flexible.
- The planner may decide whether to keep thin compatibility wrappers named like the current JSON helpers or replace call sites directly.

</decisions>

<specifics>
## Specific Ideas

- User selected all five phase gray areas for discussion, then moved directly to planning before choosing individual options. The recommended defaults presented during discussion are treated as accepted to avoid planning without context.
- The SQLite DB path should be easy to inspect in Docker volume usage: `/data/price_monitor.sqlite3`.
- Existing root/runtime JSON artifacts should be treated as migration inputs, not as future source of truth.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and requirements
- `.planning/PROJECT.md` - Product constraints, strict architecture rules, and core value.
- `.planning/REQUIREMENTS.md` - Phase 1 requirements `STOR-01` through `STOR-05`, `OPS-01` through `OPS-04`, `QUAL-01`, and `QUAL-02`.
- `.planning/ROADMAP.md` - Phase boundary, success criteria, and requirement mapping.
- `.planning/STATE.md` - Current phase state and known blockers.

### Codebase map
- `.planning/codebase/ARCHITECTURE.md` - Existing JSON persistence flow, config merge, and `run_check` data flow.
- `.planning/codebase/STRUCTURE.md` - Where to add storage code and tests.
- `.planning/codebase/CONVENTIONS.md` - Naming, dataclass, error handling, and test conventions.
- `.planning/codebase/CONCERNS.md` - JSON corruption, test failures, large module risk, and history growth concerns.
- `.planning/codebase/STACK.md` - Python/Docker runtime and dependency constraints.

### Existing implementation files
- `price_monitor/monitor.py` - Current `MonitorConfig`, JSON helpers, `effective_config`, `load_search_targets`, price history, snapshot, and `run_check` integration points.
- `tests/test_price_monitor.py` - Existing tests that currently need repair and extension for SQLite storage.
- `docker-compose.yml` - Docker environment and `/data` volume wiring.
- `docker/price-monitor/Dockerfile` - Container entrypoint and package runtime.
- `.env.example` - Example runtime configuration to update with `BG_DB_PATH`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MonitorConfig` in `price_monitor/monitor.py`: already carries state paths and should gain `db_path: Path`.
- `load_runtime_settings`, `save_runtime_settings`, `load_snapshot`, `save_snapshot`, `load_price_history`, and `save_price_history` in `price_monitor/monitor.py`: these define the current persistence surface to replace or wrap.
- `effective_config` in `price_monitor/monitor.py`: should continue to merge persisted settings into env-derived config, but source settings from SQLite.
- `run_check` in `price_monitor/monitor.py`: main integration point for snapshots and price history persistence.
- `tests/test_price_monitor.py`: current pure-helper test style should be preserved and extended with SQLite-focused tests.

### Established Patterns
- Production runtime is Python 3.11 in Docker.
- Existing code uses frozen dataclasses, typed helpers, `Path` values for filesystem configuration, and plain `logging`.
- Existing tests import helpers directly from `price_monitor.monitor`.
- Current application is synchronous and single-process; Phase 1 should keep that behavior.

### Integration Points
- `MonitorConfig.from_env` should read `BG_DB_PATH` with default `/data/price_monitor.sqlite3`.
- Docker Compose should pass `BG_DB_PATH` into the container and keep the existing `/data` volume.
- New `price_monitor/storage.py` should be imported by `price_monitor/monitor.py`.
- Tests should cover DB initialization, one-time JSON import, settings persistence, snapshot persistence, price history writes, and corrupt DB fallback.

</code_context>

<deferred>
## Deferred Ideas

- Telegram menu redesign and authorization behavior belong to Phase 2.
- Readable Telegram summaries and target-price alert behavior belong to Phase 3.
- Duration anomaly analytics belongs to Phase 4.
- Currency observation tables and exchange-rate alerts belong to Phase 5, even though the SQLite schema should not block adding those tables later.

</deferred>

---

*Phase: 01-sqlite-state-and-single-container-foundation*
*Context gathered: 2026-05-03*
