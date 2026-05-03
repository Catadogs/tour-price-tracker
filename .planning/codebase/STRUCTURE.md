# Codebase Structure

**Analysis Date:** 2026-05-03

## Directory Layout

```
C:\price_parcer/
├── .claude/                    # Local Claude/Codex settings for this workspace
├── .planning/                  # GSD planning and generated codebase mapping documents
├── docker/                     # Docker build files
│   └── price-monitor/          # Container image definition for the monitor service
├── price_monitor/              # Python package containing the monitor implementation
├── tests/                      # Pytest test suite
├── .env                        # Local environment configuration; contents not documented
├── .env.example                # Example environment configuration; contents not documented here
├── .gitignore                  # Git ignore rules
├── docker-compose.yml          # Docker Compose service and persistent volume definition
├── last_snapshot.json          # Root-level price snapshot artifact
└── README.md                   # Usage documentation
```

## Directory Purposes

**`.claude/`:**
- Purpose: Store local assistant settings for the workspace.
- Contains: Local JSON settings.
- Key files: `.claude/settings.local.json`

**`.planning/`:**
- Purpose: Store GSD planning artifacts and codebase analysis documents.
- Contains: Generated markdown documents under `.planning/codebase/`.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

**`docker/`:**
- Purpose: Store Docker build definitions outside the Python package.
- Contains: Service-specific Dockerfile directories.
- Key files: `docker/price-monitor/Dockerfile`

**`docker/price-monitor/`:**
- Purpose: Define the container image for running the monitor.
- Contains: `Dockerfile` that installs Python dependencies and starts the package module.
- Key files: `docker/price-monitor/Dockerfile`

**`price_monitor/`:**
- Purpose: Store the importable Python package and application implementation.
- Contains: The executable monitor module, Python dependency manifest, and package marker.
- Key files: `price_monitor/monitor.py`, `price_monitor/requirements.txt`, `price_monitor/__init__.py`

**`tests/`:**
- Purpose: Store automated tests for parser, filtering, formatting, validation, and helper behavior.
- Contains: Pytest test modules.
- Key files: `tests/test_price_monitor.py`

## Key File Locations

**Entry Points:**
- `price_monitor/monitor.py`: Main executable module; contains `main`, the scheduled loop, Telegram bot controller, parsing, persistence, and reporting logic.
- `docker/price-monitor/Dockerfile`: Container entry point using `CMD ["python", "-m", "price_monitor.monitor"]`.
- `docker-compose.yml`: Compose entry point for the `bg-price-monitor` service.

**Configuration:**
- `price_monitor/monitor.py`: Defines environment-backed settings in `MonitorConfig.from_env` and runtime settings paths.
- `docker-compose.yml`: Defines the Docker service, environment variable wiring, and `bg-price-monitor-data` volume.
- `.env`: Local environment configuration file present at the project root; contents are intentionally not read or documented.
- `.env.example`: Example environment configuration file present at the project root; contents are intentionally not read or documented.
- `price_monitor/requirements.txt`: Python dependency pins for the container build and local package execution.

**Core Logic:**
- `price_monitor/monitor.py`: All domain logic lives in this file. Add parsing, filtering, reporting, persistence, Telegram, and scheduling changes here unless the codebase is intentionally split into modules.
- `price_monitor/__init__.py`: Package marker only; do not add runtime behavior here.

**Testing:**
- `tests/test_price_monitor.py`: Main pytest coverage for pure helpers imported from `price_monitor.monitor`.

**Documentation:**
- `README.md`: User-facing quick start, Docker commands, and Telegram interaction notes.
- `.planning/codebase/ARCHITECTURE.md`: Architecture map for future planning and execution.
- `.planning/codebase/STRUCTURE.md`: Directory and placement guide for future planning and execution.

**Runtime Artifacts:**
- `last_snapshot.json`: Root-level snapshot artifact. Container execution defaults to `/data/last_snapshot.json` through `MonitorConfig.state_path`.
- `/data/settings.json`: Default container path for Telegram-edited runtime settings, configured in `MonitorConfig.settings_path`.
- `/data/price_history.json`: Default container path for historical price series, configured in `MonitorConfig.history_path`.

## Naming Conventions

**Files:**
- Python package modules use lowercase snake_case names: `price_monitor/monitor.py`.
- Python tests use `test_*.py` names: `tests/test_price_monitor.py`.
- Docker directories use kebab-case for the service build context: `docker/price-monitor/`.
- Planning documents use uppercase markdown names: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.
- Runtime JSON artifacts use lowercase snake_case names: `last_snapshot.json`, `/data/settings.json`, `/data/price_history.json`.

**Directories:**
- Python packages use lowercase snake_case: `price_monitor/`.
- Test directories use the standard plural name: `tests/`.
- Docker service directories use kebab-case: `docker/price-monitor/`.
- Planning directories use dot-prefixed workspace folders: `.planning/`, `.planning/codebase/`.

## Where to Add New Code

**New Price Provider:**
- Primary code: Add provider detection, parsing, and report formatting in `price_monitor/monitor.py` near `provider_from_url`, `parse_external_price`, `extract_external_hotel_name`, and `extract_external_min_price`.
- Tests: Add provider parser and URL-validation tests to `tests/test_price_monitor.py`.

**New Biblio-Globus Parsing Behavior:**
- Primary code: Add parsing helpers in `price_monitor/monitor.py` near `parse_offers`, `extract_hotel_name`, `parse_int`, and `parse_usd`.
- Tests: Add focused HTML fixture tests to `tests/test_price_monitor.py`.

**New Filtering or Selection Rule:**
- Primary code: Add filtering and comparison logic in `price_monitor/monitor.py` near `filter_offers`, `best_by_departure_and_nights`, `find_overall_best`, and `format_strong_diff_line`.
- Tests: Add offer selection and formatting tests to `tests/test_price_monitor.py`.

**New Runtime Setting:**
- Primary code: Add the field to `MonitorConfig` in `price_monitor/monitor.py`, load it in `MonitorConfig.from_env`, merge it in `effective_config`, expose it in `format_settings`, and persist Telegram edits through `TelegramControlBot.apply_pending_action`.
- Tests: Add validation/helper tests in `tests/test_price_monitor.py`.
- Configuration: Add Docker environment wiring in `docker-compose.yml` and document usage in `README.md`; do not commit secret values.

**New Telegram Command or Button:**
- Primary code: Add inline button data to `main_keyboard` or `settings_keyboard` in `price_monitor/monitor.py`, route it in `TelegramControlBot.handle_callback`, and implement any text follow-up in `TelegramControlBot.apply_pending_action`.
- Tests: Add pure validation or formatting tests to `tests/test_price_monitor.py`; Telegram network calls are not directly tested in the current structure.

**New Persistence File:**
- Primary code: Add load/save helpers in `price_monitor/monitor.py` using `Path.read_text`, `Path.write_text`, and `json`.
- Configuration: Add a path field to `MonitorConfig` and environment loading in `MonitorConfig.from_env`.
- Docker: Mount through the existing `bg-price-monitor-data` volume configured in `docker-compose.yml`.

**New Component/Module:**
- Implementation: Keep changes in `price_monitor/monitor.py` when they are small and directly related to existing monitor behavior. Create a new module under `price_monitor/` only when a cohesive area, such as Telegram control or provider parsing, becomes independently testable.
- Tests: Keep tests in `tests/test_price_monitor.py` for the current single-module structure; create `tests/test_<module>.py` if a new package module is introduced.

**Utilities:**
- Shared helpers: Place monitor-specific helpers in `price_monitor/monitor.py` near related functions.
- Package-wide helpers: Create a new `price_monitor/<name>.py` module only when the helper is reused across multiple modules.

## Special Directories

**`.planning/`:**
- Purpose: GSD-generated planning and codebase analysis.
- Generated: Yes
- Committed: Project-dependent; treat generated planning docs as workspace artifacts unless the orchestrator commits them.

**`.pytest_cache/`:**
- Purpose: Pytest cache directory from local test runs.
- Generated: Yes
- Committed: No

**`docker/`:**
- Purpose: Docker build assets for the service.
- Generated: No
- Committed: Yes

**`price_monitor/`:**
- Purpose: Python application package.
- Generated: No
- Committed: Yes

**`tests/`:**
- Purpose: Automated test suite.
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-05-03*
