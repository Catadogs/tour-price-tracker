# Architecture

**Analysis Date:** 2026-05-03

## Pattern Overview

**Overall:** Single-package procedural service with dataclass domain models and an optional Telegram control loop.

**Key Characteristics:**
- Keep application behavior in `price_monitor/monitor.py`; this module is both the library surface used by tests and the executable entry point run by Docker.
- Use immutable dataclasses in `price_monitor/monitor.py` for core data structures: `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice`.
- Use JSON files for durable state and runtime settings through `load_snapshot`, `save_snapshot`, `load_price_history`, `save_price_history`, `load_runtime_settings`, and `save_runtime_settings` in `price_monitor/monitor.py`.
- Use synchronous HTTP requests through `requests` in `price_monitor/monitor.py`; there is no async framework, web server, database layer, or job queue.
- Run Telegram polling in a background `threading.Thread` from `TelegramControlBot.start` while the main loop performs scheduled checks.

## Layers

**Configuration Layer:**
- Purpose: Convert environment variables and Telegram-edited runtime settings into an effective monitor configuration.
- Location: `price_monitor/monitor.py`
- Contains: `MonitorConfig.from_env`, `parse_nights`, `parse_filters`, `load_runtime_settings`, `save_runtime_settings`, `effective_config`, `parse_date_range_text`, `parse_diff_text`, and `parse_interval_text`.
- Depends on: `os.getenv`, `pathlib.Path`, `json`, and parsing helpers in `price_monitor/monitor.py`.
- Used by: `main`, `run_check`, `TelegramControlBot`, `format_settings`, and tests in `tests/test_price_monitor.py`.

**Fetching Layer:**
- Purpose: Retrieve HTML pages from Biblio-Globus, Level.Travel, and Travelata search URLs.
- Location: `price_monitor/monitor.py`
- Contains: `fetch_html`, `provider_from_url`, `is_bgoperator_url`, and `normalize_search_url`.
- Depends on: `requests.get`, `urllib.parse.urlparse`, and configured target URLs from `SearchTarget`.
- Used by: `run_check` for scheduled checks and by `TelegramControlBot.apply_pending_action` for validating added search URLs.

**Parsing Layer:**
- Purpose: Convert provider HTML into structured price data.
- Location: `price_monitor/monitor.py`
- Contains: `parse_offers`, `extract_hotel_name`, `parse_external_price`, `extract_external_hotel_name`, `extract_external_min_price`, `decode_js_string`, `parse_int`, `parse_usd`, and `first_query_value`.
- Depends on: `BeautifulSoup`, regular expressions in `re`, `json.loads`, and URL query parsing.
- Used by: `run_check`, report formatting functions, and tests in `tests/test_price_monitor.py`.

**Selection and Comparison Layer:**
- Purpose: Filter offers, choose best prices, compute differences, detect changes, track historical minimums, and build alert text.
- Location: `price_monitor/monitor.py`
- Contains: `filter_offers`, `best_by_departure_and_nights`, `find_overall_best`, `snapshot`, `format_changes`, `update_price_history`, `historical_min_price`, `compute_trend`, `format_new_minimums`, `format_target_alerts`, `format_strong_diff_line`, and `adaptive_interval`.
- Depends on: `Offer`, `MonitorConfig`, `datetime`, and JSON-backed state loaded from disk.
- Used by: `run_check` and tests in `tests/test_price_monitor.py`.

**Persistence Layer:**
- Purpose: Store last observed prices, historical price series, and Telegram-defined runtime settings.
- Location: `price_monitor/monitor.py`
- Contains: `load_snapshot`, `save_snapshot`, `load_price_history`, `save_price_history`, `load_runtime_settings`, and `save_runtime_settings`.
- Depends on: `Path.read_text`, `Path.write_text`, `Path.mkdir`, and `json`.
- Used by: `run_check`, `effective_config`, `load_search_targets`, and `TelegramControlBot.apply_pending_action`.

**Notification and Control Layer:**
- Purpose: Send reports to Telegram and expose inline controls for manual checks and runtime settings.
- Location: `price_monitor/monitor.py`
- Contains: `send_telegram`, `telegram_post`, `split_telegram_text`, `escape_markdown_v2`, `main_keyboard`, `settings_keyboard`, `format_settings`, and `TelegramControlBot`.
- Depends on: Telegram Bot API over `requests.post`, MarkdownV2 escaping helpers, runtime settings persistence, and `threading.Lock`.
- Used by: `main` for scheduled notifications and by Telegram update handling methods in `TelegramControlBot`.

**Packaging Layer:**
- Purpose: Build and run the monitor as a Dockerized service.
- Location: `docker-compose.yml` and `docker/price-monitor/Dockerfile`
- Contains: Docker Compose service `bg-price-monitor`, Python 3.11 image setup, package dependency installation from `price_monitor/requirements.txt`, and command `python -m price_monitor.monitor`.
- Depends on: `price_monitor/monitor.py`, `price_monitor/requirements.txt`, `.env` environment configuration, and the `bg-price-monitor-data` Docker volume.
- Used by: local and production-like service execution described in `README.md`.

## Data Flow

**Scheduled Price Check:**

1. `main` in `price_monitor/monitor.py` calls `configure_logging`, creates `MonitorConfig.from_env`, starts `TelegramControlBot`, and enters the check loop.
2. `run_check` calls `effective_config` to merge `.env`-backed configuration with runtime settings from `settings_path`.
3. `load_search_targets` returns the primary configured URL plus any Telegram-added searches from runtime settings.
4. Each `SearchTarget.url` is fetched by `fetch_html`.
5. Biblio-Globus URLs flow through `parse_offers`, `filter_offers`, `best_by_departure_and_nights`, `format_report`, and `snapshot`.
6. Level.Travel, Travelata, and other supported non-Biblio-Globus URLs flow through `parse_external_price` and `format_external_report`.
7. `run_check` reads previous state with `load_snapshot` and price history with `load_price_history`.
8. `format_changes`, `format_new_minimums`, and `format_target_alerts` generate alert sections.
9. `update_price_history`, `save_price_history`, and `save_snapshot` persist current state before `run_check` returns the full message.
10. `main` sends the returned message via `send_telegram`, then sleeps for `adaptive_interval`.

**Telegram Manual Check:**

1. `TelegramControlBot.poll_forever` calls Telegram `getUpdates` through `TelegramControlBot.api`.
2. `handle_update` routes messages to `handle_message` and inline callbacks to `handle_callback`.
3. `/check` or the `check` callback calls `run_manual_check`.
4. `run_manual_check` uses the shared `threading.Lock` to prevent overlap with the scheduled `main` loop.
5. The result of `run_check` is sent back with `TelegramControlBot.send_message`.

**Telegram Runtime Settings:**

1. Inline callbacks in `TelegramControlBot.handle_callback` set a pending action in `TelegramControlBot.pending`.
2. The next text message for that chat is processed by `TelegramControlBot.apply_pending_action`.
3. The action validates input with helpers such as `normalize_search_url`, `parse_date_range_text`, `parse_nights`, `parse_diff_text`, and `parse_interval_text`.
4. Updated values are written through `save_runtime_settings` to `MonitorConfig.settings_path`.
5. Future scheduled and manual checks use `effective_config` and `load_search_targets` to apply the saved runtime settings.

**State Management:**
- Static configuration comes from environment variables in `MonitorConfig.from_env` inside `price_monitor/monitor.py`; `.env` is present at the project root and is consumed by Docker Compose without being committed into architecture docs.
- Runtime settings are JSON data at `MonitorConfig.settings_path`, defaulting to `/data/settings.json` in container execution.
- Last-check snapshots are JSON data at `MonitorConfig.state_path`, defaulting to `/data/last_snapshot.json`.
- Historical price points are JSON data at `MonitorConfig.history_path`, defaulting to `/data/price_history.json`.
- In-memory Telegram conversation state lives in `TelegramControlBot.pending` and is not persisted.

## Key Abstractions

**Offer:**
- Purpose: Represent one Biblio-Globus room/date/night/price row.
- Examples: `Offer` in `price_monitor/monitor.py`, parser tests in `tests/test_price_monitor.py`.
- Pattern: Frozen dataclass with an `identity` property used as the snapshot key suffix.

**MonitorConfig:**
- Purpose: Represent all monitor configuration needed by fetching, filtering, persistence, Telegram, and scheduling.
- Examples: `MonitorConfig` in `price_monitor/monitor.py`, direct test construction in `tests/test_price_monitor.py`.
- Pattern: Frozen dataclass built from environment variables by `MonitorConfig.from_env` and modified immutably with `dataclasses.replace` in `effective_config` and `run_check`.

**SearchTarget:**
- Purpose: Represent the primary search and any Telegram-added extra searches.
- Examples: `SearchTarget` and `load_search_targets` in `price_monitor/monitor.py`.
- Pattern: Frozen dataclass loaded from runtime settings, carrying a display name, URL, and optional per-target room filters.

**ExternalPrice:**
- Purpose: Represent a provider-level reference price for non-Biblio-Globus pages.
- Examples: `ExternalPrice`, `parse_external_price`, and `format_external_report` in `price_monitor/monitor.py`.
- Pattern: Frozen dataclass populated from JSON-LD, page title, and min-price regex extraction.

**TelegramControlBot:**
- Purpose: Poll Telegram, authorize chats, render inline keyboards, handle settings updates, and run manual checks.
- Examples: `TelegramControlBot` in `price_monitor/monitor.py`.
- Pattern: Stateful controller class using `offset` for Telegram update pagination, `pending` for multi-message settings flows, and a shared `threading.Lock` around `run_check`.

**Snapshot Dictionaries:**
- Purpose: Store current and previous offers in a JSON-serializable structure.
- Examples: `snapshot`, `load_snapshot`, `save_snapshot`, `format_changes`, and `update_price_history` in `price_monitor/monitor.py`.
- Pattern: `dict[str, dict[str, object]]` keyed by target name plus `Offer.identity`.

## Entry Points

**Python Module Entry Point:**
- Location: `price_monitor/monitor.py`
- Triggers: `python -m price_monitor.monitor`, Docker `CMD`, or direct script execution.
- Responsibilities: Configure logging, build `MonitorConfig`, start Telegram polling, run scheduled checks, send Telegram notifications, and sleep between checks.

**Docker Service Entry Point:**
- Location: `docker/price-monitor/Dockerfile`
- Triggers: `docker compose up`, `docker compose run`, or any container runtime using the image.
- Responsibilities: Install `price_monitor/requirements.txt`, copy `price_monitor/`, set unbuffered Python output, and execute `python -m price_monitor.monitor`.

**Compose Service Definition:**
- Location: `docker-compose.yml`
- Triggers: `docker compose up -d --build` or `docker compose run --rm`.
- Responsibilities: Build `bg-price-monitor`, provide environment configuration, mount the persistent data volume, and run the monitor container.

**Package Import Surface:**
- Location: `price_monitor/__init__.py`
- Triggers: `import price_monitor`.
- Responsibilities: Mark `price_monitor/` as a package; application symbols are imported from `price_monitor.monitor`.

**Test Entry Point:**
- Location: `tests/test_price_monitor.py`
- Triggers: `pytest`.
- Responsibilities: Exercise parser, filtering, best-offer selection, Markdown escaping, interval parsing, URL validation, hotel-name extraction, and external price parsing helpers from `price_monitor/monitor.py`.

## Error Handling

**Strategy:** Use synchronous exceptions at boundaries, catch them at long-running loop boundaries, and keep pure parsing helpers explicit with `ValueError` for invalid user input.

**Patterns:**
- `fetch_html` in `price_monitor/monitor.py` calls `response.raise_for_status`; HTTP failures propagate to `run_check` callers.
- `telegram_post` in `price_monitor/monitor.py` raises `RuntimeError` on Telegram API HTTP errors and returns parsed JSON on success.
- `main` in `price_monitor/monitor.py` catches all exceptions around scheduled checks, logs with `logging.exception`, exits with status `1` only when `MonitorConfig.run_once` is true, and otherwise continues.
- `TelegramControlBot.poll_forever` in `price_monitor/monitor.py` catches all polling exceptions, logs the stack trace, sleeps five seconds, and resumes polling.
- `TelegramControlBot.apply_pending_action` in `price_monitor/monitor.py` handles `ValueError` with a user-facing validation message and logs unexpected exceptions.
- Parsing helpers such as `parse_nights`, `parse_int`, `parse_date_range_text`, `parse_interval_text`, and `normalize_search_url` in `price_monitor/monitor.py` raise `ValueError` for invalid inputs.

## Cross-Cutting Concerns

**Logging:** `configure_logging` in `price_monitor/monitor.py` sends `logging` output to stdout with timestamps and `INFO` level; scheduled, manual, and polling failures use `logging.exception`.
**Validation:** URL, date, interval, threshold, and night-list validation is centralized in helper functions in `price_monitor/monitor.py`; Telegram settings flows call those helpers before writing runtime settings.
**Authentication:** Telegram authorization is handled by `TelegramControlBot.is_authorized` in `price_monitor/monitor.py`; when `MonitorConfig.telegram_chat_id` is set, only that chat id is allowed, otherwise any chat can interact with the bot.

---

*Architecture analysis: 2026-05-03*
