"""Level.Travel HTML parser.

Extracts external reference prices from level.travel pages.
"""

from __future__ import annotations

from price_monitor.parsers._external import (
    ExternalPrice,
    extract_external_hotel_name,
    extract_external_min_price,
)


def parse_external_price(html: str, url: str) -> ExternalPrice:
    return ExternalPrice(
        provider="Level.Travel",
        hotel_name=extract_external_hotel_name(html, "Level.Travel"),
        price_rub=extract_external_min_price(html),
        url=url,
    )
