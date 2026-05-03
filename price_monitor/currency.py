"""Currency exchange rate monitoring for tour price early warnings.

Fetches USD/RUB and EUR/RUB rates from a configurable source (default: CBR
JSON mirror), stores observations in SQLite, and generates Telegram alerts
when rates move beyond configured thresholds.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import requests

from price_monitor import storage


# Default source: unofficial CBR daily rates JSON mirror
DEFAULT_CURRENCY_SOURCE = "https://www.cbr-xml-daily.ru/daily_json.js"

# Pairs we monitor
TRACKED_PAIRS = ("USD/RUB", "EUR/RUB")


def fetch_exchange_rates(source_url: str) -> dict[str, float]:
    """Fetch exchange rates from a JSON API.

    Expected format (CBR mirror)::

        {
          "Valute": {
            "USD": {"CharCode": "USD", "Value": 97.5},
            "EUR": {"CharCode": "EUR", "Value": 106.2}
          }
        }

    Returns dict mapping pair name to rate, e.g. {"USD/RUB": 97.5, "EUR/RUB": 106.2}.

    Raises RuntimeError on HTTP or parse failure.
    """
    response = requests.get(
        source_url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 personal-bg-price-monitor",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected currency source response type: {type(data).__name__}")

    # Try CBR-style nested Valute dict
    valute = data.get("Valute")
    if isinstance(valute, dict):
        rates: dict[str, float] = {}
        for code_key in ("USD", "EUR"):
            item = valute.get(code_key)
            if isinstance(item, dict):
                value = item.get("Value")
                if isinstance(value, (int, float)):
                    rates[f"{code_key}/RUB"] = float(value)
        if "USD/RUB" in rates and "EUR/RUB" in rates:
            return rates

    # Try flat dict with pair keys
    flat_rates: dict[str, float] = {}
    for pair in TRACKED_PAIRS:
        value = data.get(pair)
        if isinstance(value, (int, float)):
            flat_rates[pair] = float(value)
    if "USD/RUB" in flat_rates and "EUR/RUB" in flat_rates:
        return flat_rates

    raise RuntimeError(
        "Could not extract USD/RUB and EUR/RUB rates from response"
    )


def format_currency_alert(
    pair: str,
    current_rate: float,
    previous_rate: float | None,
    threshold_pct: float,
) -> str | None:
    """Format a currency alert if the rate has moved beyond threshold.

    Returns None if no alert is needed.
    """
    if previous_rate is None:
        return None

    delta = current_rate - previous_rate
    pct = abs(delta) / previous_rate * 100

    if pct < threshold_pct:
        return None

    direction = "вырос" if delta > 0 else "упал"
    arrow = "📈" if delta > 0 else "📉"
    sign = "+" if delta > 0 else ""

    return (
        f"{arrow} *{pair}* {direction} на {pct:.1f}% за день "
        f"({sign}{delta:.2f} RUB)\n"
        f"  Было: {previous_rate:.2f} → Стало: {current_rate:.2f}\n"
        f"  ⚠️ Туроператор может пересчитать RUB-цены при следующем обновлении.\n"
        f"  Порог: {threshold_pct:.1f}%"
    )


def run_currency_check(
    db_path: Path,
    source_url: str,
    threshold_pct: float,
) -> str | None:
    """Fetch exchange rates, store observation, return alert message if needed.

    Returns None if no alert-worthy movement is detected.
    """
    try:
        rates = fetch_exchange_rates(source_url)
    except Exception:
        logging.exception("Currency rate fetch failed from %s", source_url)
        return None

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M")
    alerts: list[str] = []

    for pair in TRACKED_PAIRS:
        rate = rates.get(pair)
        if rate is None:
            logging.warning("Currency pair %s not found in response", pair)
            continue

        storage.save_currency_observation(db_path, pair, rate, ts)

        previous_obs = storage.load_currency_observations(db_path, pair, limit=2)
        previous_rate = previous_obs[1][1] if len(previous_obs) >= 2 else None

        alert = format_currency_alert(pair, rate, previous_rate, threshold_pct)
        if alert:
            alerts.append(alert)

    if alerts:
        logging.info(
            "Currency alert(s) triggered: %d pair(s) moved beyond %.1f%% threshold",
            len(alerts),
            threshold_pct,
        )
        return "\n\n".join(alerts)

    logging.info(
        "Currency check complete: USD/RUB=%.2f, EUR/RUB=%.2f",
        rates.get("USD/RUB", 0),
        rates.get("EUR/RUB", 0),
    )
    return None
