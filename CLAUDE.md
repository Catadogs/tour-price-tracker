<!-- GSD:project-start source:PROJECT.md -->
## Project

**Personal Tour Price Tracker Bot**

Personal Tour Price Tracker Bot is a single-user Telegram bot for monitoring vacation tour prices, spotting price anomalies, and warning about currency-driven price hikes before operators recalculate RUB prices. The project is a personal admin-only tool, not a multi-user SaaS product.

The existing codebase already runs as a Dockerized Python price monitor with Telegram controls and provider parsing. This project turns that working monitor into a more durable, user-friendly personal tour tracking bot with SQLite storage, richer Telegram settings, anomaly analytics, and daily currency monitoring.

**Core Value:** The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.

### Constraints

- **Audience**: Single admin user only — avoid multi-user abstractions unless needed for Telegram authorization.
- **Architecture**: Monolith — keep checks, Telegram polling, parsing, and scheduling in one application process.
- **Storage**: SQLite — use a local database file mounted through Docker volume for settings and price history.
- **Background work**: Same process — use existing loop, `asyncio`, `threading`, or APScheduler-style scheduling, but no Celery or separate workers.
- **Deployment**: Single Dockerfile and mounted volume — keep deployment understandable and portable.
- **Security**: Admin-only Telegram control — settings changes and URL additions must require explicit admin authorization.
- **Provider fragility**: HTML parsers are brittle — parser changes need fixture-based tests and clear failure reporting.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11 - Production runtime via `docker/price-monitor/Dockerfile` using `python:3.11-slim`; application code lives in `price_monitor/monitor.py`.
- Markdown - Project documentation in `README.md`.
- YAML - Docker Compose configuration in `docker-compose.yml`.
- Dockerfile - Container build definition in `docker/price-monitor/Dockerfile`.
## Runtime
- Dockerized Python service using `python:3.11-slim` from `docker/price-monitor/Dockerfile`.
- Local analysis environment has Python 3.14.4 and pytest 9.0.3 available, but production runtime is the Docker image.
- Application entrypoint is `python -m price_monitor.monitor` from `docker/price-monitor/Dockerfile`.
- pip - Installs dependencies from `price_monitor/requirements.txt`.
- Lockfile: missing. There is no `requirements-lock.txt`, `pyproject.toml`, `poetry.lock`, `Pipfile.lock`, or root-level package manifest.
## Frameworks
- No web framework detected - `price_monitor/monitor.py` is a long-running worker process with a polling loop in `main()`.
- requests 2.31.0 - HTTP client for price pages and Telegram API calls, declared in `price_monitor/requirements.txt`.
- beautifulsoup4 4.12.3 - HTML parsing for Biblio-Globus, Level.Travel, and Travelata pages, declared in `price_monitor/requirements.txt`.
- Python standard library dataclasses - Domain models `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice` are declared in `price_monitor/monitor.py`.
- pytest 9.0.3 - Test runner available in the current environment; tests live in `tests/test_price_monitor.py`.
- pytest is not declared in `price_monitor/requirements.txt`; install it separately for local test execution.
- Docker - Container image built from `docker/price-monitor/Dockerfile`.
- Docker Compose - Service orchestration in `docker-compose.yml`.
- No linting or formatting tool detected in root config files.
## Key Dependencies
- `requests==2.31.0` - Performs outbound `GET` requests in `fetch_html()` and outbound Telegram `POST` requests in `telegram_post()` inside `price_monitor/monitor.py`.
- `beautifulsoup4==4.12.3` - Parses tour-price HTML in `parse_offers()`, `extract_hotel_name()`, and `extract_external_hotel_name()` inside `price_monitor/monitor.py`.
- Docker named volume `bg-price-monitor-data` - Persists `/data/last_snapshot.json`, `/data/price_history.json`, and `/data/settings.json` as configured by `docker-compose.yml` and `price_monitor/monitor.py`.
- Python logging module - Writes service logs to stdout through `configure_logging()` in `price_monitor/monitor.py`.
- Python threading module - Runs the Telegram control bot as a daemon thread through `TelegramControlBot.start()` in `price_monitor/monitor.py`.
## Configuration
- Runtime configuration is loaded from environment variables in `MonitorConfig.from_env()` inside `price_monitor/monitor.py`.
- Docker Compose injects environment variables in `docker-compose.yml`.
- `.env` file present - contains local environment configuration and must not be read or committed with secret values.
- `.env.example` file present - template environment file; do not treat example values as production secrets.
- Supported environment variables in `price_monitor/monitor.py`: `BG_MONITOR_URL`, `BG_DEPARTURE_FROM`, `BG_DEPARTURE_TO`, `BG_NIGHTS`, `BG_ROOM_FILTERS`, `BG_ROOM_CONTAINS`, `BG_CHECK_INTERVAL_SECONDS`, `BG_RUN_ONCE`, `BG_STATE_PATH`, `BG_SETTINGS_PATH`, `BG_STRONG_DIFF_RUB`, `BG_STRONG_DIFF_PERCENT`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `BG_TARGET_PRICE`, and `BG_HISTORY_PATH`.
- Runtime settings can override selected env-derived values through JSON at `BG_SETTINGS_PATH`, defaulting to `/data/settings.json`.
- `docker/price-monitor/Dockerfile` sets `WORKDIR /app`, installs `price_monitor/requirements.txt`, copies `price_monitor/`, sets `PYTHONUNBUFFERED=1`, and runs `python -m price_monitor.monitor`.
- `docker-compose.yml` builds the `bg-price-monitor` service from the repository root with Dockerfile `docker/price-monitor/Dockerfile`.
- `price_monitor/requirements.txt` is the only dependency manifest.
- `.gitignore` excludes `.env`, `.pytest_cache/`, `__pycache__/`, `*.pyc`, and `last_snapshot.json`.
## Platform Requirements
- Python 3.x with pytest installed to run `tests/test_price_monitor.py`.
- pip to install `price_monitor/requirements.txt`.
- Docker and Docker Compose for the documented runtime workflow in `README.md`.
- Network access to `bgoperator.ru`, `level.travel`, `travelata.ru`, and `api.telegram.org` for live monitoring.
- Docker Compose service `bg-price-monitor` in `docker-compose.yml`.
- Persistent Docker named volume `bg-price-monitor-data` mounted at `/data`.
- Environment configuration supplied through `.env` or equivalent deployment environment variables.
- No dedicated production hosting provider, orchestrator, or CI/CD platform detected.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Use lowercase Python module names with underscores for tests and package files.
- Production code lives in `price_monitor/monitor.py` and package metadata lives in `price_monitor/__init__.py`.
- Tests use `test_*.py` naming under `tests/`, as in `tests/test_price_monitor.py`.
- Use `snake_case` for module functions: `parse_offers`, `filter_offers`, `format_report`, `run_check`, and `normalize_search_url` in `price_monitor/monitor.py`.
- Prefix parsing helpers with `parse_`: `parse_nights`, `parse_ru_date`, `parse_external_price`, `parse_interval_text` in `price_monitor/monitor.py`.
- Prefix formatting helpers with `format_`: `format_report`, `format_price`, `format_changes`, `format_settings` in `price_monitor/monitor.py`.
- Prefix persistence helpers with explicit verbs: `load_runtime_settings`, `save_runtime_settings`, `load_snapshot`, `save_snapshot`, `load_price_history`, and `save_price_history` in `price_monitor/monitor.py`.
- Use `snake_case` for local variables and fields: `departure_date`, `price_rub`, `telegram_chat_id`, `target_price_rub`, and `history_path` in `price_monitor/monitor.py`.
- Use descriptive temporary names for parsed data: `room_cell`, `price_cell`, `booking_link`, `query`, `nights_raw`, and `current_snapshot` in `price_monitor/monitor.py`.
- Use `UPPER_CASE` for constants: `DEFAULT_URL`, `_MD_LINK_RE`, and `_MD_SPECIAL` in `price_monitor/monitor.py`.
- Use `PascalCase` for dataclasses and service classes: `Offer`, `MonitorConfig`, `SearchTarget`, `ExternalPrice`, and `TelegramControlBot` in `price_monitor/monitor.py`.
- Use frozen dataclasses for immutable value objects: `@dataclass(frozen=True)` on `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice` in `price_monitor/monitor.py`.
- Use built-in generic annotations: `list[Offer]`, `dict[str, object]`, `tuple[int, ...]`, and `str | None` in `price_monitor/monitor.py`.
## Code Style
- Formatter: Not detected.
- Formatting follows standard Python indentation with 4 spaces in `price_monitor/monitor.py` and `tests/test_price_monitor.py`.
- Use blank lines between top-level functions/classes and keep multiline literals wrapped in parentheses, as in `DEFAULT_URL` in `price_monitor/monitor.py`.
- Keep import blocks in this order: future import, standard library imports, third-party imports, local imports.
- Linter config: Not detected. No `pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, `ruff.toml`, `mypy.ini`, or dedicated lint config exists at the project root.
- Type checking is inline and partial. `price_monitor/monitor.py` uses annotations throughout and has targeted `# type: ignore[...]` comments where dynamic JSON shapes are accessed.
- Keep `# type: ignore[...]` comments specific and bracketed, matching `# type: ignore[index]` and `# type: ignore[arg-type]` in `price_monitor/monitor.py`.
## Import Organization
- Not detected. Imports use package paths such as `from price_monitor.monitor import parse_offers` in `tests/test_price_monitor.py`.
- Add new modules under `price_monitor/` and import them through `price_monitor.<module>` from tests.
## Error Handling
- Raise `ValueError` for invalid user/config input in parsing and validation helpers: `parse_nights`, `parse_int`, `parse_date_range_text`, `parse_interval_text`, and `normalize_search_url` in `price_monitor/monitor.py`.
- Return `None` for optional extraction misses instead of raising: `parse_usd`, `extract_hotel_name`, `extract_external_min_price`, `format_changes`, `format_new_minimums`, and `format_target_alerts` in `price_monitor/monitor.py`.
- Use HTTP library error handling for fetches: `fetch_html` calls `response.raise_for_status()` in `price_monitor/monitor.py`.
- Wrap Telegram API errors with `RuntimeError` carrying method, status, and response body in `telegram_post` in `price_monitor/monitor.py`.
- Catch `ValueError` separately for user-facing Telegram setting errors in `TelegramControlBot.apply_pending_action` in `price_monitor/monitor.py`.
- Log unexpected exceptions with stack traces via `logging.exception` in `TelegramControlBot.poll_forever`, `TelegramControlBot.apply_pending_action`, `TelegramControlBot.run_manual_check`, and `main` in `price_monitor/monitor.py`.
## Logging
- Configure process logging once in `configure_logging` in `price_monitor/monitor.py`.
- Write logs to stdout with `logging.basicConfig(..., stream=sys.stdout)` in `price_monitor/monitor.py` for Docker-friendly output.
- Use `logging.info` for lifecycle and successful check messages: Telegram bot startup/disabled state, price check completion, and next sleep interval in `price_monitor/monitor.py`.
- Use `logging.exception` inside broad exception handlers so stack traces are retained in `price_monitor/monitor.py`.
- Avoid `print()` in production code. No `print()` calls are used in `price_monitor/monitor.py`.
## Comments
- Use comments sparingly for non-obvious behavior. `run_check` in `price_monitor/monitor.py` includes a short comment explaining why first-run all-new-offer notifications are suppressed.
- Do not add narrative comments for straightforward parsing, filtering, or formatting helpers in `price_monitor/monitor.py`.
- Not applicable.
- Python docstrings are minimal. `price_monitor/__init__.py` contains the package docstring, while `price_monitor/monitor.py` uses type annotations and function names instead of docstrings.
## Function Design
- Existing small helpers in `price_monitor/monitor.py` handle parsing, formatting, extraction, and persistence independently.
- Larger orchestration stays in `run_check`, `TelegramControlBot`, and `main` in `price_monitor/monitor.py`.
- For new behavior, prefer adding a pure helper near related helpers instead of extending `run_check` or `TelegramControlBot.apply_pending_action` unless orchestration is required.
- Pass `MonitorConfig` into functions that need runtime settings, as in `filter_offers`, `format_report`, `send_telegram`, and `run_check` in `price_monitor/monitor.py`.
- Pass `Path` objects for filesystem operations, as in `load_snapshot`, `save_snapshot`, `load_price_history`, and `save_price_history` in `price_monitor/monitor.py`.
- Use `Iterable[Offer]` for functions that only iterate offers, as in `filter_offers` and `best_by_departure_and_nights` in `price_monitor/monitor.py`.
- Return lists for ordered collections: `parse_offers` returns `list[Offer]` and `split_telegram_text` returns `list[str]` in `price_monitor/monitor.py`.
- Return dictionaries for keyed snapshots and grouped offers: `best_by_departure_and_nights`, `snapshot`, `load_snapshot`, and `load_price_history` in `price_monitor/monitor.py`.
- Return `str | None` when a message section may be absent, as in `format_changes`, `format_new_minimums`, and `format_target_alerts` in `price_monitor/monitor.py`.
## Module Design
- No explicit `__all__` is defined in `price_monitor/__init__.py` or `price_monitor/monitor.py`.
- Tests import production functions directly from `price_monitor.monitor` in `tests/test_price_monitor.py`.
- Add new production helpers to `price_monitor/monitor.py` only if they fit the existing single-module layout; otherwise create a focused module under `price_monitor/` and import it by package path.
- `price_monitor/__init__.py` only contains a package docstring.
- Do not add re-export barrels unless the package gains a public API boundary.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Keep application behavior in `price_monitor/monitor.py`; this module is both the library surface used by tests and the executable entry point run by Docker.
- Use immutable dataclasses in `price_monitor/monitor.py` for core data structures: `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice`.
- Use JSON files for durable state and runtime settings through `load_snapshot`, `save_snapshot`, `load_price_history`, `save_price_history`, `load_runtime_settings`, and `save_runtime_settings` in `price_monitor/monitor.py`.
- Use synchronous HTTP requests through `requests` in `price_monitor/monitor.py`; there is no async framework, web server, database layer, or job queue.
- Run Telegram polling in a background `threading.Thread` from `TelegramControlBot.start` while the main loop performs scheduled checks.
## Layers
- Purpose: Convert environment variables and Telegram-edited runtime settings into an effective monitor configuration.
- Location: `price_monitor/monitor.py`
- Contains: `MonitorConfig.from_env`, `parse_nights`, `parse_filters`, `load_runtime_settings`, `save_runtime_settings`, `effective_config`, `parse_date_range_text`, `parse_diff_text`, and `parse_interval_text`.
- Depends on: `os.getenv`, `pathlib.Path`, `json`, and parsing helpers in `price_monitor/monitor.py`.
- Used by: `main`, `run_check`, `TelegramControlBot`, `format_settings`, and tests in `tests/test_price_monitor.py`.
- Purpose: Retrieve HTML pages from Biblio-Globus, Level.Travel, and Travelata search URLs.
- Location: `price_monitor/monitor.py`
- Contains: `fetch_html`, `provider_from_url`, `is_bgoperator_url`, and `normalize_search_url`.
- Depends on: `requests.get`, `urllib.parse.urlparse`, and configured target URLs from `SearchTarget`.
- Used by: `run_check` for scheduled checks and by `TelegramControlBot.apply_pending_action` for validating added search URLs.
- Purpose: Convert provider HTML into structured price data.
- Location: `price_monitor/monitor.py`
- Contains: `parse_offers`, `extract_hotel_name`, `parse_external_price`, `extract_external_hotel_name`, `extract_external_min_price`, `decode_js_string`, `parse_int`, `parse_usd`, and `first_query_value`.
- Depends on: `BeautifulSoup`, regular expressions in `re`, `json.loads`, and URL query parsing.
- Used by: `run_check`, report formatting functions, and tests in `tests/test_price_monitor.py`.
- Purpose: Filter offers, choose best prices, compute differences, detect changes, track historical minimums, and build alert text.
- Location: `price_monitor/monitor.py`
- Contains: `filter_offers`, `best_by_departure_and_nights`, `find_overall_best`, `snapshot`, `format_changes`, `update_price_history`, `historical_min_price`, `compute_trend`, `format_new_minimums`, `format_target_alerts`, `format_strong_diff_line`, and `adaptive_interval`.
- Depends on: `Offer`, `MonitorConfig`, `datetime`, and JSON-backed state loaded from disk.
- Used by: `run_check` and tests in `tests/test_price_monitor.py`.
- Purpose: Store last observed prices, historical price series, and Telegram-defined runtime settings.
- Location: `price_monitor/monitor.py`
- Contains: `load_snapshot`, `save_snapshot`, `load_price_history`, `save_price_history`, `load_runtime_settings`, and `save_runtime_settings`.
- Depends on: `Path.read_text`, `Path.write_text`, `Path.mkdir`, and `json`.
- Used by: `run_check`, `effective_config`, `load_search_targets`, and `TelegramControlBot.apply_pending_action`.
- Purpose: Send reports to Telegram and expose inline controls for manual checks and runtime settings.
- Location: `price_monitor/monitor.py`
- Contains: `send_telegram`, `telegram_post`, `split_telegram_text`, `escape_markdown_v2`, `main_keyboard`, `settings_keyboard`, `format_settings`, and `TelegramControlBot`.
- Depends on: Telegram Bot API over `requests.post`, MarkdownV2 escaping helpers, runtime settings persistence, and `threading.Lock`.
- Used by: `main` for scheduled notifications and by Telegram update handling methods in `TelegramControlBot`.
- Purpose: Build and run the monitor as a Dockerized service.
- Location: `docker-compose.yml` and `docker/price-monitor/Dockerfile`
- Contains: Docker Compose service `bg-price-monitor`, Python 3.11 image setup, package dependency installation from `price_monitor/requirements.txt`, and command `python -m price_monitor.monitor`.
- Depends on: `price_monitor/monitor.py`, `price_monitor/requirements.txt`, `.env` environment configuration, and the `bg-price-monitor-data` Docker volume.
- Used by: local and production-like service execution described in `README.md`.
## Data Flow
- Static configuration comes from environment variables in `MonitorConfig.from_env` inside `price_monitor/monitor.py`; `.env` is present at the project root and is consumed by Docker Compose without being committed into architecture docs.
- Runtime settings are JSON data at `MonitorConfig.settings_path`, defaulting to `/data/settings.json` in container execution.
- Last-check snapshots are JSON data at `MonitorConfig.state_path`, defaulting to `/data/last_snapshot.json`.
- Historical price points are JSON data at `MonitorConfig.history_path`, defaulting to `/data/price_history.json`.
- In-memory Telegram conversation state lives in `TelegramControlBot.pending` and is not persisted.
## Key Abstractions
- Purpose: Represent one Biblio-Globus room/date/night/price row.
- Examples: `Offer` in `price_monitor/monitor.py`, parser tests in `tests/test_price_monitor.py`.
- Pattern: Frozen dataclass with an `identity` property used as the snapshot key suffix.
- Purpose: Represent all monitor configuration needed by fetching, filtering, persistence, Telegram, and scheduling.
- Examples: `MonitorConfig` in `price_monitor/monitor.py`, direct test construction in `tests/test_price_monitor.py`.
- Pattern: Frozen dataclass built from environment variables by `MonitorConfig.from_env` and modified immutably with `dataclasses.replace` in `effective_config` and `run_check`.
- Purpose: Represent the primary search and any Telegram-added extra searches.
- Examples: `SearchTarget` and `load_search_targets` in `price_monitor/monitor.py`.
- Pattern: Frozen dataclass loaded from runtime settings, carrying a display name, URL, and optional per-target room filters.
- Purpose: Represent a provider-level reference price for non-Biblio-Globus pages.
- Examples: `ExternalPrice`, `parse_external_price`, and `format_external_report` in `price_monitor/monitor.py`.
- Pattern: Frozen dataclass populated from JSON-LD, page title, and min-price regex extraction.
- Purpose: Poll Telegram, authorize chats, render inline keyboards, handle settings updates, and run manual checks.
- Examples: `TelegramControlBot` in `price_monitor/monitor.py`.
- Pattern: Stateful controller class using `offset` for Telegram update pagination, `pending` for multi-message settings flows, and a shared `threading.Lock` around `run_check`.
- Purpose: Store current and previous offers in a JSON-serializable structure.
- Examples: `snapshot`, `load_snapshot`, `save_snapshot`, `format_changes`, and `update_price_history` in `price_monitor/monitor.py`.
- Pattern: `dict[str, dict[str, object]]` keyed by target name plus `Offer.identity`.
## Entry Points
- Location: `price_monitor/monitor.py`
- Triggers: `python -m price_monitor.monitor`, Docker `CMD`, or direct script execution.
- Responsibilities: Configure logging, build `MonitorConfig`, start Telegram polling, run scheduled checks, send Telegram notifications, and sleep between checks.
- Location: `docker/price-monitor/Dockerfile`
- Triggers: `docker compose up`, `docker compose run`, or any container runtime using the image.
- Responsibilities: Install `price_monitor/requirements.txt`, copy `price_monitor/`, set unbuffered Python output, and execute `python -m price_monitor.monitor`.
- Location: `docker-compose.yml`
- Triggers: `docker compose up -d --build` or `docker compose run --rm`.
- Responsibilities: Build `bg-price-monitor`, provide environment configuration, mount the persistent data volume, and run the monitor container.
- Location: `price_monitor/__init__.py`
- Triggers: `import price_monitor`.
- Responsibilities: Mark `price_monitor/` as a package; application symbols are imported from `price_monitor.monitor`.
- Location: `tests/test_price_monitor.py`
- Triggers: `pytest`.
- Responsibilities: Exercise parser, filtering, best-offer selection, Markdown escaping, interval parsing, URL validation, hotel-name extraction, and external price parsing helpers from `price_monitor/monitor.py`.
## Error Handling
- `fetch_html` in `price_monitor/monitor.py` calls `response.raise_for_status`; HTTP failures propagate to `run_check` callers.
- `telegram_post` in `price_monitor/monitor.py` raises `RuntimeError` on Telegram API HTTP errors and returns parsed JSON on success.
- `main` in `price_monitor/monitor.py` catches all exceptions around scheduled checks, logs with `logging.exception`, exits with status `1` only when `MonitorConfig.run_once` is true, and otherwise continues.
- `TelegramControlBot.poll_forever` in `price_monitor/monitor.py` catches all polling exceptions, logs the stack trace, sleeps five seconds, and resumes polling.
- `TelegramControlBot.apply_pending_action` in `price_monitor/monitor.py` handles `ValueError` with a user-facing validation message and logs unexpected exceptions.
- Parsing helpers such as `parse_nights`, `parse_int`, `parse_date_range_text`, `parse_interval_text`, and `normalize_search_url` in `price_monitor/monitor.py` raise `ValueError` for invalid inputs.
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
