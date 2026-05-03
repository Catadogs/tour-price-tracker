"""Shared parser utilities and data classes."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    departure_date: str
    nights: int
    room: str
    price_rub: int
    price_usd: int | None
    booking_url: str
    hotel_option_id: str | None

    @property
    def identity(self) -> str:
        suffix = self.hotel_option_id or self.room
        return f"{self.departure_date}|{self.nights}|{suffix}"


@dataclass(frozen=True)
class ExternalPrice:
    provider: str
    hotel_name: str | None
    price_rub: int | None
    url: str


def parse_int(value: str) -> int:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"No integer value in {value!r}")
    return int(digits)


def parse_usd(value: str) -> int | None:
    match = re.search(r"(\d+)\s*USD", value)
    return int(match.group(1)) if match else None


def decode_js_string(value: str) -> str:
    return value.replace("\\/", "/").replace('\\"', '"')


def first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]
