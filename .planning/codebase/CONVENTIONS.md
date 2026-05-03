# Coding Conventions

**Analysis Date:** 2026-05-03

## Naming Patterns

**Files:**
- Use lowercase Python module names with underscores for tests and package files.
- Production code lives in `price_monitor/monitor.py` and package metadata lives in `price_monitor/__init__.py`.
- Tests use `test_*.py` naming under `tests/`, as in `tests/test_price_monitor.py`.

**Functions:**
- Use `snake_case` for module functions: `parse_offers`, `filter_offers`, `format_report`, `run_check`, and `normalize_search_url` in `price_monitor/monitor.py`.
- Prefix parsing helpers with `parse_`: `parse_nights`, `parse_ru_date`, `parse_external_price`, `parse_interval_text` in `price_monitor/monitor.py`.
- Prefix formatting helpers with `format_`: `format_report`, `format_price`, `format_changes`, `format_settings` in `price_monitor/monitor.py`.
- Prefix persistence helpers with explicit verbs: `load_runtime_settings`, `save_runtime_settings`, `load_snapshot`, `save_snapshot`, `load_price_history`, and `save_price_history` in `price_monitor/monitor.py`.

**Variables:**
- Use `snake_case` for local variables and fields: `departure_date`, `price_rub`, `telegram_chat_id`, `target_price_rub`, and `history_path` in `price_monitor/monitor.py`.
- Use descriptive temporary names for parsed data: `room_cell`, `price_cell`, `booking_link`, `query`, `nights_raw`, and `current_snapshot` in `price_monitor/monitor.py`.
- Use `UPPER_CASE` for constants: `DEFAULT_URL`, `_MD_LINK_RE`, and `_MD_SPECIAL` in `price_monitor/monitor.py`.

**Types:**
- Use `PascalCase` for dataclasses and service classes: `Offer`, `MonitorConfig`, `SearchTarget`, `ExternalPrice`, and `TelegramControlBot` in `price_monitor/monitor.py`.
- Use frozen dataclasses for immutable value objects: `@dataclass(frozen=True)` on `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice` in `price_monitor/monitor.py`.
- Use built-in generic annotations: `list[Offer]`, `dict[str, object]`, `tuple[int, ...]`, and `str | None` in `price_monitor/monitor.py`.

## Code Style

**Formatting:**
- Formatter: Not detected.
- Formatting follows standard Python indentation with 4 spaces in `price_monitor/monitor.py` and `tests/test_price_monitor.py`.
- Use blank lines between top-level functions/classes and keep multiline literals wrapped in parentheses, as in `DEFAULT_URL` in `price_monitor/monitor.py`.
- Keep import blocks in this order: future import, standard library imports, third-party imports, local imports.

**Linting:**
- Linter config: Not detected. No `pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, `ruff.toml`, `mypy.ini`, or dedicated lint config exists at the project root.
- Type checking is inline and partial. `price_monitor/monitor.py` uses annotations throughout and has targeted `# type: ignore[...]` comments where dynamic JSON shapes are accessed.
- Keep `# type: ignore[...]` comments specific and bracketed, matching `# type: ignore[index]` and `# type: ignore[arg-type]` in `price_monitor/monitor.py`.

## Import Organization

**Order:**
1. `from __future__ import annotations` at the top of production modules, as in `price_monitor/monitor.py`.
2. Standard library imports: `json`, `logging`, `os`, `re`, `sys`, `threading`, `time`, `dataclasses`, `datetime`, `pathlib`, `typing`, and `urllib.parse` in `price_monitor/monitor.py`.
3. Third-party imports: `requests` and `BeautifulSoup` in `price_monitor/monitor.py`.
4. Test imports from the package under test, as in `tests/test_price_monitor.py`.

**Path Aliases:**
- Not detected. Imports use package paths such as `from price_monitor.monitor import parse_offers` in `tests/test_price_monitor.py`.
- Add new modules under `price_monitor/` and import them through `price_monitor.<module>` from tests.

## Error Handling

**Patterns:**
- Raise `ValueError` for invalid user/config input in parsing and validation helpers: `parse_nights`, `parse_int`, `parse_date_range_text`, `parse_interval_text`, and `normalize_search_url` in `price_monitor/monitor.py`.
- Return `None` for optional extraction misses instead of raising: `parse_usd`, `extract_hotel_name`, `extract_external_min_price`, `format_changes`, `format_new_minimums`, and `format_target_alerts` in `price_monitor/monitor.py`.
- Use HTTP library error handling for fetches: `fetch_html` calls `response.raise_for_status()` in `price_monitor/monitor.py`.
- Wrap Telegram API errors with `RuntimeError` carrying method, status, and response body in `telegram_post` in `price_monitor/monitor.py`.
- Catch `ValueError` separately for user-facing Telegram setting errors in `TelegramControlBot.apply_pending_action` in `price_monitor/monitor.py`.
- Log unexpected exceptions with stack traces via `logging.exception` in `TelegramControlBot.poll_forever`, `TelegramControlBot.apply_pending_action`, `TelegramControlBot.run_manual_check`, and `main` in `price_monitor/monitor.py`.

## Logging

**Framework:** `logging`

**Patterns:**
- Configure process logging once in `configure_logging` in `price_monitor/monitor.py`.
- Write logs to stdout with `logging.basicConfig(..., stream=sys.stdout)` in `price_monitor/monitor.py` for Docker-friendly output.
- Use `logging.info` for lifecycle and successful check messages: Telegram bot startup/disabled state, price check completion, and next sleep interval in `price_monitor/monitor.py`.
- Use `logging.exception` inside broad exception handlers so stack traces are retained in `price_monitor/monitor.py`.
- Avoid `print()` in production code. No `print()` calls are used in `price_monitor/monitor.py`.

## Comments

**When to Comment:**
- Use comments sparingly for non-obvious behavior. `run_check` in `price_monitor/monitor.py` includes a short comment explaining why first-run all-new-offer notifications are suppressed.
- Do not add narrative comments for straightforward parsing, filtering, or formatting helpers in `price_monitor/monitor.py`.

**JSDoc/TSDoc:**
- Not applicable.
- Python docstrings are minimal. `price_monitor/__init__.py` contains the package docstring, while `price_monitor/monitor.py` uses type annotations and function names instead of docstrings.

## Function Design

**Size:** Keep new pure helpers small and single-purpose.
- Existing small helpers in `price_monitor/monitor.py` handle parsing, formatting, extraction, and persistence independently.
- Larger orchestration stays in `run_check`, `TelegramControlBot`, and `main` in `price_monitor/monitor.py`.
- For new behavior, prefer adding a pure helper near related helpers instead of extending `run_check` or `TelegramControlBot.apply_pending_action` unless orchestration is required.

**Parameters:** Use typed parameters and concrete domain objects.
- Pass `MonitorConfig` into functions that need runtime settings, as in `filter_offers`, `format_report`, `send_telegram`, and `run_check` in `price_monitor/monitor.py`.
- Pass `Path` objects for filesystem operations, as in `load_snapshot`, `save_snapshot`, `load_price_history`, and `save_price_history` in `price_monitor/monitor.py`.
- Use `Iterable[Offer]` for functions that only iterate offers, as in `filter_offers` and `best_by_departure_and_nights` in `price_monitor/monitor.py`.

**Return Values:** Return typed domain structures.
- Return lists for ordered collections: `parse_offers` returns `list[Offer]` and `split_telegram_text` returns `list[str]` in `price_monitor/monitor.py`.
- Return dictionaries for keyed snapshots and grouped offers: `best_by_departure_and_nights`, `snapshot`, `load_snapshot`, and `load_price_history` in `price_monitor/monitor.py`.
- Return `str | None` when a message section may be absent, as in `format_changes`, `format_new_minimums`, and `format_target_alerts` in `price_monitor/monitor.py`.

## Module Design

**Exports:** Direct module imports
- No explicit `__all__` is defined in `price_monitor/__init__.py` or `price_monitor/monitor.py`.
- Tests import production functions directly from `price_monitor.monitor` in `tests/test_price_monitor.py`.
- Add new production helpers to `price_monitor/monitor.py` only if they fit the existing single-module layout; otherwise create a focused module under `price_monitor/` and import it by package path.

**Barrel Files:** Not used
- `price_monitor/__init__.py` only contains a package docstring.
- Do not add re-export barrels unless the package gains a public API boundary.

---

*Convention analysis: 2026-05-03*
