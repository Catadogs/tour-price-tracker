from pathlib import Path

from price_monitor.currency import (
    fetch_exchange_rates,
    format_currency_alert,
)
from price_monitor import storage


def test_fetch_exchange_rates_parses_cbr_style_json(monkeypatch):
    """Test parsing of CBR mirror JSON format."""

    def mock_get(url, timeout, headers):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "Valute": {
                        "USD": {"CharCode": "USD", "Value": 97.5},
                        "EUR": {"CharCode": "EUR", "Value": 106.2},
                    }
                }

        return MockResponse()

    monkeypatch.setattr("price_monitor.currency.requests.get", mock_get)

    rates = fetch_exchange_rates("https://example.test/rates")

    assert rates["USD/RUB"] == 97.5
    assert rates["EUR/RUB"] == 106.2


def test_fetch_exchange_rates_parses_flat_json(monkeypatch):
    """Test parsing of flat JSON with pair keys."""

    def mock_get(url, timeout, headers):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"USD/RUB": 97.5, "EUR/RUB": 106.2}

        return MockResponse()

    monkeypatch.setattr("price_monitor.currency.requests.get", mock_get)

    rates = fetch_exchange_rates("https://example.test/rates")

    assert rates["USD/RUB"] == 97.5
    assert rates["EUR/RUB"] == 106.2


def test_format_currency_alert_triggered_on_large_increase():
    alert = format_currency_alert(
        pair="USD/RUB",
        current_rate=100.0,
        previous_rate=97.0,
        threshold_pct=1.0,
    )

    assert alert is not None
    assert "USD/RUB" in alert
    assert "вырос" in alert
    assert "+3.00 RUB" in alert
    assert "97.00" in alert
    assert "100.00" in alert


def test_format_currency_alert_triggered_on_large_decrease():
    alert = format_currency_alert(
        pair="EUR/RUB",
        current_rate=102.0,
        previous_rate=108.0,
        threshold_pct=1.0,
    )

    assert alert is not None
    assert "EUR/RUB" in alert
    assert "упал" in alert
    assert "-6.00 RUB" in alert


def test_format_currency_alert_suppressed_below_threshold():
    alert = format_currency_alert(
        pair="USD/RUB",
        current_rate=97.5,
        previous_rate=97.0,
        threshold_pct=1.0,
    )

    assert alert is None


def test_format_currency_alert_returns_none_for_no_previous():
    alert = format_currency_alert(
        pair="USD/RUB",
        current_rate=97.5,
        previous_rate=None,
        threshold_pct=1.0,
    )

    assert alert is None


def test_currency_observations_round_trip(tmp_path: Path):
    """Currency observations persist and load correctly."""
    db_path = tmp_path / "price_monitor.sqlite3"
    storage.initialize_storage(db_path, settings_path=tmp_path / "settings.json", state_path=tmp_path / "state.json")

    storage.save_currency_observation(db_path, "USD/RUB", 97.5, "2026-05-03T10:00")
    storage.save_currency_observation(db_path, "USD/RUB", 98.0, "2026-05-03T11:00")
    storage.save_currency_observation(db_path, "EUR/RUB", 106.2, "2026-05-03T10:00")

    usd_obs = storage.load_currency_observations(db_path, "USD/RUB", limit=2)
    eur_obs = storage.load_currency_observations(db_path, "EUR/RUB", limit=2)

    # Most recent first
    assert len(usd_obs) == 2
    assert usd_obs[0][1] == 98.0  # newest
    assert usd_obs[1][1] == 97.5  # older

    assert len(eur_obs) == 1
    assert eur_obs[0][1] == 106.2
