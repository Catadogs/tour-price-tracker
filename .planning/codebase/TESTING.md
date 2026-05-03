# Testing Patterns

**Analysis Date:** 2026-05-03

## Test Framework

**Runner:**
- Pytest
- Version: Not declared in project files.
- Config: Not detected. No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` exists at the project root.
- Tests are discovered from `tests/test_price_monitor.py`.

**Assertion Library:**
- Plain Python `assert` statements in `tests/test_price_monitor.py`.

**Run Commands:**
```bash
python -m pytest              # Run all tests
python -m pytest -q           # Run all tests with concise output
python -m pytest tests/test_price_monitor.py -q  # Run the current test module
```

**Current Result:**
- `python -m pytest -q` collects 11 tests from `tests/test_price_monitor.py`.
- Result: 9 passed, 2 failed.
- Failing tests:
  - `tests/test_price_monitor.py::test_filter_and_best_offer_by_departure_and_nights`
  - `tests/test_price_monitor.py::test_strong_diff_line_flags_large_12_13_gap`
- Failure cause: `MonitorConfig` in `price_monitor/monitor.py` requires `target_price_rub` and `history_path`, but the two test constructors in `tests/test_price_monitor.py` omit those fields.

## Test File Organization

**Location:**
- Tests live in the top-level `tests/` directory.
- Production code lives in `price_monitor/`.
- The current test module is `tests/test_price_monitor.py`.

**Naming:**
- Test files use `test_*.py`.
- Test functions use descriptive `test_<behavior>` names, such as `test_parse_offers_extracts_price_and_booking_fields` and `test_parse_external_price_from_level_microdata` in `tests/test_price_monitor.py`.

**Structure:**
```text
tests/
└── test_price_monitor.py      # Unit tests for helpers in price_monitor/monitor.py
```

## Test Structure

**Suite Organization:**
```python
from pathlib import Path

from price_monitor.monitor import (
    MonitorConfig,
    best_by_departure_and_nights,
    filter_offers,
    parse_offers,
)


def test_parse_offers_extracts_price_and_booking_fields():
    html = """
    <table>
      <tr>
        <td class="c_ns c_ns__ai">SUPERIOR DELUXE Garden View AI<br>ALL INCLUSIVE</td>
        <td class="c_pe">
          <b class=r>286230</b>
          <a href="https://www.bgoperator.ru/zaya?dt=14.09.2026&kol=12&otn=104610620518" title="3542 USD">Buy</a>
        </td>
      </tr>
    </table>
    """

    offers = parse_offers(html)

    assert len(offers) == 1
    assert offers[0].departure_date == "14.09.2026"
    assert offers[0].nights == 12
```

**Patterns:**
- Use inline HTML strings as fixtures for parser tests in `tests/test_price_monitor.py`.
- Arrange data, call one production function or a short function chain, then assert concrete fields.
- Test parser and formatter behavior with deterministic inputs; avoid network and filesystem access in unit tests.
- Build `MonitorConfig` directly for filtering and formatting tests. Include all required fields from `price_monitor/monitor.py`: `target_price_rub` and `history_path` are required.

## Mocking

**Framework:** Not used

**Patterns:**
```python
# No mocking pattern is present in tests/test_price_monitor.py.
# Existing tests use inline strings and direct function calls instead.
offers = parse_offers(html)
assert offers[0].price_rub == 286230
```

**What to Mock:**
- Mock `requests.get` or wrap `fetch_html` when testing `run_check` from `price_monitor/monitor.py`.
- Mock `telegram_post` or `requests.post` when testing `send_telegram` and `TelegramControlBot` behavior in `price_monitor/monitor.py`.
- Mock filesystem reads/writes or use `tmp_path` when testing `load_snapshot`, `save_snapshot`, `load_price_history`, `save_price_history`, `load_runtime_settings`, and `save_runtime_settings` in `price_monitor/monitor.py`.

**What NOT to Mock:**
- Do not mock pure parsing helpers such as `parse_offers`, `parse_external_price`, `extract_hotel_name`, `parse_date_range_text`, `parse_diff_text`, `parse_interval_text`, or `normalize_search_url` in `price_monitor/monitor.py`.
- Do not mock `BeautifulSoup` for parser tests; supply representative HTML strings in `tests/test_price_monitor.py`.
- Do not mock `MonitorConfig` for pure unit tests; instantiate the dataclass with explicit values.

## Fixtures and Factories

**Test Data:**
```python
html = """
<table>
  <tr><td class="c_ns">Room A</td><td class="c_pe"><b class=r>300000</b><a href="/zaya?dt=14.09.2026&kol=12&otn=a" title="3700 USD">Buy</a></td></tr>
  <tr><td class="c_ns">Room B</td><td class="c_pe"><b class=r>280000</b><a href="/zaya?dt=14.09.2026&kol=12&otn=b" title="3500 USD">Buy</a></td></tr>
</table>
"""
```

**Location:**
- Inline test data lives inside individual test functions in `tests/test_price_monitor.py`.
- No shared fixture files, `conftest.py`, or test factories are present.
- If more tests need `MonitorConfig`, add a small local helper or pytest fixture in `tests/test_price_monitor.py` or `tests/conftest.py` to keep constructor changes centralized.

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
python -m pytest --cov=price_monitor  # Requires pytest-cov; not declared in project files
```

**Coverage Configuration:**
- Not detected. No coverage config exists in repository files.
- `price_monitor/requirements.txt` does not include pytest, pytest-cov, or other test tooling.

## Test Types

**Unit Tests:**
- Present in `tests/test_price_monitor.py`.
- Covered behaviors include Biblio-Globus offer parsing, filtering/best selection, strong 12/13 night diff formatting, date range parsing, diff threshold parsing, URL normalization, Telegram Markdown escaping, interval parsing/formatting, hotel name extraction, and external price parsing.
- Unit tests are deterministic and use inline strings rather than live HTTP calls.

**Integration Tests:**
- Not used.
- No tests exercise `run_check`, snapshot/history persistence, runtime settings persistence, Telegram API posting, Telegram polling, Docker execution, or environment loading from `MonitorConfig.from_env` in `price_monitor/monitor.py`.

**E2E Tests:**
- Not used.
- No browser, Docker, or live service tests are present.

## Common Patterns

**Async Testing:**
```python
# Not applicable. The code uses a background threading.Thread in
# TelegramControlBot.start in price_monitor/monitor.py, but tests do not cover it.
```

**Error Testing:**
```python
# No pytest.raises pattern is present in tests/test_price_monitor.py.
# Use this pattern for parser validation errors in price_monitor/monitor.py:
import pytest

def test_parse_interval_text_rejects_short_interval():
    with pytest.raises(ValueError, match="minimum interval"):
        parse_interval_text("60s")
```

**Filesystem Testing:**
```python
def test_save_snapshot_round_trips(tmp_path):
    path = tmp_path / "state.json"
    data = {"Main search|14.09.2026|12|a": {"price_rub": 280000}}

    save_snapshot(path, data)

    assert load_snapshot(path) == data
```

**HTTP Testing:**
```python
def test_fetch_html_uses_timeout_and_headers(monkeypatch):
    calls = []

    class Response:
        text = "<html></html>"

        def raise_for_status(self):
            return None

    def fake_get(url, timeout, headers):
        calls.append((url, timeout, headers))
        return Response()

    monkeypatch.setattr("price_monitor.monitor.requests.get", fake_get)

    assert fetch_html("https://example.test") == "<html></html>"
    assert calls[0][1] == 30
```

---

*Testing analysis: 2026-05-03*
