"""Sletat.ru API client — multi-operator tour price comparison.

No auth required, pure JSON, rate-limited at 1 req/sec.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

API = "https://api.sletat.ru"
PRICES_ENDPOINT = f"{API}/history/tour/prices/min"

COUNTRY_EGYPT = 40
CITY_MOSCOW = 832
STAR_5 = 404


def fetch_min_prices(
    date_from: str,
    date_to: str,
    nights_min: int = 12,
    nights_max: int = 14,
    adults: int = 2,
    country_id: int = COUNTRY_EGYPT,
    departure_city_id: int = CITY_MOSCOW,
    star_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Fetch minimum tour prices per day from all operators on Sletat."""
    try:
        body: dict[str, Any] = {
            "checkInDateFrom": date_from,
            "checkInDateTo": date_to,
            "countryToId": country_id,
            "departureCityId": departure_city_id,
            "nightsMin": nights_min,
            "nightsMax": nights_max,
            "adults": adults,
            "hotelIds": [],
            "kidsAges": [],
            "starIds": star_ids or [STAR_5],
            "resortIds": [],
            "mealIds": [],
            "isTicketsIncluded": True,
            "sourceIds": [],
            "beachLines": [],
            "minHotelRating": 0,
        }
        resp = requests.post(
            PRICES_ENDPOINT,
            json=body,
            timeout=30,
            headers={
                "Origin": "https://sletat.ru",
                "Referer": "https://sletat.ru/",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            return {"error": str(data["error"])}
        return data["result"]
    except Exception as exc:
        logging.warning("Sletat API fetch failed: %s", exc)
        return {"error": str(exc)}


def format_sletat_comparison(
    api_result: dict[str, Any],
    date_from: str,
    date_to: str,
) -> str | None:
    """Format Sletat price comparison for Telegram (ISO dates)."""
    if "error" in api_result:
        return None

    min_price = api_result.get("minPrice", 0)
    max_price = api_result.get("maxPrice", 0)
    data = api_result.get("data", [])

    if not data:
        return None

    lines = ["Sletat.ru (все 5* отели, не только отслеживаемые)"]

    target_dates = set()
    try:
        d = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        while d <= end:
            target_dates.add(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
    except ValueError:
        pass

    found = []
    for bucket in data:
        for item in bucket:
            if item.get("date") in target_dates and item.get("price"):
                found.append(item)

    if found:
        for item in sorted(found, key=lambda x: x["date"]):
            price_str = f"{item['price']:,}".replace(",", " ")
            lines.append(
                f"  {item['date']}: {price_str} RUB ({item.get('sourceName', '?')})"
            )
    else:
        all_prices = [(item["date"], item["price"], item.get("sourceName", "?"))
                       for bucket in data for item in bucket if item.get("price")]
        if all_prices:
            for date_str, price, source in all_prices[:5]:
                price_str = f"{price:,}".replace(",", " ")
                lines.append(f"  {date_str}: {price_str} RUB ({source})")

    if min_price and max_price:
        min_str = f"{min_price:,}".replace(",", " ")
        max_str = f"{max_price:,}".replace(",", " ")
        lines.append(f"min: {min_str} — max: {max_str} RUB")

    return "\n".join(lines)
