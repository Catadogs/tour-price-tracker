"""Domain models for the price monitor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
class MonitorConfig:
    url: str
    departure_from: str
    departure_to: str
    nights: tuple[int, ...]
    room_filters: tuple[str, ...]
    interval_seconds: int
    run_once: bool
    db_path: Path
    strong_diff_rub: int
    strong_diff_percent: float
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    target_price_rub: int | None
    currency_source_url: str
    currency_alert_threshold_pct: float
    currency_check_hours: int
    price_history_retention_days: int
    chart_interval_hours: int
    anomaly_preset: str  # "conservative" | "balanced" | "aggressive"
    state_path: Path | None = None
    settings_path: Path | None = None
    history_path: Path | None = None


@dataclass(frozen=True)
class SearchTarget:
    name: str
    url: str
    room_filters: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalPrice:
    provider: str
    hotel_name: str | None
    price_rub: int | None
    url: str


@dataclass(frozen=True)
class TargetResult:
    target_name: str
    provider: str
    hotel_name: str | None
    best_by_date: dict[str, dict[int, Offer]] | None
    external_price: ExternalPrice | None


@dataclass(frozen=True)
class HotelGroup:
    hotel_name: str
    results: list[TargetResult]


ANOMALY_PRESETS: dict[str, dict[str, object]] = {
    "conservative": {"strong_diff_rub": 30000, "strong_diff_percent": 10.0},
    "balanced": {"strong_diff_rub": 20000, "strong_diff_percent": 7.0},
    "aggressive": {"strong_diff_rub": 10000, "strong_diff_percent": 4.0},
}
