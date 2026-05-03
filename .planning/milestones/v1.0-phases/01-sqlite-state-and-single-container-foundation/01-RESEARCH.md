# Phase 1: SQLite State and Single-Container Foundation - Research

**Researched:** 2026-05-03
**Domain:** Python stdlib SQLite persistence migration for a Dockerized monolithic service
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Claude's Discretion
- The exact function names inside `price_monitor/storage.py` may be chosen by the planner/executor as long as the API is small, typed, and testable.
- The exact SQLite DDL may be chosen during planning, but it must support the indexable fields listed above.
- The exact migration metadata key names are flexible.
- The planner may decide whether to keep thin compatibility wrappers named like the current JSON helpers or replace call sites directly.

### Deferred Ideas (OUT OF SCOPE)
- Telegram menu redesign and authorization behavior belong to Phase 2.
- Readable Telegram summaries and target-price alert behavior belong to Phase 3.
- Duration anomaly analytics belongs to Phase 4.
- Currency observation tables and exchange-rate alerts belong to Phase 5, even though the SQLite schema should not block adding those tables later.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | The application stores runtime settings in a local SQLite database file mounted through the Docker data volume. | Add `db_path` to `MonitorConfig`, wire `BG_DB_PATH=/data/price_monitor.sqlite3`, and replace runtime settings JSON helpers with SQLite settings rows. |
| STOR-02 | The application stores observed tour price history in SQLite with timestamps, provider, hotel/search target, departure date, nights, and price in RUB. | Use append-only `price_history` table with indexed typed columns plus payload JSON. |
| STOR-03 | The application stores latest snapshots in SQLite so price changes can be detected across checks. | Use `latest_snapshots` keyed by current snapshot identity, with upsert semantics and load/save compatibility. |
| STOR-04 | The application can migrate or initialize from an empty database without manual SQL steps. | `storage.initialize()` should create schema, run idempotent JSON import once, and tolerate missing JSON inputs. |
| STOR-05 | The application no longer depends on JSON files for settings, snapshots, or price history in normal runtime. | JSON path env vars stay as migration inputs only; normal `effective_config`, `load_search_targets`, and `run_check` use SQLite. |
| OPS-01 | The application runs as a monolithic Python service in one process. | Use stdlib `sqlite3`; no service split, async framework, worker, or broker. |
| OPS-02 | The Docker image starts the bot with a single command and persists SQLite data through a mounted volume. | Keep existing Dockerfile command and named volume; add `BG_DB_PATH` env. |
| OPS-03 | The project does not require RabbitMQ, Redis, Kafka, Celery, PostgreSQL, MySQL, or separate worker containers. | Do not add external storage, queue, ORM, migration service, or extra container. |
| OPS-04 | The application handles malformed or missing persisted data without crashing the long-running service. | Catch JSON import decode errors and SQLite database errors; corrupt DB fallback renames bad file and reinitializes. |
| QUAL-01 | Existing tests pass with the current `MonitorConfig` shape. | Current failure is two old `MonitorConfig(...)` constructors missing `target_price_rub` and `history_path`; Phase 1 must repair tests or add defaults. |
| QUAL-02 | SQLite storage has focused tests for initialization, settings persistence, snapshot persistence, and price history writes. | Add `tmp_path` tests for `storage.py` and narrow integration tests for monitor helper wrappers. |
</phase_requirements>

## Summary

Phase 1 should use Python's built-in `sqlite3` module and a new focused `price_monitor/storage.py`. This matches the project constraints because SQLite is embedded, does not require a server process, is available in the Python 3.11 container, and keeps the application as one process and one Docker container.

The planner should treat existing JSON files as a data migration problem, not as an ongoing fallback path. The live `bg-price-monitor` container currently has `/data/settings.json`, `/data/last_snapshot.json`, and `/data/price_history.json` in the Docker volume, and no `/data/price_monitor.sqlite3`, so the first real deployment after Phase 1 will need one-time import from those files.

**Primary recommendation:** Implement a small synchronous SQLite storage module using stdlib `sqlite3`, idempotent schema/migration metadata, JSON payload columns for compatibility, typed/indexed columns for queries, and focused `tmp_path` pytest coverage.

## Project Constraints (from CLAUDE.md)

- Single admin user only; do not introduce multi-user or SaaS abstractions.
- Keep checks, Telegram polling, parsing, scheduling, and persistence inside one monolithic application process.
- Use SQLite as local durable storage through the Docker volume.
- No Celery, separate workers, brokers, RabbitMQ, Redis, Kafka, PostgreSQL, MySQL, or extra worker containers.
- Keep deployment as one Dockerfile/image/container and a mounted volume.
- Telegram remains the v1 interface; no public web dashboard in this phase.
- Parser and Telegram redesigns are out of scope for Phase 1.
- Use GSD workflow artifacts and keep planning docs in sync before implementation work.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | Container: 3.11.15; local test host: 3.14.4 | Runtime and tests | Existing Dockerfile uses `python:3.11-slim`; production behavior should be validated against container Python. |
| `sqlite3` stdlib module | Python 3.11 module, runtime SQLite 3.46.1 in live container | Embedded local database | Official Python DB-API interface for SQLite; no external server, broker, ORM, or package needed. |
| SQLite | Container runtime library 3.46.1; local Python reports 3.50.4 | Database engine | Supports local file database, transactions, indexes, WAL, upsert, and integrity checks. |
| Docker named volume | `price_parcer_bg-price-monitor-data` | Persistent `/data` storage | Existing volume holds JSON state and should hold `/data/price_monitor.sqlite3`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` stdlib | Python 3.11 | Read old JSON files and store payload columns | Use for one-time import and full offer payload preservation. |
| `pathlib` stdlib | Python 3.11 | DB path and old JSON path handling | Continue existing `Path`-based configuration convention. |
| `logging` stdlib | Python 3.11 | Corruption/import warnings | Use existing Docker-friendly stdout logging style. |
| pytest | Local 9.0.3 | Focused storage tests | Already available locally; not declared in production requirements. |
| requests | Existing pinned 2.31.0; latest 2.33.1 | Provider and Telegram HTTP | Keep pinned version; Phase 1 should not upgrade unrelated dependencies. |
| beautifulsoup4 | Existing pinned 4.12.3; latest 4.14.3 | HTML parsing | Keep pinned version; parser work is out of scope. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `sqlite3` | SQLAlchemy | Adds ORM dependency and migration complexity for a tiny monolith. Not needed for 4 simple tables. |
| Handwritten schema metadata | Alembic | Alembic is useful with SQLAlchemy and larger schema histories; Phase 1 only needs `schema_version` and import flags. |
| SQLite file | PostgreSQL/MySQL | Violates locked project constraints and adds service/container operational burden. |
| In-process sqlite writes | Celery/RQ/background worker | Violates one-process constraint; unnecessary for low-volume settings and history writes. |
| JSON files | Atomic JSON writes | Would reduce corruption risk but fails STOR-01 through STOR-05 and keeps whole-file history rewrites. |

**Installation:**

No new runtime package should be installed for SQLite. Keep `price_monitor/requirements.txt` unchanged unless tests require a dev-only fixture package, which is not currently necessary.

```bash
# Production SQLite support is included in Python.
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

**Version verification:**
- `docker exec bg-price-monitor python --version`: Python 3.11.15.
- `docker exec bg-price-monitor python -c "import sqlite3; print(sqlite3.sqlite_version)"`: SQLite 3.46.1.
- `python -m pip index versions requests`: installed 2.31.0, latest 2.33.1, installed release uploaded 2023-05-22.
- `python -m pip index versions beautifulsoup4`: installed 4.12.3, latest 4.14.3, installed release uploaded 2024-01-17.
- `python -m pip index versions pytest`: installed and latest 9.0.3, release uploaded 2026-04-07.

## Architecture Patterns

### Recommended Project Structure

```text
price_monitor/
├── monitor.py        # existing orchestration, parsers, Telegram, thin storage calls
├── storage.py        # SQLite connection, schema, JSON import, persistence API
└── requirements.txt  # unchanged runtime deps

tests/
├── test_price_monitor.py  # existing helper tests, repaired for config shape
└── test_storage.py        # new focused SQLite tests using tmp_path
```

### Pattern 1: Small Storage Facade

**What:** Put all SQL, schema initialization, JSON import, corrupt DB fallback, and row/payload conversion in `price_monitor/storage.py`.

**When to use:** Every current `load_*` or `save_*` persistence path. Keep `monitor.py` as the caller so parser and Telegram code do not get mixed with SQL.

**Recommended API shape:**

```python
# Source: Python sqlite3 docs, https://docs.python.org/3.11/library/sqlite3.html
def initialize_storage(config: MonitorConfig) -> None: ...
def load_runtime_settings(config: MonitorConfig) -> dict[str, object]: ...
def save_runtime_settings(config: MonitorConfig, settings: dict[str, object]) -> None: ...
def load_snapshot(config: MonitorConfig) -> dict[str, dict[str, object]]: ...
def save_snapshot(config: MonitorConfig, data: dict[str, dict[str, object]]) -> None: ...
def append_price_history(config: MonitorConfig, snapshot: dict[str, dict[str, object]], observed_at: str) -> None: ...
def load_price_history(config: MonitorConfig) -> dict[str, list[list]]: ...
```

Thin compatibility wrappers in `monitor.py` are acceptable if they keep existing tests close to their current import surface.

### Pattern 2: Idempotent Initialization

**What:** `initialize_storage()` should create the parent directory, connect to `BG_DB_PATH`, set safe pragmas, create tables with `CREATE TABLE IF NOT EXISTS`, apply schema version metadata, then import JSON only if `metadata.json_import_completed` is absent.

**When to use:** Call once at process startup after `MonitorConfig.from_env()`, and defensively before storage operations in tests or wrappers.

**Example DDL:**

```sql
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_settings (
  key TEXT PRIMARY KEY,
  value_type TEXT NOT NULL,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS latest_snapshots (
  snapshot_key TEXT PRIMARY KEY,
  target_name TEXT NOT NULL,
  provider TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  nights INTEGER NOT NULL,
  offer_identity TEXT NOT NULL,
  price_rub INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_key TEXT NOT NULL,
  target_name TEXT NOT NULL,
  provider TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  nights INTEGER NOT NULL,
  price_rub INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_history_lookup
ON price_history(target_name, provider, departure_date, nights, observed_at);
```

### Pattern 3: Typed Columns Plus JSON Payload

**What:** Store columns needed for lookups and filtering as real `TEXT`/`INTEGER` columns, and keep the complete current dict in `payload_json` for compatibility with existing formatters.

**When to use:** `latest_snapshots` and `price_history`. Do not store only a JSON blob; future phases need indexed date/night/price queries.

### Pattern 4: Short-Lived Connections and Serialized Writes

**What:** Open connections inside storage functions or via a small connection helper. Do not share one global connection between the scheduler thread and Telegram polling thread unless access is explicitly serialized.

**Why:** Python `sqlite3.connect()` defaults `check_same_thread=True`; using a connection from another thread raises `ProgrammingError`. If `check_same_thread=False` is used, user code must serialize writes.

**Recommended:** Use a module-level `threading.RLock` around write operations plus `sqlite3.connect(path, timeout=10)` for short operations. Keep transactions small.

### Pattern 5: Corrupt DB Quarantine

**What:** On database open/init failure that indicates corruption or unreadability, rename the DB file to `price_monitor.sqlite3.corrupt-YYYYMMDDHHMMSS`, also quarantine `-wal` and `-shm` sidecars if WAL is enabled, log the new paths, then initialize an empty DB.

**When to use:** During `initialize_storage()`, not inside every query. Missing JSON input remains non-error; corrupt SQLite DB follows D-18 through D-20.

### Anti-Patterns to Avoid

- **ORM/migration framework:** Adds moving parts and violates the small monolith intent.
- **JSON fallback after SQLite exists:** Would hide migration bugs and violate STOR-05.
- **Only JSON blob tables:** Blocks efficient history/date/night queries needed in later phases.
- **Single global connection across threads:** Conflicts with `sqlite3` default thread guard and can corrupt writes if manually disabled without locking.
- **Deleting corrupt DB files:** Violates D-20 and destroys forensic recovery data.
- **Refactoring parser or Telegram code while migrating storage:** Enlarges blast radius beyond Phase 1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedded persistence | Custom file format or JSON append log | SQLite via stdlib `sqlite3` | Handles transactions, indexing, and atomic commit better than ad hoc files. |
| SQL escaping | f-string SQL values | DB-API placeholders | Python docs explicitly recommend placeholders for binding values. |
| One-time migration tracking | Sentinel files beside the DB | `metadata` table key | Keeps migration state with the schema and survives container restarts. |
| Schema migrations | External migration CLI | Small metadata-driven `apply_schema()` | One service, one DB, simple schema. |
| Corrupt DB recovery | Delete/recreate silently | Rename bad DB and sidecars, log warning, initialize new | Preserves old data for manual recovery and meets D-18/D-20. |
| Thread concurrency | Shared unchecked global connection | Short-lived connections plus write lock/busy timeout | Fits Python `sqlite3` thread model. |

**Key insight:** The hard part is not SQL complexity; it is preserving existing behavior while changing the source of truth. Keep the API compatible and tests close to current helper behavior.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Live Docker volume `price_parcer_bg-price-monitor-data` contains `/data/settings.json` size 404, `/data/last_snapshot.json` size 12458, `/data/price_history.json` size 3421. Root repo also has `last_snapshot.json` size 5133, but current Docker defaults point to `/data`. No `*.sqlite`, `*.sqlite3`, or `*.db` file found in repo; `/data/price_monitor.sqlite3` does not exist in the running container. | Data migration required from configured JSON paths on first SQLite initialization. Treat root `last_snapshot.json` only as migration input if `BG_STATE_PATH` points there in a local run. |
| Live service config | Running container `bg-price-monitor` is up. Container env includes `BG_STATE_PATH` and `BG_HISTORY_PATH`, but no `BG_DB_PATH` yet. Compose currently mounts `/data` through the named volume and wires `BG_STATE_PATH`/`BG_HISTORY_PATH`; `.env.example` has `BG_SETTINGS_PATH` but no `BG_DB_PATH`. | Code and config edit required: add `BG_DB_PATH`, keep old JSON vars as migration inputs, include `BG_SETTINGS_PATH` in compose if migration should be explicit. Restart/recreate container after implementation. |
| OS-registered state | No project-specific Windows Scheduled Task found. The only `Bg...` task matched was Windows `BrokerInfrastructure\BgTaskRegistrationMaintenanceTask`, unrelated. Docker container registration exists as container name `bg-price-monitor`. | No OS task migration. Container recreate is enough for env changes. |
| Secrets/env vars | `.env` exists but was not read to avoid exposing secrets. Shell environment has no `BG_*` or `TELEGRAM_*` variables. Container has Telegram and BG env keys but values were not printed. | Code edit required to read `BG_DB_PATH`; no secret key rename needed. Do not commit `.env`. |
| Build artifacts | No project `*.egg-info` or `*.dist-info` artifacts found. Docker image/container `bg-price-monitor` exists and will still contain old code until rebuilt. | Rebuild/recreate Docker container after implementation; no package artifact cleanup needed. |

## Common Pitfalls

### Pitfall 1: Repeated JSON Import

**What goes wrong:** Every restart reimports old JSON and overwrites newer SQLite changes.
**Why it happens:** Migration code checks for JSON file existence instead of a durable import-completed marker.
**How to avoid:** Write `metadata('json_import_completed') = '1'` in the same transaction as import completion.
**Warning signs:** Settings changed through Telegram revert after restart.

### Pitfall 2: JSON Fallback Still in Normal Runtime

**What goes wrong:** Code appears migrated but still reads JSON when SQLite is empty or errors.
**Why it happens:** Keeping old helper fallback logic after adding SQLite.
**How to avoid:** JSON reads should exist only inside `import_legacy_json()`. Normal load helpers read SQLite only after initialization.
**Warning signs:** Deleting JSON files changes runtime behavior after migration.

### Pitfall 3: Shared SQLite Connection Across Threads

**What goes wrong:** Telegram settings writes or manual checks fail with thread errors or lock contention.
**Why it happens:** `sqlite3` connections default to same-thread usage; disabling the guard requires external write serialization.
**How to avoid:** Use short-lived connections, `timeout`, `PRAGMA busy_timeout`, and a write lock for one-process writes.
**Warning signs:** `ProgrammingError` mentions thread mismatch, or intermittent `database is locked`.

### Pitfall 4: Losing Snapshot Key Compatibility

**What goes wrong:** First SQLite run sends spurious new-offer/price-change notifications or loses historical minimum detection.
**Why it happens:** The snapshot identity is changed during migration from `target_name|departure|nights|suffix`.
**How to avoid:** Preserve existing snapshot keys as `snapshot_key` and parse typed fields from payload.
**Warning signs:** Alert output changes on a no-price-change restart.

### Pitfall 5: Corrupt DB Rename Misses WAL Sidecars

**What goes wrong:** A replacement DB is initialized but stale `-wal` or `-shm` files remain beside it.
**Why it happens:** WAL mode creates sidecar files in the same directory.
**How to avoid:** If using WAL, quarantine `price_monitor.sqlite3-wal` and `price_monitor.sqlite3-shm` along with the main DB.
**Warning signs:** New DB reports unexpected old state or repeated open failures after fallback.

### Pitfall 6: Over-Refactoring `monitor.py`

**What goes wrong:** Parser, Telegram, and scheduler behavior regress while storage is being replaced.
**Why it happens:** The existing file is large and tempting to split broadly.
**How to avoid:** Phase 1 should add `storage.py`, add `db_path`, and change persistence call sites only.
**Warning signs:** Plans touch provider parser functions, Telegram keyboard layout, or scheduling logic without storage need.

## Code Examples

Verified patterns from official sources:

### Connection Helper

```python
# Source: Python sqlite3 docs, https://docs.python.org/3.11/library/sqlite3.html
import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    con.execute("PRAGMA journal_mode = WAL")
    return con
```

### Idempotent Schema

```python
def initialize_schema(db_path: Path) -> None:
    with connect(db_path) as con:
        con.executescript(SCHEMA_SQL)
        con.execute(
            """
            INSERT INTO metadata(key, value, updated_at)
            VALUES ('schema_version', '1', CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """
        )
```

### One-Time Legacy Import Guard

```python
def should_import_legacy_json(con: sqlite3.Connection) -> bool:
    row = con.execute(
        "SELECT value FROM metadata WHERE key = ?",
        ("json_import_completed",),
    ).fetchone()
    return row is None
```

### Snapshot Upsert

```python
def save_snapshot_row(con: sqlite3.Connection, key: str, item: dict[str, object]) -> None:
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
    con.execute(
        """
        INSERT INTO latest_snapshots(
          snapshot_key, target_name, provider, departure_date, nights,
          offer_identity, price_rub, observed_at, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(snapshot_key) DO UPDATE SET
          price_rub = excluded.price_rub,
          observed_at = excluded.observed_at,
          payload_json = excluded.payload_json
        """,
        (
            key,
            key.split("|", 1)[0],
            str(item.get("provider") or "Biblio-Globus"),
            str(item["departure_date"]),
            int(item["nights"]),
            key,
            int(item["price_rub"]),
            payload,
        ),
    )
```

### Corrupt DB Quarantine

```python
def quarantine_database(db_path: Path, suffix: str) -> None:
    for path in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        if path.exists():
            path.rename(path.with_name(f"{path.name}.corrupt-{suffix}"))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Whole-file JSON settings/snapshot/history | SQLite tables with typed columns and JSON payloads | Phase 1 | Removes normal-runtime JSON dependency and avoids whole-history rewrites. |
| Manual SQL setup | App-owned `CREATE TABLE IF NOT EXISTS` plus metadata | Phase 1 | Fresh Docker volume starts without manual SQL. |
| Implicit config shape from JSON | Validated settings rows before applying to `MonitorConfig` | Phase 1 | Malformed persisted settings should not crash checks. |
| Unbounded history dictionary rewrite | Append-only `price_history` rows | Phase 1 | Better write behavior and future analytics queries. |
| Silent JSON read errors crashing checks | Corrupt DB quarantine plus missing JSON tolerance during import | Phase 1 | Long-running service continues after storage problems. |

**Deprecated/outdated:**
- `BG_STATE_PATH`, `BG_SETTINGS_PATH`, `BG_HISTORY_PATH` as normal-runtime storage paths: keep only as migration inputs.
- Root `last_snapshot.json` as local state: not part of Docker default runtime and should not become the new source of truth.
- `pytest` command directly in this workspace: previous codebase notes say `python -m pytest -q` is the reliable runner.

## Open Questions

1. **Should compatibility wrappers remain in `monitor.py`?**
   - What we know: Existing tests import helpers directly from `price_monitor.monitor`.
   - What's unclear: Whether executor should update all imports to `price_monitor.storage`.
   - Recommendation: Keep thin wrappers in `monitor.py` for Phase 1, add direct `storage.py` tests, and avoid broad import churn.

2. **Should WAL be enabled?**
   - What we know: SQLite WAL improves read/write concurrency and is supported by the container SQLite version.
   - What's unclear: Whether sidecar files are worth the extra corrupt-rename handling in this very low-volume app.
   - Recommendation: Enable WAL with sidecar quarantine handling; if planner chooses default journaling for simplicity, keep `busy_timeout` and write lock.

3. **What should happen to malformed legacy JSON during import?**
   - What we know: OPS-04 says malformed persisted data must not crash the service; D-18 only defines SQLite corruption behavior.
   - What's unclear: Whether malformed JSON should be quarantined or merely logged and skipped.
   - Recommendation: Log actionable warning, skip that specific JSON import, complete migration so runtime moves to SQLite. Do not delete JSON.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python local | Tests and research commands | yes | 3.14.4 | Use container Python for production parity if behavior differs. |
| Python container | Production runtime | yes | 3.11.15 | None needed. |
| SQLite via `sqlite3` local | Storage tests | yes | SQLite 3.50.4 | Use container for parity. |
| SQLite via `sqlite3` container | Production storage | yes | SQLite 3.46.1 | None needed. |
| pytest | Test suite | yes | 9.0.3 | None needed locally; not in production requirements. |
| Docker | Container build/run | yes | 29.3.1 | None needed. |
| Docker Compose | One-command service | yes | v5.1.1 | `docker compose` available. |
| Docker volume | Runtime data migration | yes | `price_parcer_bg-price-monitor-data` | None needed. |
| Live container | Runtime state inspection | yes | `bg-price-monitor`, running | Stop/recreate during implementation. |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- No `BG_DB_PATH` in current container/compose yet; this is an implementation task, not a tool dependency.

## Test Architecture

Nyquist validation is explicitly disabled in `.planning/config.json` (`workflow.nyquist_validation=false`), so no formal Validation Architecture section is required.

Current observed test state:

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 local |
| Config file | none |
| Quick run command | `python -m pytest tests/test_storage.py -q` after adding storage tests |
| Full suite command | `python -m pytest -q` |
| Current result | 9 passed, 2 failed |
| Current failures | Two `MonitorConfig(...)` test constructors omit `target_price_rub` and `history_path` |

Focused tests the planner should include:

| Behavior | Test Type | Suggested Test |
|----------|-----------|----------------|
| Fresh DB initializes schema | unit | `test_initialize_storage_creates_tables` using `tmp_path` |
| Missing legacy JSON initializes empty DB | unit | `test_initialize_storage_allows_missing_legacy_json` |
| Legacy settings import once | unit | `test_import_legacy_settings_only_once` |
| Runtime settings round trip | unit | `test_runtime_settings_round_trip_sqlite` |
| Latest snapshot round trip | unit | `test_latest_snapshot_round_trip_sqlite` |
| Price history appends rows | unit | `test_price_history_append_does_not_rewrite_snapshot` |
| Corrupt DB fallback | unit | `test_corrupt_db_is_renamed_and_reinitialized` |
| `MonitorConfig.from_env` reads `BG_DB_PATH` | unit | `test_monitor_config_reads_db_path` with `monkeypatch` |

## Sources

### Primary (HIGH confidence)

- Python 3.11 `sqlite3` official docs: https://docs.python.org/3.11/library/sqlite3.html - DB-API, connection options, thread behavior, placeholders, exceptions, type mapping.
- SQLite WAL docs: https://www.sqlite.org/wal.html - WAL concurrency properties and `SQLITE_BUSY` caveat.
- SQLite UPSERT docs: https://www.sqlite.org/lang_upsert.html - `ON CONFLICT DO UPDATE` behavior and version history.
- SQLite PRAGMA docs: https://www.sqlite.org/pragma.html - `journal_mode`, `integrity_check`, `quick_check`, and related operational controls.
- Docker volume docs: https://docs.docker.com/engine/storage/volumes/ - volumes as persistent container data stores.
- Docker Compose services docs: https://docs.docker.com/reference/compose-file/services/ - service volume/env wiring reference.
- Local project files read for scope: `01-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `monitor.py`, `test_price_monitor.py`, `docker-compose.yml`, Dockerfile, `AGENTS.md`, `CLAUDE.md`, `.planning/config.json`.

### Secondary (MEDIUM confidence)

- PyPI registry via `python -m pip index versions` and PyPI JSON API - checked latest package versions and release upload dates for existing dependencies.
- Live Docker inspection - verified container Python/SQLite versions and `/data` file inventory.

### Tertiary (LOW confidence)

- None used for critical claims.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified from Docker container, local Python, project manifests, official Python/SQLite/Docker docs.
- Architecture: HIGH - Directly constrained by CONTEXT.md and existing `monitor.py` call sites.
- Pitfalls: HIGH - Based on official sqlite thread/transaction behavior plus observed live Docker state and known project concerns.
- Runtime state inventory: HIGH - Verified by Docker CLI, filesystem inspection, and PowerShell searches; `.env` values intentionally not read.

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 for project architecture; re-check package and Docker versions before dependency upgrades.
