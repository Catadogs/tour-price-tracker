"""Sletat.ru API client — multi-operator tour price comparison.

No auth required, pure JSON, rate-limited at 1 req/sec.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

API = "https://api.sletat.ru"
PRICES_ENDPOINT = f"{API}/history/tour/prices/min"

# Internal Sletat IDs
COUNTRY_EGYPT = 40
CITY_MOSCOW = 832
STAR_5 = 404


def fetch_min_prices(
    date_from: str,       # "2026-09-14"
    date_to: str,
    nights_min: int = 12,
    nights_max: int = 14,
    adults: int = 2,
    country_id: int = COUNTRY_EGYPT,
    departure_city_id: int = CITY_MOSCOW,
    star_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Fetch minimum tour prices per day from all operators on Sletat.

    Returns:
        {
          "minPrice": 68145,
          "maxPrice": 159894,
          "data": [
            [  # bucket
              {"price": 71809, "date": "2026-08-24", "sourceId": 20, "sourceName": "ICS Travel Group"},
              ...
            ],
            ...
          ]
        }
        or {"error": "message"} on failure.
    """
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


def format_sletat_comparison(api_result: dict[str, Any], date_from: str, date_to: str) -> str | None:
    """Format Sletat price comparison for Telegram.

    date_from/to are ISO format: "2026-09-14"
    """
    if "error" in api_result:
        return None

    min_price = api_result.get("minPrice", 0)
    max_price = api_result.get("maxPrice", 0)
    data = api_result.get("data", [])

    if not data:
        return None

    lines = ["🌐 *Sletat\\.ru — все операторы*"]

    # Find prices for the user's specific dates
    target_dates = set()
    from datetime import datetime, timedelta
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
        lines.append(f"\nМин. цена на твои даты:")
        for item in sorted(found, key=lambda x: x["date"]):
            lines.append(
                f"  • {item['date']}: *{item['price']:,}* RUB "
                f"({item.get('sourceName', '?')})".replace(",", " ")
            )
    else:
        lines.append(f"\nНа {date_from} — {date_to} данные не найдены\\.")
        # Show nearest dates with prices
        all_prices = [(item["date"], item["price"], item.get("sourceName", "?"))
                       for bucket in data for item in bucket if item.get("price")]
        if all_prices:
            lines.append("Ближайшие:")
            for date_str, price, source in all_prices[:5]:
                lines.append(
                    f"  • {date_str}: *{price:,}* RUB ({source})".replace(",", " ")
                )

    if min_price and max_price:
        lines.append(
            f"\nДиапазон за месяц: *{min_price:,}* — *{max_price:,}* RUB".replace(",", " ")
        )

    return "\n".join(lines)
