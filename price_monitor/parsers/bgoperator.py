"""Biblio-Globus HTML parser.

Extracts tour offers from bgoperator.ru price pages.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from price_monitor.parsers import (
    Offer,
    decode_js_string,
    first_query_value,
    parse_int,
    parse_usd,
)


def parse_offers(html: str) -> list[Offer]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []

    for row in soup.select("tr"):
        room_cell = row.select_one("td.c_ns")
        price_cell = row.select_one("td.c_pe b.r")
        booking_link = row.select_one("td.c_pe a[href]")

        if not room_cell or not price_cell or not booking_link:
            continue

        query = parse_qs(urlparse(booking_link["href"]).query)
        departure_date = first_query_value(query, "dt")
        nights_raw = first_query_value(query, "kol")

        if not departure_date or not nights_raw:
            continue

        price_rub = parse_int(price_cell.get_text())
        price_usd = parse_usd(booking_link.get("title", ""))

        offers.append(
            Offer(
                departure_date=departure_date,
                nights=int(nights_raw),
                room=room_cell.get_text(" ", strip=True),
                price_rub=price_rub,
                price_usd=price_usd,
                booking_url=booking_link["href"],
                hotel_option_id=first_query_value(query, "otn"),
            )
        )

    return offers


def extract_hotel_name(html: str, url: str) -> str | None:
    hotel_id = first_query_value(parse_qs(urlparse(url).query), "F4")
    if hotel_id:
        pattern = re.compile(
            rf"\[{re.escape(hotel_id)},\{{.*?\"n\":\"(?P<name>.*?)\"",
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            return decode_js_string(match.group("name"))

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    match = re.search(r"в отель\s+(.+?)\.\s", title, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None
