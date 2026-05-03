"""Travelata HTML parser.

Extracts external reference prices from travelata.ru pages.
"""

from __future__ import annotations

from price_monitor.parsers._external import (
    ExternalPrice,
    extract_external_hotel_name,
    extract_external_min_price,
)


def parse_external_price(html: str, url: str) -> ExternalPrice:
    return ExternalPrice(
        provider="Travelata",
        hotel_name=extract_external_hotel_name(html, "Travelata"),
        price_rub=extract_external_min_price(html),
        url=url,
    )
