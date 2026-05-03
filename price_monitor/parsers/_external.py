"""Shared external provider (Level.Travel / Travelata) extraction logic."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from price_monitor.parsers import ExternalPrice, parse_int  # noqa: F401


def extract_external_hotel_name(html: str, provider: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Hotel":
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if title:
        for separator in (" - ", " – ", ", забронировать", " | "):
            if separator in title:
                return title.split(separator, 1)[0].strip()
        return title.strip()

    return provider


def extract_external_min_price(html: str) -> int | None:
    candidates: list[int] = []

    for match in re.finditer(r'"(?:minPrice|price)"\s*:\s*(\d{5,9})', html):
        candidates.append(int(match.group(1)))

    for match in re.finditer(
        r"от\s+(\d[\d\s\u00a0]*)\s*(?:руб|₽)", html, flags=re.IGNORECASE
    ):
        candidates.append(parse_int(match.group(1)))

    return min(candidates) if candidates else None
