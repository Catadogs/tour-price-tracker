from pathlib import Path

from price_monitor.parsers import bgoperator
from price_monitor.parsers import leveltravel
from price_monitor.parsers import travelata
from price_monitor.parsers._fetch import fetch_with_retry


FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_bgoperator_parses_offers_from_fixture():
    html = _load_fixture("bgoperator.html")
    offers = bgoperator.parse_offers(html)

    assert len(offers) == 1
    assert offers[0].departure_date == "14.09.2026"
    assert offers[0].nights == 12
    assert offers[0].price_rub == 286230
    assert offers[0].price_usd == 3542
    assert offers[0].hotel_option_id == "104610620518"
    assert "SUPERIOR DELUXE" in offers[0].room


def test_bgoperator_extract_hotel_name_from_fixture():
    html = _load_fixture("bgoperator.html")
    name = bgoperator.extract_hotel_name(html, "https://www.bgoperator.ru/price.shtml?F4=102632942104")
    # Fixture has no hotel catalog JSON, so fallback to title extraction
    assert name is None  # inline fixture has no <title>


def test_leveltravel_parses_price_from_fixture():
    html = _load_fixture("leveltravel.html")
    price = leveltravel.parse_external_price(html, "https://level.travel/hotels/629-test")

    assert price.provider == "Level.Travel"
    assert price.hotel_name == "Jaz Makadi Oasis"
    assert price.price_rub == 138920


def test_travelata_parses_price_from_fixture():
    html = _load_fixture("travelata.html")
    price = travelata.parse_external_price(html, "https://travelata.ru/")

    assert price.provider == "Travelata"
    assert price.hotel_name == "Jaz Makadi Star"
    assert price.price_rub == 165000


def test_fetch_with_retry_rate_limits(monkeypatch):
    """Verify that fetch_with_retry enforces rate limit between calls."""
    call_times: list[float] = []
    call_count = [0]

    import time as _time

    def mock_get(url, timeout, headers):
        call_times.append(_time.monotonic())
        call_count[0] += 1

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            text = "mock"

        return MockResponse()

    monkeypatch.setattr("price_monitor.parsers._fetch.requests.get", mock_get)

    # First call — no wait
    fetch_with_retry("https://test.test", "test-provider", rate_limit_seconds=0.1, max_retries=0)
    # Second call — should wait ~0.1s
    fetch_with_retry("https://test.test", "test-provider", rate_limit_seconds=0.1, max_retries=0)

    assert call_count[0] == 2
    # Time between calls should be >= rate_limit_seconds
    gap = call_times[1] - call_times[0]
    assert gap >= 0.09  # allow small timing variance


def test_fetch_with_retry_backoff(monkeypatch):
    """Verify that fetch_with_retry retries on HTTP 500 with backoff."""
    import requests as _requests

    attempt_times: list[float] = []
    attempts = [0]

    import time as _time

    def mock_get(url, timeout, headers):
        attempts[0] += 1
        attempt_times.append(_time.monotonic())

        class MockResponse:
            status_code = 500

            def raise_for_status(self):
                raise _requests.HTTPError(response=self)  # type: ignore[arg-type]

        return MockResponse()

    monkeypatch.setattr("price_monitor.parsers._fetch.requests.get", mock_get)

    try:
        fetch_with_retry("https://test.test", "test-provider", rate_limit_seconds=0, max_retries=2, timeout=1)
    except Exception:
        pass

    # Should have tried 3 times (initial + 2 retries)
    assert attempts[0] == 3
    # Check backoff: gap between attempts 1→2 should be ~1s, 2→3 should be ~2s
    gap1 = attempt_times[1] - attempt_times[0]
    gap2 = attempt_times[2] - attempt_times[1]
    assert gap1 >= 0.9
    assert gap2 >= 1.9
