from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from price_monitor import currency, storage


DEFAULT_URL = (
    "https://www.bgoperator.ru/price.shtml?action=price&tid=211&idt="
    "&flt2=100510000863&bfr=1&id_price=121110211810&data=14.09.2026"
    "&d2=26.09.2026&f7=12&f7=13&f3=5*&f8=&ho=0&F4=102632942104"
    "&ins=0-40000-USD&flt=100410000047&p=0140819900.0140819900"
)


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

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        room_filters = parse_filters(
            os.getenv("BG_ROOM_FILTERS") or os.getenv("BG_ROOM_CONTAINS") or ""
        )
        target_raw = empty_to_none(os.getenv("BG_TARGET_PRICE"))

        return cls(
            url=empty_to_none(os.getenv("BG_MONITOR_URL")) or DEFAULT_URL,
            departure_from=os.getenv("BG_DEPARTURE_FROM", "14.09.2026"),
            departure_to=os.getenv("BG_DEPARTURE_TO", "17.09.2026"),
            nights=parse_nights(os.getenv("BG_NIGHTS", "12,13,14")),
            room_filters=room_filters,
            interval_seconds=int(os.getenv("BG_CHECK_INTERVAL_SECONDS", "3600")),
            run_once=os.getenv("BG_RUN_ONCE", "0") == "1",
            db_path=Path(os.getenv("BG_DB_PATH", "/data/price_monitor.sqlite3")),
            state_path=Path(os.getenv("BG_STATE_PATH", "")) or None,
            settings_path=Path(os.getenv("BG_SETTINGS_PATH", "")) or None,
            strong_diff_rub=int(os.getenv("BG_STRONG_DIFF_RUB", "20000")),
            strong_diff_percent=float(os.getenv("BG_STRONG_DIFF_PERCENT", "7")),
            telegram_bot_token=empty_to_none(os.getenv("TELEGRAM_BOT_TOKEN")),
            telegram_chat_id=empty_to_none(os.getenv("TELEGRAM_CHAT_ID")),
            target_price_rub=int(target_raw) if target_raw else None,
            history_path=Path(os.getenv("BG_HISTORY_PATH", "")) or None,
            currency_source_url=os.getenv(
                "BG_CURRENCY_SOURCE_URL",
                "https://www.cbr-xml-daily.ru/daily_json.js",
            ),
            currency_alert_threshold_pct=float(
                os.getenv("BG_CURRENCY_ALERT_THRESHOLD_PCT", "1.0")
            ),
            currency_check_hours=int(os.getenv("BG_CURRENCY_CHECK_HOURS", "24")),
            price_history_retention_days=int(os.getenv("BG_PRICE_HISTORY_RETENTION_DAYS", "90")),
            chart_interval_hours=int(os.getenv("BG_CHART_INTERVAL_HOURS", "0")),
            anomaly_preset=os.getenv("BG_ANOMALY_PRESET", "balanced"),
        )


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


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_nights(value: str) -> tuple[int, ...]:
    nights = tuple(sorted({int(part.strip()) for part in value.split(",") if part.strip()}))
    if not nights:
        raise ValueError("BG_NIGHTS must contain at least one number")
    return nights


def parse_filters(value: str) -> tuple[str, ...]:
    parts = re.split(r"[;,]", value)
    filters = []
    for part in parts:
        cleaned = part.strip()
        if cleaned and cleaned.lower() not in {item.lower() for item in filters}:
            filters.append(cleaned)
    return tuple(filters)


def parse_ru_date(value: str) -> datetime:
    return datetime.strptime(value, "%d.%m.%Y")


def date_in_range(value: str, start: str, end: str) -> bool:
    parsed = parse_ru_date(value)
    return parse_ru_date(start) <= parsed <= parse_ru_date(end)


def parse_offers(html: str) -> list[Offer]:
    from price_monitor.parsers import bgoperator
    return bgoperator.parse_offers(html)


def first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]


def parse_int(value: str) -> int:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"No integer value in {value!r}")
    return int(digits)


def parse_usd(value: str) -> int | None:
    match = re.search(r"(\d+)\s*USD", value)
    return int(match.group(1)) if match else None


def initialize_storage(config: MonitorConfig) -> None:
    storage.initialize_storage(
        config.db_path,
        settings_path=config.settings_path,
        state_path=config.state_path,
        history_path=config.history_path,
    )


def load_runtime_settings(config: MonitorConfig) -> dict[str, object]:
    return storage.load_runtime_settings(config.db_path)


def save_runtime_settings(config: MonitorConfig, settings: dict[str, object]) -> None:
    storage.save_runtime_settings(config.db_path, settings)


def effective_config(config: MonitorConfig) -> MonitorConfig:
    settings = load_runtime_settings(config)
    updates: dict[str, object] = {}

    for key in ("departure_from", "departure_to"):
        if key in settings:
            updates[key] = settings[key]

    if "nights" in settings:
        _apply_runtime_setting(updates, "nights", settings["nights"], _settings_nights)
    if "room_filters" in settings:
        _apply_runtime_setting(
            updates,
            "room_filters",
            settings["room_filters"],
            _settings_room_filters,
        )
    if "target_price_rub" in settings:
        _apply_runtime_setting(
            updates,
            "target_price_rub",
            settings["target_price_rub"],
            _settings_optional_int,
        )
    if "strong_diff_rub" in settings:
        _apply_runtime_setting(updates, "strong_diff_rub", settings["strong_diff_rub"], int)
    if "strong_diff_percent" in settings:
        _apply_runtime_setting(
            updates,
            "strong_diff_percent",
            settings["strong_diff_percent"],
            float,
        )
    if "interval_seconds" in settings:
        _apply_runtime_setting(
            updates,
            "interval_seconds",
            settings["interval_seconds"],
            int,
        )
    if "anomaly_preset" in settings:
        preset_name = str(settings["anomaly_preset"])
        preset = ANOMALY_PRESETS.get(preset_name)
        if preset:
            updates["anomaly_preset"] = preset_name
            updates["strong_diff_rub"] = int(preset["strong_diff_rub"])
            updates["strong_diff_percent"] = float(preset["strong_diff_percent"])
    if "price_history_retention_days" in settings:
        _apply_runtime_setting(
            updates,
            "price_history_retention_days",
            settings["price_history_retention_days"],
            int,
        )

    config = replace(config, **updates)

    # Enforce max 3 departure days
    try:
        start = parse_ru_date(config.departure_from)
        end = parse_ru_date(config.departure_to)
        if (end - start).days > 2:
            clamped = (start + (end - start).__class__(days=2)).strftime("%d.%m.%Y")
            logging.warning(
                "Departure range clamped from %s to %s (max 3 days)",
                config.departure_to,
                clamped,
            )
            config = replace(config, departure_to=clamped)
    except ValueError:
        pass

    return config


def _apply_runtime_setting(
    updates: dict[str, object],
    key: str,
    value: object,
    convert,
) -> None:
    try:
        updates[key] = convert(value)
    except (TypeError, ValueError):
        logging.warning("Ignoring invalid runtime setting %s=%r", key, value)


def _settings_nights(value: object) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("nights must be a sequence of integers")
    nights = tuple(int(item) for item in value)  # type: ignore[union-attr]
    if not nights:
        raise ValueError("nights must not be empty")
    return nights


def _settings_room_filters(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        return parse_filters(str(value))
    return tuple(str(item) for item in value)  # type: ignore[union-attr]


def _settings_optional_int(value: object) -> int | None:
    return int(value) if value is not None else None


def load_search_targets(config: MonitorConfig) -> list[SearchTarget]:
    settings = load_runtime_settings(config)
    targets = [SearchTarget(name="Основной поиск", url=config.url, room_filters=config.room_filters)]

    raw_searches = settings.get("searches", [])
    if not isinstance(raw_searches, list):
        return targets

    for index, item in enumerate(raw_searches, start=2):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        name = str(item.get("name") or f"Поиск {index}").strip()
        raw_filters = item.get("room_filters", [])
        if not isinstance(raw_filters, list):
            continue
        filters = tuple(str(value) for value in raw_filters)
        targets.append(SearchTarget(name=name, url=url, room_filters=filters))

    return targets


def filter_offers(offers: Iterable[Offer], config: MonitorConfig) -> list[Offer]:
    filtered: list[Offer] = []
    room_filters = tuple(item.lower() for item in config.room_filters)

    for offer in offers:
        if offer.nights not in config.nights:
            continue
        if not date_in_range(offer.departure_date, config.departure_from, config.departure_to):
            continue
        if room_filters and not any(item in offer.room.lower() for item in room_filters):
            continue
        filtered.append(offer)

    return filtered


def best_by_departure_and_nights(offers: Iterable[Offer]) -> dict[str, dict[int, Offer]]:
    best: dict[str, dict[int, Offer]] = {}

    for offer in offers:
        by_nights = best.setdefault(offer.departure_date, {})
        current = by_nights.get(offer.nights)
        if current is None or offer.price_rub < current.price_rub:
            by_nights[offer.nights] = offer

    return dict(sorted(best.items(), key=lambda kv: parse_ru_date(kv[0])))


def find_overall_best(best: dict[str, dict[int, Offer]]) -> Offer | None:
    offers = [offer for by_nights in best.values() for offer in by_nights.values()]
    if not offers:
        return None
    return min(offers, key=lambda offer: offer.price_rub)


def format_report(
    best: dict[str, dict[int, Offer]],
    config: MonitorConfig,
    target_name: str = "Main search",
    hotel_name: str | None = None,
) -> str:
    lines = [
        f"🏨 *{target_name}*",
        f"🏩 Отель: `{hotel_name}`" if hotel_name else None,
        f"📅 Вылет: `{config.departure_from} - {config.departure_to}`",
        f"🌙 Ночей: `{', '.join(str(item) for item in config.nights)}`",
    ]
    lines = [line for line in lines if line is not None]

    if config.room_filters:
        lines.append("🔎 Фильтры: `" + "; ".join(config.room_filters) + "`")

    overall = find_overall_best(best)
    if overall:
        lines.extend(
            [
                "",
                f"✅ *Лучшая*: `{overall.departure_date}`, `{overall.nights}`н — *{format_price(overall)}* [Посмотреть]({overall.booking_url})",
            ]
        )
    else:
        lines.append("")
        lines.append("⚠️ Подходящие предложения не найдены.")
        return "\n".join(lines)

    lines.extend(["", "📊 *По датам вылета*"])
    last_best: int | None = None
    dates = list(best.items())
    for departure_date, by_nights in dates:
        # Get best price for this date
        date_best = min(o.price_rub for o in by_nights.values())
        # Skip if within 10% of previous date
        if last_best is not None and abs(date_best - last_best) / last_best * 100 < 10:
            continue
        last_best = date_best

        night_lines: list[str] = []
        for nights in config.nights:
            offer = by_nights.get(nights)
            if offer:
                night_lines.append(f"• `{nights}`н: `{format_price(offer)}` [Смотреть]({offer.booking_url})")
        if night_lines:
            lines.append(f"\n*{departure_date}*")
            lines.extend(night_lines)

    anomalies = format_duration_anomalies(best, config)
    if anomalies:
        lines.extend(["", "⚠️ *Аномалии длительности*", anomalies])

    return "\n".join(lines)


def format_external_report(target_name: str, price: ExternalPrice) -> str:
    lines = [
        f"🌐 *{target_name}*",
        f"Сайт: *{price.provider}*",
    ]
    if price.hotel_name:
        lines.append(f"🏩 Отель: `{price.hotel_name}`")
    if price.price_rub:
        lines.append(f"💰 Цена на сайте: *от {format_rub(price.price_rub)}*")
    else:
        lines.append("⚠️ Цена на странице не найдена.")
    lines.append("ℹ️ Это справочная цена со страницы сайта, не точное сравнение по датам/ночам Библио-Глобуса.")
    return "\n".join(lines)


def format_price(offer: Offer) -> str:
    suffix = f" / {offer.price_usd} USD" if offer.price_usd else ""
    return f"{format_rub(offer.price_rub)}{suffix}"


def format_rub(value: int) -> str:
    return f"{value:,} RUB".replace(",", " ")


def format_duration_anomalies(
    best: dict[str, dict[int, Offer]],
    config: MonitorConfig,
) -> str | None:
    """Detect cases where a longer duration is cheaper than a shorter one on the same date."""
    lines: list[str] = []
    for date, by_nights in best.items():
        sorted_nights = sorted(by_nights.keys())
        for i, shorter in enumerate(sorted_nights):
            for longer in sorted_nights[i + 1:]:
                offer_s = by_nights[shorter]
                offer_l = by_nights[longer]
                if offer_l.price_rub >= offer_s.price_rub:
                    continue
                diff = offer_s.price_rub - offer_l.price_rub
                pct = (diff / offer_s.price_rub) * 100
                if diff < config.strong_diff_rub and pct < config.strong_diff_percent:
                    continue
                lines.append(
                    f"⚠️ {date}: {longer}н дешевле {shorter}н "
                    f"на {diff:,} RUB ({pct:.1f}%)"
                )
    return "\n".join(lines).replace(",", " ") if lines else None


def format_strong_diff_line(
    departure_date: str,
    by_nights: dict[int, Offer],
    config: MonitorConfig,
) -> str | None:
    if 12 not in by_nights or 13 not in by_nights:
        return None

    offer_12 = by_nights[12]
    offer_13 = by_nights[13]
    diff = offer_13.price_rub - offer_12.price_rub
    diff_abs = abs(diff)
    base = min(offer_12.price_rub, offer_13.price_rub)
    percent = (diff_abs / base) * 100 if base else 0

    if diff_abs < config.strong_diff_rub and percent < config.strong_diff_percent:
        return None

    cheaper = "13 ночей" if diff < 0 else "12 ночей"
    return (
        f"  Сильная разница 12/13 ночей на {departure_date}: "
        f"{diff_abs:,} RUB ({percent:.1f}%), дешевле: {cheaper}"
    ).replace(",", " ")


def format_trend_report(db_path: Path, config: MonitorConfig | None = None) -> str:
    """Format compact trend summary from price history.

    Only shows dates within configured departure range.
    Adjacent dates (±1 day) are shown only if price differs >10% from in-range dates.
    """
    grouped = storage.load_price_history_grouped(db_path)
    if not grouped:
        return "📊 *Тренды цен*\n\nНет данных для анализа. Нужно несколько проверок."

    # Determine allowed dates: configured range + optional ±1 day
    allowed_dates: set[str] = set()
    adjacent_dates: set[str] = set()
    if config:
        from datetime import timedelta
        start = parse_ru_date(config.departure_from)
        end = parse_ru_date(config.departure_to)
        d = start
        while d <= end:
            allowed_dates.add(d.strftime("%d.%m.%Y"))
            d += timedelta(days=1)
        # Adjacent dates ±1
        prev_day = (start - timedelta(days=1)).strftime("%d.%m.%Y")
        next_day = (end + timedelta(days=1)).strftime("%d.%m.%Y")
        adjacent_dates = {prev_day, next_day} - allowed_dates

    lines: list[str] = ["📊 *Тренды цен*\n"]
    for target_name, by_date in grouped.items():
        lines.append(f"🏨 *{target_name}*")
        shown = 0
        for date, by_nights in sorted(by_date.items(), key=lambda kv: _safe_parse_date(kv[0])):
            if config:
                if date not in allowed_dates and date not in adjacent_dates:
                    continue

            for nights, price_points in by_nights.items():
                if len(price_points) < 2:
                    continue
                prices = [p[1] for p in price_points[-6:]]
                delta = prices[-1] - prices[0]
                pct = abs(delta) / prices[0] * 100 if prices[0] else 0

                # For adjacent dates, skip if change < 10%
                if config and date in adjacent_dates and pct < 10:
                    continue

                if delta < 0:
                    direction = f"↓ -{pct:.0f}%"
                elif delta > 0:
                    direction = f"↑ +{pct:.0f}%"
                else:
                    direction = "→ 0%"
                current = prices[-1]
                date_label = f"🟡 {date}" if date in adjacent_dates else date
                lines.append(
                    f"  {date_label}, {nights}н: *{format_rub(current)}* {direction}"
                )
                shown += 1
        if shown == 0:
            lines.append("  _нет данных_")
        lines.append("")
    return "\n".join(lines)


def _safe_parse_date(value: str) -> datetime:
    """Parse date or return epoch for invalid dates (used for sorting)."""
    try:
        return parse_ru_date(value)
    except ValueError:
        return datetime(1970, 1, 1)


def snapshot(
    best: dict[str, dict[int, Offer]],
    target_name: str = "Main search",
) -> dict[str, dict[str, object]]:
    return {
        f"{target_name}|{offer.identity}": asdict(offer)
        for by_nights in best.values()
        for offer in by_nights.values()
    }


def load_snapshot(config: MonitorConfig) -> dict[str, dict[str, object]]:
    return storage.load_snapshot(config.db_path)


def save_snapshot(config: MonitorConfig, data: dict[str, dict[str, object]]) -> None:
    storage.save_snapshot(config.db_path, data)


def load_price_history(config: MonitorConfig) -> dict[str, list[list]]:
    return storage.load_price_history(config.db_path)


def save_price_history(path: Path, history: dict[str, list[list]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def update_price_history(
    history: dict[str, list[list]],
    current_snapshot: dict[str, dict[str, object]],
    ts: str,
) -> None:
    for key, item in current_snapshot.items():
        price = item.get("price_rub")
        if price is None:
            continue
        history.setdefault(key, []).append([ts, int(price)])  # type: ignore[arg-type]


def append_price_history(
    config: MonitorConfig,
    current_snapshot: dict[str, dict[str, object]],
    ts: str,
) -> None:
    storage.append_price_history(config.db_path, current_snapshot, ts)


def historical_min_price(history: dict[str, list[list]], key: str) -> int | None:
    entries = history.get(key)
    if not entries:
        return None
    return min(int(e[1]) for e in entries)


def compute_trend(history: dict[str, list[list]], key: str, window: int = 6) -> str:
    prices = [int(e[1]) for e in history.get(key, [])[-window:]]
    if len(prices) < 2:
        return ""
    delta = prices[-1] - prices[0]
    pct = abs(delta) / prices[0] * 100
    if pct < 1:
        return "→ стабильно"
    return f"↓ падает ({pct:.1f}%)" if delta < 0 else f"↑ растёт ({pct:.1f}%)"


def format_new_minimums(
    current_snapshot: dict[str, dict[str, object]],
    history: dict[str, list[list]],
) -> tuple[str | None, set[str]]:
    """Detect new historical minimum prices.

    Returns (formatted_block, set_of_affected_keys).
    The key set is used to avoid duplicate reporting in format_changes.
    """
    lines: list[str] = []
    affected_keys: set[str] = set()
    for key, item in current_snapshot.items():
        prev_min = historical_min_price(history, key)
        if prev_min is None:
            continue
        current_price = int(item["price_rub"])
        if current_price < prev_min:
            affected_keys.add(key)
            booking_url = str(item.get("booking_url") or "")
            link = f" [Посмотреть]({booking_url})" if booking_url else ""
            target_name = key.split("|", 1)[0]
            trend = compute_trend(history, key)
            trend_str = f", {trend}" if trend else ""
            lines.append(
                f"🏆 `{target_name}`: `{item['departure_date']}`, "
                f"`{item['nights']}` ночей — *{format_rub(current_price)}*"
                f"{trend_str}{link}"
            )
    return ("\n".join(lines) if lines else None, affected_keys)


def format_target_alerts(
    current_snapshot: dict[str, dict[str, object]],
    target_price_rub: int,
) -> str | None:
    lines: list[str] = []
    for item in current_snapshot.values():
        price = int(item["price_rub"])
        if price <= target_price_rub:
            booking_url = str(item.get("booking_url") or "")
            link = f" [Посмотреть]({booking_url})" if booking_url else ""
            lines.append(
                f"🎯 Цена достигла цели {format_rub(target_price_rub)}: "
                f"`{item['departure_date']}`, `{item['nights']}` ночей — "
                f"*{format_rub(price)}*{link}"
            )
    return "\n".join(lines) if lines else None


def adaptive_interval(departure_from: str, base_interval: int) -> int:
    try:
        days_left = (parse_ru_date(departure_from) - datetime.now()).days
    except ValueError:
        return base_interval
    if days_left < 14:
        return min(base_interval, 900)
    if days_left < 30:
        return min(base_interval, 3600)
    if days_left < 60:
        return min(base_interval, 21600)
    return base_interval


def format_changes(
    previous: dict[str, dict[str, object]],
    current: dict[str, dict[str, object]],
    skip_keys: set[str] | None = None,
) -> str | None:
    if not previous:
        return None

    skip = skip_keys or set()
    lines: list[str] = []

    for identity, item in current.items():
        if identity in skip:
            continue  # Already reported as historical minimum
        old = previous.get(identity)
        if old is None:
            lines.append(
                "🆕 Новое предложение: "
                f"`{item['departure_date']}`, `{item['nights']}` ночей, "
                f"`{item['price_rub']} RUB`"
            )
            continue

        old_price = int(old["price_rub"])
        new_price = int(item["price_rub"])
        if old_price != new_price:
            fell = new_price < old_price
            marker = "📉" if fell else "📈"
            direction = "упала" if fell else "выросла"
            booking_url = str(item.get("booking_url") or "")
            link = f" [Посмотреть]({booking_url})" if booking_url and fell else ""
            diff = old_price - new_price if fell else new_price - old_price
            sign = "-" if fell else "+"
            lines.append(
                f"{marker} {item['departure_date']}, {item['nights']}н: "
                f"*{format_rub(new_price)}* ({sign}{format_rub(diff)}){link}"
            )

    return "\n".join(lines) if lines else None


def format_new_arrivals(
    previous: dict[str, dict[str, object]],
    current: dict[str, dict[str, object]],
) -> tuple[str | None, str | None]:
    """Detect new departure dates and new hotel/room combos vs previous snapshot.

    Returns (new_dates_block, new_hotels_block) — each str or None.
    """
    if not previous:
        return None, None

    # --- New dates ---
    prev_dates: set[str] = set()
    cur_dates: set[str] = set()

    for item in previous.values():
        d = str(item.get("departure_date", ""))
        if d and d != "external":
            prev_dates.add(d)
    for item in current.values():
        d = str(item.get("departure_date", ""))
        if d and d != "external":
            cur_dates.add(d)

    new_dates = cur_dates - prev_dates

    date_lines: list[str] = []
    if new_dates:
        date_lines = ["📅 *Новые даты вылета*"]
        for date in sorted(new_dates, key=parse_ru_date):
            best_price = None
            for item in current.values():
                if str(item.get("departure_date")) == date:
                    p = int(item["price_rub"])
                    if best_price is None or p < best_price:
                        best_price = p
            price_str = format_rub(best_price) if best_price else "?"
            date_lines.append(f"  • {date}: от *{price_str}*")

    # --- New hotels/rooms on existing dates ---
    prev_ids: dict[str, set[str]] = {}
    cur_ids: dict[str, set[str]] = {}

    for key, item in previous.items():
        d = str(item.get("departure_date", ""))
        if d and d != "external":
            prev_ids.setdefault(d, set()).add(key)
    for key, item in current.items():
        d = str(item.get("departure_date", ""))
        if d and d != "external":
            cur_ids.setdefault(d, set()).add(key)

    room_lines: list[str] = []
    for date in sorted(cur_ids, key=parse_ru_date):
        if date in new_dates:
            continue  # Entirely new dates are already reported above
        prev_set = prev_ids.get(date, set())
        new_keys = cur_ids[date] - prev_set
        if new_keys:
            if not room_lines:
                room_lines = ["🏩 *Новые отели/номера*"]
            for key in sorted(new_keys):
                item = current.get(key)
                if item:
                    nights = item.get("nights", "?")
                    price = int(item["price_rub"])
                    room = item.get("room", "")
                    room_lines.append(
                        f"  • {date}, {nights}н: {room} — *{format_rub(price)}*"
                    )

    return (
        "\n".join(date_lines) if date_lines else None,
        "\n".join(room_lines) if room_lines else None,
    )


def fetch_html(url: str) -> str:
    from price_monitor.parsers._fetch import fetch_with_retry
    provider = provider_from_url(url).lower().replace(".", "").replace(" ", "-")
    return fetch_with_retry(url, provider)


def extract_hotel_name(html: str, url: str) -> str | None:
    from price_monitor.parsers import bgoperator
    return bgoperator.extract_hotel_name(html, url)


def parse_external_price(html: str, url: str) -> ExternalPrice:
    provider = provider_from_url(url)
    if "level.travel" in provider.lower():
        from price_monitor.parsers import leveltravel
        return leveltravel.parse_external_price(html, url)
    from price_monitor.parsers import travelata
    return travelata.parse_external_price(html, url)


def provider_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "level.travel" in host:
        return "Level.Travel"
    if "travelata.ru" in host:
        return "Travelata"
    if "bgoperator.ru" in host:
        return "Библио-Глобус"
    return host


def is_bgoperator_url(url: str) -> bool:
    return "bgoperator.ru" in urlparse(url).netloc.lower()


def extract_external_hotel_name(html: str, provider: str) -> str | None:
    from price_monitor.parsers._external import extract_external_hotel_name as _extract
    return _extract(html, provider)


def extract_external_min_price(html: str) -> int | None:
    from price_monitor.parsers._external import extract_external_min_price as _extract
    return _extract(html)


def decode_js_string(value: str) -> str:
    return value.replace("\\/", "/").replace('\\"', '"')


def send_telegram(config: MonitorConfig, text: str, chat_id: str | None = None) -> None:
    if not config.telegram_bot_token:
        return

    target_chat_id = chat_id or config.telegram_chat_id
    if not target_chat_id:
        return

    for chunk in split_telegram_text(text):
        telegram_post(
            config.telegram_bot_token,
            "sendMessage",
            {
                "chat_id": target_chat_id,
                "text": escape_markdown_v2(chunk),
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            },
        )


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    chunks.append(remaining)
    return chunks


_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_MD_SPECIAL = set(r"_[]()~`>#+-=|{}.!")


def _escape_plain(text: str) -> str:
    result: list[str] = []
    in_code = False
    for char in text:
        if char == "`":
            in_code = not in_code
            result.append(char)
            continue
        if in_code:
            if char in {"\\", "`"}:
                result.append("\\" + char)
            else:
                result.append(char)
            continue
        if char in _MD_SPECIAL:
            result.append("\\" + char)
        else:
            result.append(char)
    return "".join(result)


def escape_markdown_v2(text: str) -> str:
    parts: list[str] = []
    last = 0
    for m in _MD_LINK_RE.finditer(text):
        parts.append(_escape_plain(text[last:m.start()]))
        display = _escape_plain(m.group(1))
        parts.append(f"[{display}]({m.group(2)})")
        last = m.end()
    parts.append(_escape_plain(text[last:]))
    return "".join(parts)


def telegram_post(
    token: str,
    method: str,
    payload: dict[str, object],
    timeout: int = 20,
    max_retries: int = 3,
) -> dict[str, object]:
    max_retries_count = max(max_retries, 0)
    url = f"https://api.telegram.org/bot{token}/{method}"
    for attempt in range(max_retries_count + 1):
        try:
            response = requests.post(url, timeout=timeout, json=payload)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt >= max_retries_count:
                raise RuntimeError(
                    f"Telegram API {method} failed after {max_retries_count + 1} attempts: {exc}"
                ) from exc
            logging.warning(
                "Telegram %s attempt %d/%d: %s, retrying in %ds",
                method, attempt + 1, max_retries_count + 1, exc, 2 ** attempt,
            )
            time.sleep(2 ** attempt)
            continue
        if response.status_code >= 500 and attempt < max_retries_count:
            logging.warning(
                "Telegram %s attempt %d/%d: HTTP %d, retrying in %ds",
                method, attempt + 1, max_retries_count + 1,
                response.status_code, 2 ** attempt,
            )
            time.sleep(2 ** attempt)
            continue
        if response.status_code >= 400:
            raise RuntimeError(
                f"Telegram API {method} failed: HTTP {response.status_code}, "
                f"body={response.text}"
            )
        return response.json()

    raise RuntimeError(f"Telegram API {method} failed after all retries")


def run_check(config: MonitorConfig) -> str:
    active_config = effective_config(config)
    reports: list[str] = []
    current_snapshot: dict[str, dict[str, object]] = {}
    target_results: list[TargetResult] = []

    for target in load_search_targets(active_config):
        # Rewrite date parameters in Biblio-Globus URLs to match current config
        fetch_url = target.url
        if is_bgoperator_url(target.url):
            fetch_url = re.sub(
                r"data=[^&]*", f"data={active_config.departure_from}", fetch_url
            )
            fetch_url = re.sub(
                r"d2=[^&]*", f"d2={active_config.departure_to}", fetch_url
            )

        html = fetch_html(fetch_url)

        if is_bgoperator_url(target.url):
            target_filters = target.room_filters or active_config.room_filters
            target_config = replace(
                active_config,
                url=target.url,
                room_filters=target_filters,
            )
            hotel_name = extract_hotel_name(html, target_config.url)
            offers = filter_offers(parse_offers(html), target_config)
            best = best_by_departure_and_nights(offers)
            reports.append(format_report(best, target_config, target.name, hotel_name))
            current_snapshot.update(snapshot(best, target.name))
            target_results.append(TargetResult(
                target_name=target.name,
                provider="Библио-Глобус",
                hotel_name=hotel_name,
                best_by_date=best,
                external_price=None,
            ))
            continue

        external_price = parse_external_price(html, target.url)
        reports.append(format_external_report(target.name, external_price))
        if external_price.price_rub:
            current_snapshot[f"{target.name}|external"] = {
                "departure_date": "external",
                "nights": 0,
                "price_rub": external_price.price_rub,
                "hotel": external_price.hotel_name or target.name,
            }
        target_results.append(TargetResult(
            target_name=target.name,
            provider=external_price.provider,
            hotel_name=external_price.hotel_name,
            best_by_date=None,
            external_price=external_price,
        ))

    previous_snapshot = load_snapshot(active_config)
    history = load_price_history(active_config)

    minimums, minimum_keys = format_new_minimums(current_snapshot, history)

    changes = format_changes(previous_snapshot, current_snapshot, minimum_keys)
    # Suppress notification when all changes are new offers (first run after empty snapshot)
    if changes and all(line.startswith("🆕") for line in changes.splitlines()):
        changes = None

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M")
    append_price_history(active_config, current_snapshot, ts)
    save_snapshot(active_config, current_snapshot)

    target_alerts = (
        format_target_alerts(current_snapshot, active_config.target_price_rub)
        if active_config.target_price_rub
        else None
    )

    new_dates_block, new_hotels_block = format_new_arrivals(previous_snapshot, current_snapshot)

    report = "\n\n".join(reports)

    # Cross-provider comparison
    groups = match_hotels_across_providers(target_results)
    comparison = format_comparison(groups)
    if comparison:
        report = f"{report}\n\n{comparison}"

    # Cross-search comparison (different BG hotels)
    cross = format_cross_search_comparison(target_results)
    if cross:
        report = f"{report}\n\n{cross}"

    alerts: list[str] = []
    if minimums:
        alerts.append(f"🏆 *Исторические минимумы*\n{minimums}")
    if target_alerts:
        alerts.append(f"🎯 *Цель достигнута*\n{target_alerts}")
    if new_dates_block:
        alerts.append(new_dates_block)
    if new_hotels_block:
        alerts.append(new_hotels_block)
    if changes:
        alerts.append(f"🔔 *Изменения с прошлой проверки*\n{changes}")

    message = report if not alerts else f"{report}\n\n" + "\n\n".join(alerts)
    logging.info("Price check finished: %s search(es), %s offer(s)", len(reports), len(current_snapshot))
    return message


class TelegramControlBot:
    def __init__(self, config: MonitorConfig, check_lock: threading.Lock) -> None:
        self.config = config
        self.check_lock = check_lock
        self.offset = 0
        self.pending: dict[int, str] = {}

    def start(self) -> None:
        if not self.config.telegram_bot_token:
            logging.info("Telegram bot is disabled: TELEGRAM_BOT_TOKEN is empty")
            return

        thread = threading.Thread(target=self.poll_forever, name="telegram-bot", daemon=True)
        thread.start()
        logging.info("Telegram bot polling started")

    def poll_forever(self) -> None:
        while True:
            try:
                updates = self.api(
                    "getUpdates",
                    {
                        "offset": self.offset,
                        "timeout": 30,
                        "allowed_updates": ["message", "callback_query"],
                    },
                    timeout=35,
                ).get("result", [])

                for update in updates:
                    self.offset = max(self.offset, int(update["update_id"]) + 1)
                    self.handle_update(update)
            except Exception:
                logging.exception("Telegram polling error, retrying in 5s")
                time.sleep(5)

    def api(self, method: str, payload: dict[str, object], timeout: int = 20) -> dict[str, object]:
        if not self.config.telegram_bot_token:
            raise RuntimeError("Telegram bot token is empty")
        return telegram_post(self.config.telegram_bot_token, method, payload, timeout)

    def handle_update(self, update: dict[str, object]) -> None:
        if "callback_query" in update:
            self.handle_callback(update["callback_query"])  # type: ignore[arg-type]
            return

        message = update.get("message")
        if isinstance(message, dict):
            self.handle_message(message)

    def handle_message(self, message: dict[str, object]) -> None:
        chat = message.get("chat")
        if not isinstance(chat, dict):
            return
        chat_id = int(chat["id"])
        if not self.is_authorized(chat_id):
            self.send_message(chat_id, f"Chat id {chat_id} is not allowed.")
            return

        text = str(message.get("text") or "").strip()
        if not text:
            return

        pending_action = self.pending.pop(chat_id, None)
        if pending_action:
            self.apply_pending_action(chat_id, pending_action, text)
            return

        if text.startswith("/start") or text.startswith("/help"):
            self.send_menu(chat_id)
        elif text.startswith("/check"):
            self.run_manual_check(chat_id)
        elif text.startswith("/status"):
            self.send_message(chat_id, format_settings(effective_config(self.config)), reply_markup=main_keyboard())
        elif text.startswith("/trend"):
            report = format_trend_report(self.config.db_path, effective_config(self.config))
            self.send_message(chat_id, report, reply_markup=main_keyboard())
        else:
            self.send_message(chat_id, "Используй кнопки или команду /help.", reply_markup=main_keyboard())

    def handle_callback(self, callback: dict[str, object]) -> None:
        callback_id = str(callback["id"])
        message = callback.get("message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat")
        if not isinstance(chat, dict):
            return
        chat_id = int(chat["id"])
        data = str(callback.get("data") or "")

        self.api("answerCallbackQuery", {"callback_query_id": callback_id})

        if not self.is_authorized(chat_id):
            self.send_message(chat_id, f"Chat id {chat_id} is not allowed.")
            return

        if data == "check":
            self.run_manual_check(chat_id)
        elif data == "trend":
            report = format_trend_report(self.config.db_path, effective_config(self.config))
            self.send_message(chat_id, report, reply_markup=main_keyboard())
        elif data == "weekly":
            report = format_weekly_change(self.config.db_path, effective_config(self.config))
            self.send_message(chat_id, report, reply_markup=main_keyboard())
        elif data == "recommend":
            active = effective_config(self.config)
            rec = _generate_recommendation_from_db(active)
            self.send_message(chat_id, rec, reply_markup=main_keyboard())
        elif data == "settings":
            self.send_message(chat_id, format_settings(effective_config(self.config)), reply_markup=settings_keyboard())
        elif data == "add_filter":
            self.pending[chat_id] = "add_filter"
            self.send_message(chat_id, "Отправь фрагмент названия номера или отеля для фильтра.")
        elif data == "add_search":
            self.pending[chat_id] = "add_search"
            self.send_message(
                chat_id,
                "Отправь ссылку на Библио-Глобус, Level.Travel или Travelata.\n"
                "Для точного сравнения лучше отправлять не главную страницу, а страницу конкретного отеля/поиска.",
            )
        elif data == "clear_searches":
            settings = load_runtime_settings(self.config)
            settings["searches"] = []
            save_runtime_settings(self.config, settings)
            self.send_message(chat_id, "Дополнительные поиски очищены.", reply_markup=main_keyboard())
        elif data == "clear_filters":
            settings = load_runtime_settings(self.config)
            settings["room_filters"] = []
            save_runtime_settings(self.config, settings)
            self.send_message(chat_id, "Фильтры очищены.", reply_markup=main_keyboard())
        elif data == "set_dates":
            self.pending[chat_id] = "set_dates"
            self.send_message(chat_id, "Отправь диапазон дат, например: 14.09.2026 17.09.2026")
        elif data == "set_diff":
            self.pending[chat_id] = "set_diff"
            self.send_message(
                chat_id,
                "Это порог для сравнения 12 и 13 ночей.\n"
                "Бот отметит дату, если разница >= сумме в RUB или >= проценту.\n"
                "Отправь, например: 10000 4.5",
            )
        elif data == "set_interval":
            self.pending[chat_id] = "set_interval"
            self.send_message(
                chat_id,
                "Отправь частоту проверки: 30m, 1h, 6h или число секунд.",
            )
        elif data == "set_nights":
            self.pending[chat_id] = "set_nights"
            self.send_message(chat_id, "Отправь список ночей, например: 12,13")
        elif data == "set_target":
            self.pending[chat_id] = "set_target"
            self.send_message(chat_id, "Отправь целевую цену в RUB, например: 160000\nБот пришлёт алерт когда цена будет ≤ этой суммы.")
        elif data == "set_retention":
            self.pending[chat_id] = "set_retention"
            self.send_message(chat_id, "Отправь срок хранения истории цен в днях (например: 90).")
        elif data == "set_reference":
            self.pending[chat_id] = "set_reference"
            self.send_message(chat_id, "Отправь референсную цену в RUB (например: 250000).\nЭто твоя оценка — сколько должен стоить тур.")
        elif data == "clear_target":
            settings = load_runtime_settings(self.config)
            settings["target_price_rub"] = None
            save_runtime_settings(self.config, settings)
            self.send_message(chat_id, "Целевая цена сброшена.", reply_markup=main_keyboard())
        elif data == "anomaly_preset":
            settings = load_runtime_settings(self.config)
            current = str(settings.get("anomaly_preset", "balanced"))
            presets = list(ANOMALY_PRESETS.keys())
            next_idx = (presets.index(current) + 1) % len(presets)
            next_preset = presets[next_idx]
            settings["anomaly_preset"] = next_preset
            preset_data = ANOMALY_PRESETS[next_preset]
            settings["strong_diff_rub"] = int(preset_data["strong_diff_rub"])
            settings["strong_diff_percent"] = float(preset_data["strong_diff_percent"])
            save_runtime_settings(self.config, settings)
            labels = {"conservative": "консервативный", "balanced": "сбалансированный", "aggressive": "агрессивный"}
            self.send_message(
                chat_id,
                f"Пресет аномалий: *{labels[next_preset]}*\n"
                f"  Порог RUB: {int(preset_data['strong_diff_rub']):,}\n"
                f"  Порог %: {preset_data['strong_diff_percent']}%",
                reply_markup=main_keyboard(),
            )
        elif data == "help":
            self.send_menu(chat_id)

    def apply_pending_action(self, chat_id: int, action: str, text: str) -> None:
        try:
            settings = load_runtime_settings(self.config)

            if action == "add_filter":
                current = [str(item) for item in settings.get("room_filters", self.config.room_filters)]
                if text.lower() not in {item.lower() for item in current}:
                    current.append(text)
                settings["room_filters"] = current
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Фильтр добавлен: {text}", reply_markup=main_keyboard())
            elif action == "add_search":
                url = normalize_search_url(text)
                searches = list(settings.get("searches", []))
                if any(isinstance(item, dict) and item.get("url") == url for item in searches):
                    self.send_message(chat_id, "Эта ссылка уже отслеживается.", reply_markup=main_keyboard())
                    return
                name = f"{provider_from_url(url)} {len(searches) + 1}"
                searches.append({"name": name, "url": url, "room_filters": []})
                settings["searches"] = searches
                save_runtime_settings(self.config, settings)

                msg = f"Добавлен {name}. Нажми Проверить сейчас."
                if is_bgoperator_url(url):
                    msg += "\n💡 Для сравнения цен добавь этот же отель на Level.Travel и Travelata."
                self.send_message(chat_id, msg, reply_markup=main_keyboard())
            elif action == "set_dates":
                start, end = parse_date_range_text(text)
                settings["departure_from"] = start
                settings["departure_to"] = end
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Диапазон дат сохранен: {start}-{end}", reply_markup=main_keyboard())
            elif action == "set_diff":
                rub, percent = parse_diff_text(text, self.config.strong_diff_percent)
                settings["strong_diff_rub"] = rub
                settings["strong_diff_percent"] = percent
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Порог разницы 12/13 сохранен: {rub} RUB или {percent}%", reply_markup=main_keyboard())
            elif action == "set_interval":
                interval_seconds = parse_interval_text(text)
                settings["interval_seconds"] = interval_seconds
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Частота проверки сохранена: {format_interval(interval_seconds)}", reply_markup=main_keyboard())
            elif action == "set_nights":
                nights = parse_nights(text)
                settings["nights"] = list(nights)
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Ночи сохранены: {', '.join(str(item) for item in nights)}", reply_markup=main_keyboard())
            elif action == "set_target":
                target = int(re.sub(r"\D", "", text))
                if target <= 0:
                    raise ValueError("цена должна быть > 0")
                settings["target_price_rub"] = target
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Целевая цена установлена: {format_rub(target)}", reply_markup=main_keyboard())
            elif action == "set_retention":
                days = int(re.sub(r"\D", "", text))
                if days < 7:
                    raise ValueError("минимальный срок хранения — 7 дней")
                settings["price_history_retention_days"] = days
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Срок хранения истории: {days} дн.", reply_markup=main_keyboard())
            elif action == "set_reference":
                ref = int(re.sub(r"\D", "", text))
                if ref <= 0:
                    raise ValueError("цена должна быть > 0")
                settings["reference_price_rub"] = ref
                save_runtime_settings(self.config, settings)
                self.send_message(chat_id, f"Ориентир цены: {format_rub(ref)}", reply_markup=main_keyboard())
        except ValueError as exc:
            self.send_message(chat_id, f"Не удалось сохранить настройку: {exc}", reply_markup=main_keyboard())
        except Exception as exc:
            logging.exception("Unexpected error in apply_pending_action action=%s", action)
            self.send_message(chat_id, "Внутренняя ошибка, попробуй ещё раз.", reply_markup=main_keyboard())

    def run_manual_check(self, chat_id: int) -> None:
        with self.check_lock:
            try:
                message = run_check(self.config)
            except Exception as exc:
                logging.exception("Manual price check failed")
                self.send_message(chat_id, f"Проверка не удалась: {exc}", reply_markup=main_keyboard())
                return
        self.send_message(chat_id, message, reply_markup=main_keyboard())

    def send_menu(self, chat_id: int) -> None:
        self.send_message(
            chat_id,
            "Бот мониторинга цен Библио-Глобуса\n"
            f"Твой chat id: {chat_id}\n\n"
            "Используй кнопки для проверки цен и изменения поиска.",
            reply_markup=main_keyboard(),
        )

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, object] | None = None,
    ) -> None:
        for chunk in split_telegram_text(text):
            payload: dict[str, object] = {
                "chat_id": chat_id,
                "text": escape_markdown_v2(chunk),
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            self.api("sendMessage", payload)

    def is_authorized(self, chat_id: int) -> bool:
        if not self.config.telegram_chat_id:
            return True
        return str(chat_id) == str(self.config.telegram_chat_id)


def main_keyboard() -> dict[str, object]:
    return {
        "inline_keyboard": [
            [{"text": "Проверить сейчас", "callback_data": "check"}],
            [
                {"text": "📊 Тренды", "callback_data": "trend"}, {"text": "📅 Неделя", "callback_data": "weekly"},
                {"text": "🤖 Совет", "callback_data": "recommend"},
            ],
            [{"text": "Настройки", "callback_data": "settings"}],
            [
                {"text": "Добавить отель/поиск", "callback_data": "add_search"},
                {"text": "Очистить доп. поиски", "callback_data": "clear_searches"},
            ],
            [
                {"text": "Добавить фильтр", "callback_data": "add_filter"},
                {"text": "Очистить фильтры", "callback_data": "clear_filters"},
            ],
            [
                {"text": "Даты вылета", "callback_data": "set_dates"},
                {"text": "Ночи", "callback_data": "set_nights"},
            ],
            [
                {"text": "Разница 12/13 ночей", "callback_data": "set_diff"},
                {"text": "Частота проверки", "callback_data": "set_interval"},
            ],
            [
                {"text": "🎯 Целевая цена", "callback_data": "set_target"},
                {"text": "Сбросить цель", "callback_data": "clear_target"},
            ],
        ]
    }


def settings_keyboard() -> dict[str, object]:
    return {
        "inline_keyboard": [
            [{"text": "⚠️ Пресет аномалий", "callback_data": "anomaly_preset"}],
            [
                {"text": "Добавить фильтр", "callback_data": "add_filter"},
                {"text": "Очистить фильтры", "callback_data": "clear_filters"},
            ],
            [
                {"text": "Добавить отель/поиск", "callback_data": "add_search"},
                {"text": "Очистить доп. поиски", "callback_data": "clear_searches"},
            ],
            [
                {"text": "Даты вылета", "callback_data": "set_dates"},
                {"text": "Ночи", "callback_data": "set_nights"},
            ],
            [
                {"text": "Разница 12/13 ночей", "callback_data": "set_diff"},
                {"text": "Частота проверки", "callback_data": "set_interval"},
            ],
            [
                {"text": "🎯 Целевая цена", "callback_data": "set_target"},
                {"text": "Сбросить цель", "callback_data": "clear_target"},
            ],
            [
                {"text": "🗑️ Хранение истории", "callback_data": "set_retention"},
                {"text": "💵 Ориентир цены", "callback_data": "set_reference"},
            ],
            [
                {"text": "📊 Тренды", "callback_data": "trend"}, {"text": "📅 Неделя", "callback_data": "weekly"},
                {"text": "🤖 Совет", "callback_data": "recommend"},
            ],
            [{"text": "Проверить сейчас", "callback_data": "check"}],
        ]
    }


def format_settings(config: MonitorConfig) -> str:
    filters = "; ".join(config.room_filters) if config.room_filters else "none"
    targets = load_search_targets(config)
    search_lines = "\n".join(f"  {index}. {target.name}" for index, target in enumerate(targets, start=1))
    target_str = format_rub(config.target_price_rub) if config.target_price_rub else "не задана"
    settings = load_runtime_settings(config)
    ref_raw = settings.get("reference_price_rub")
    ref_str = format_rub(int(ref_raw)) if isinstance(ref_raw, (int, float)) and int(ref_raw) > 0 else "не задан"
    try:
        days_left = (parse_ru_date(config.departure_from) - datetime.now()).days
        days_str = f"{days_left} дн."
    except ValueError:
        days_str = "?"
    labels = {"conservative": "консервативный", "balanced": "сбалансированный", "aggressive": "агрессивный"}
    preset_label = labels.get(config.anomaly_preset, "сбалансированный")
    return (
        "Текущие настройки:\n"
        f"Вылет: {config.departure_from}-{config.departure_to} (через {days_str})\n"
        f"Ночей: {', '.join(str(item) for item in config.nights)}\n"
        f"Фильтры: {filters}\n"
        "Разница 12/13 ночей: "
        f"показать, если >= {config.strong_diff_rub} RUB "
        f"или >= {config.strong_diff_percent}%\n"
        f"Пресет аномалий: {preset_label}\n"
        f"Хранение истории: {config.price_history_retention_days} дн.\n"
        f"Частота проверки: {format_interval(config.interval_seconds)}\n"
        f"Целевая цена: {target_str}\n"
        f"Ориентир цены: {ref_str}\n"
        f"Поиски:\n{search_lines}"
    )


def _normalize_hotel_name(name: str) -> str:
    """Lowercase and strip special chars for fuzzy matching."""
    return re.sub(r"[^\w\s]", "", name.lower()).strip()


def match_hotels_across_providers(results: list[TargetResult]) -> list[HotelGroup]:
    """Group TargetResults by fuzzy-matched hotel name.

    Only returns groups with 2+ providers.
    """
    named = [(r, _normalize_hotel_name(r.hotel_name))
             for r in results if r.hotel_name]
    if len(named) < 2:
        return []

    groups: list[list[TargetResult]] = []
    used: set[int] = set()

    for i, (r1, name1) in enumerate(named):
        if i in used:
            continue
        group = [r1]
        used.add(i)
        for j, (r2, name2) in enumerate(named):
            if j in used:
                continue
            if difflib.SequenceMatcher(None, name1, name2).ratio() > 0.6:
                group.append(r2)
                used.add(j)
        groups.append(group)

    return [
        HotelGroup(hotel_name=group[0].hotel_name or "Unknown", results=group)
        for group in groups
        if len(group) >= 2
    ]


def format_comparison(groups: list[HotelGroup]) -> str | None:
    """Format cross-provider price comparison block."""
    if not groups:
        return None

    provider_icons = {
        "Библио-Глобус": "🔵",
        "Level.Travel": "🟢",
        "Travelata": "🟠",
    }

    lines: list[str] = ["🌐 *Сравнение цен*"]

    for group in groups:
        lines.append(f"\n🏩 *{group.hotel_name}*")
        for r in group.results:
            icon = provider_icons.get(r.provider, "⚪")

            if r.best_by_date:
                overall = find_overall_best(r.best_by_date)
                if overall:
                    lines.append(
                        f"  {icon} {r.provider}: "
                        f"от *{format_rub(overall.price_rub)}* "
                        f"({overall.departure_date}, {overall.nights}н)"
                    )
                else:
                    lines.append(f"  {icon} {r.provider}: предложений не найдено")
            elif r.external_price and r.external_price.price_rub:
                lines.append(
                    f"  {icon} {r.provider}: "
                    f"от *{format_rub(r.external_price.price_rub)}*"
                )
            else:
                lines.append(f"  {icon} {r.provider}: цена не найдена")

    return "\n".join(lines)


def format_cross_search_comparison(
    target_results: list[TargetResult],
) -> str | None:
    """Compare best prices across multiple Bibli-Globus searches (different hotels)."""
    bg_results = [r for r in target_results if r.best_by_date]
    if len(bg_results) < 2:
        return None

    lines: list[str] = ["🏨 *Сравнение отелей*"]
    for r in bg_results:
        hotel = r.hotel_name or r.target_name
        overall = find_overall_best(r.best_by_date) if r.best_by_date else None
        if overall:
            lines.append(
                f"  • *{hotel}*: {format_rub(overall.price_rub)} "
                f"({overall.departure_date}, {overall.nights}н)"
            )
        else:
            lines.append(f"  • *{hotel}*: нет предложений")

def _generate_recommendation_from_db(config: MonitorConfig) -> str:
    """Generate buy/wait recommendation from DB snapshot + history + currency."""
    snapshot = load_snapshot(config)
    grouped = storage.load_price_history_grouped(config.db_path)

    days_left = 999
    try:
        days_left = (parse_ru_date(config.departure_from) - datetime.now()).days
    except ValueError:
        pass

    lines: list[str] = ["🤖 *Рекомендация*"]

    # Currency info
    try:
        usd_obs = storage.load_currency_observations(config.db_path, "USD/RUB", limit=2)
        if len(usd_obs) >= 2:
            usd_now = float(usd_obs[0][1])
            usd_prev = float(usd_obs[1][1])
            usd_pct = (usd_now - usd_prev) / usd_prev * 100
            if abs(usd_pct) > 0.3:
                arrow = "📈" if usd_pct > 0 else "📉"
                lines.append(f"💱 USD/RUB: {usd_now:.1f} ({arrow} {usd_pct:+.1f}%)")
            else:
                lines.append(f"💱 USD/RUB: {usd_now:.1f} (→ стабилен)")
    except Exception:
        pass

    lines.append(f"До вылета: *{days_left} дн.*\n")

    # Per-target analysis
    targets = load_search_targets(config)
    for target in targets:
        if not is_bgoperator_url(target.url):
            continue

        # Get current best price from snapshot
        best_price = None
        best_date = ""
        best_nights = 0
        for key, item in snapshot.items():
            if not key.startswith(target.name + "|"):
                continue
            p = int(item["price_rub"])
            if best_price is None or p < best_price:
                best_price = p
                best_date = str(item.get("departure_date", ""))
                best_nights = int(item.get("nights", 0))

        if best_price is None:
            lines.append(f"🏨 *{target.name}*\n  Нет данных\n")
            continue

        # Count unique check timestamps for this target
        timestamps: set[str] = set()
        by_date = grouped.get(target.name, {})
        for date, by_nights in by_date.items():
            for nights, points in by_nights.items():
                for p in points:
                    timestamps.add(p[0][:13])  # "2026-05-04T10"
        check_count = len(timestamps)

        # Find historical min from grouped history
        hist_min = None
        for date, by_nights in by_date.items():
            for nights, points in by_nights.items():
                if points:
                    m = min(p[1] for p in points)
                    if hist_min is None or m < hist_min:
                        hist_min = m

        # Get reference price from settings if set
        ref_price = None
        settings = load_runtime_settings(config)
        ref_raw = settings.get("reference_price_rub")
        if isinstance(ref_raw, (int, float)) and int(ref_raw) > 0:
            ref_price = int(ref_raw)

        # Verdict
        verdict = ""
        if check_count < 5:
            verdict = f"📊 *Мало данных* — {check_count} провер. Нужно минимум 5 для оценки."
        elif hist_min and best_price <= hist_min:
            verdict = "🎯 *БРАТЬ* — исторический минимум"
        elif days_left < 14:
            verdict = "⏰ *ПОРА* — меньше 2 недель"
        elif hist_min:
            pct = (best_price - hist_min) / hist_min * 100
            if pct < 3:
                verdict = f"👍 *МОЖНО БРАТЬ* — {pct:.0f}% выше мин. ({format_rub(hist_min)})"
            elif pct < 10:
                verdict = f"⏳ *ЖДАТЬ* — {pct:.0f}% выше мин. ({format_rub(hist_min)})"
            else:
                verdict = f"🔴 *ДОРОГО* — {pct:.0f}% выше мин. ({format_rub(hist_min)})"
        else:
            verdict = "📊 *НЕТ ДАННЫХ*"

        lines.append(f"🏨 *{target.name}*\n  Цена: *{format_rub(best_price)}* ({best_date}, {best_nights}н)")

        if ref_price:
            ref_pct = (best_price - ref_price) / ref_price * 100
            arrow = "📈" if best_price > ref_price else "📉"
            lines.append(f"  Ориентир: {format_rub(ref_price)} ({arrow} {ref_pct:+.0f}%)")

        lines.append(f"  {verdict}\n")

    lines.append("_На основе истории цен и курса. Не совет._")
    return "\n".join(lines)


def format_weekly_change(
    db_path: Path,
    config: MonitorConfig | None = None,
) -> str:
    """Compare current prices with 7 days ago, return compact summary."""
    grouped = storage.load_price_history_grouped(db_path)
    if not grouped:
        return "📅 *За неделю*\n\nНет данных для сравнения."

    now = datetime.now()
    week_ago = now - (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).__class__(days=7)

    lines: list[str] = ["📅 *За неделю*"]
    lines.append(f"{week_ago.strftime('%d.%m')} → {now.strftime('%d.%m')}\n")

    shown = 0
    for target_name, by_date in grouped.items():
        # Filter by config date range if provided
        if config:
            from datetime import timedelta
            try:
                start = parse_ru_date(config.departure_from)
                end = parse_ru_date(config.departure_to)
                d = start
                allowed = set()
                while d <= end:
                    allowed.add(d.strftime("%d.%m.%Y"))
                    d += timedelta(days=1)
            except ValueError:
                allowed = None
        else:
            allowed = None

        for date, by_nights in by_date.items():
            if allowed is not None and date not in allowed:
                continue
            for nights, points in by_nights.items():
                if len(points) < 2:
                    continue
                # Find price closest to 7 days ago
                prices_with_dates = [
                    (datetime.fromisoformat(p[0]), p[1])
                    for p in points
                ]
                prices_with_dates.sort()
                old_price = None
                for dt, price in prices_with_dates:
                    if dt <= week_ago:
                        old_price = price
                    else:
                        break
                if old_price is None:
                    continue
                current_price = prices_with_dates[-1][1]
                if old_price == current_price:
                    continue
                delta = current_price - old_price
                pct = delta / old_price * 100
                if abs(pct) < 0.5:
                    continue
                arrow = "📉" if delta < 0 else "📈"
                sign = "" if delta < 0 else "+"
                lines.append(
                    f"  {arrow} {date}, {nights}н: "
                    f"{format_rub(old_price)} → *{format_rub(current_price)}* "
                    f"({sign}{delta:+,.0f} RUB, {sign}{pct:.1f}%)".replace(",", " ")
                )
                shown += 1

    if shown == 0:
        lines.append("  Цены не изменились за неделю.")

    return "\n".join(lines)


def parse_date_range_text(text: str) -> tuple[str, str]:
    dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", text)
    if len(dates) != 2:
        raise ValueError("expected two dates in dd.mm.yyyy format")
    start, end = dates
    parsed_start = parse_ru_date(start)
    parsed_end = parse_ru_date(end)
    if parsed_start > parsed_end:
        raise ValueError("start date must be before end date")
    if (parsed_end - parsed_start).days > 2:
        raise ValueError("диапазон не больше 3 дней")
    return start, end


def parse_diff_text(text: str, default_percent: float) -> tuple[int, float]:
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
    if not numbers:
        raise ValueError("expected at least RUB threshold")
    rub = int(float(numbers[0].replace(",", ".")))
    percent = float(numbers[1].replace(",", ".")) if len(numbers) > 1 else default_percent
    return rub, percent


def parse_interval_text(text: str) -> int:
    value = text.strip().lower().replace(" ", "")
    match = re.fullmatch(r"(\d+)([smhd]?)", value)
    if not match:
        raise ValueError("expected 30m, 1h, 6h or seconds")

    amount = int(match.group(1))
    unit = match.group(2) or "s"
    multiplier = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }[unit]
    seconds = amount * multiplier
    if seconds < 300:
        raise ValueError("minimum interval is 5 minutes")
    return seconds


def format_interval(seconds: int) -> str:
    if seconds % 86400 == 0:
        days = seconds // 86400
        return f"{days} дн."
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} ч."
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} мин."
    return f"{seconds} сек."


def send_chart(config: MonitorConfig, chart_path: Path, chat_id: str | None = None) -> None:
    """Send a PNG chart to Telegram via sendPhoto."""
    if not config.telegram_bot_token:
        return
    target_chat_id = chat_id or config.telegram_chat_id
    if not target_chat_id:
        return
    with chart_path.open("rb") as f:
        chart_data = f.read()

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendPhoto"
    for attempt in range(4):  # 3 retries
        try:
            response = requests.post(
                url,
                data={"chat_id": target_chat_id},
                files={"photo": (chart_path.name, chart_data, "image/png")},
                timeout=30,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt >= 3:
                raise RuntimeError(f"Telegram sendPhoto failed after 4 attempts: {exc}")
            time.sleep(2 ** attempt)
            continue
        if response.status_code >= 500 and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        if response.status_code >= 400:
            raise RuntimeError(
                f"Telegram sendPhoto failed: HTTP {response.status_code}, body={response.text}"
            )
        return


def _send_chart_if_needed(
    config: MonitorConfig,
    interval_hours: int,
    last_sent: datetime | None,
) -> datetime | None:
    """Send weekly chart if enough time has passed."""
    now = datetime.now()
    if last_sent and (now - last_sent).total_seconds() < interval_hours * 3600:
        return last_sent
    try:
        from price_monitor import charts
        chart_path = charts.generate_price_chart(
            config.db_path,
            config.db_path.parent / "charts",
        )
        if chart_path and config.telegram_chat_id:
            send_chart(config, chart_path)
            logging.info("Weekly price chart sent")
        return now
    except Exception:
        logging.exception("Weekly chart generation/send failed")
        return last_sent


def _is_allowed_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return host in {"bgoperator.ru", "level.travel", "travelata.ru"}


def normalize_search_url(text: str) -> str:
    url = text.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("нужна полная ссылка https://...")
    host = parsed.netloc.lower()
    if not _is_allowed_host(host):
        raise ValueError("поддерживаются только bgoperator.ru, level.travel и travelata.ru")
    if "bgoperator.ru" in host and "price.shtml" not in parsed.path:
        raise ValueError("для Библио-Глобуса нужна ссылка price.shtml")
    return url


def configure_logging() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )


def _prune_if_needed(
    config: MonitorConfig,
    retention_days: int,
    last_prune: datetime | None,
    min_interval_hours: int = 24,
) -> datetime | None:
    """Prune price history if enough time has passed since last prune."""
    now = datetime.now()
    if last_prune and (now - last_prune).total_seconds() < min_interval_hours * 3600:
        return last_prune
    try:
        storage.prune_price_history(config.db_path, retention_days)
    except Exception:
        logging.exception("Price history pruning failed")
    return now


def _vacuum_if_needed(
    config: MonitorConfig,
    last_vacuum: datetime | None,
    interval_hours: int = 168,
) -> datetime | None:
    """Run VACUUM on the database if enough time has passed."""
    now = datetime.now()
    if last_vacuum and (now - last_vacuum).total_seconds() < interval_hours * 3600:
        return last_vacuum
    try:
        storage.vacuum_db(config.db_path)
        logging.info("Database VACUUM completed")
    except Exception:
        logging.exception("Database VACUUM failed")
    return now


def main() -> int:
    configure_logging()
    config = MonitorConfig.from_env()
    initialize_storage(config)
    check_lock = threading.Lock()
    TelegramControlBot(config, check_lock).start()

    last_currency_check: datetime | None = None
    last_prune: datetime | None = None
    last_vacuum: datetime | None = None
    last_chart_sent: datetime | None = None

    while True:
        try:
            with check_lock:
                message = run_check(config)
            send_telegram(effective_config(config), message)
        except Exception:
            logging.exception("Price check failed")
            if config.run_once:
                return 1

        # Currency monitoring: check periodically based on configured interval
        now = datetime.now()
        if (
            last_currency_check is None
            or (now - last_currency_check).total_seconds() >= config.currency_check_hours * 3600
        ):
            try:
                currency_alert = currency.run_currency_check(
                    config.db_path,
                    config.currency_source_url,
                    config.currency_alert_threshold_pct,
                )
                if currency_alert:
                    send_telegram(effective_config(config), currency_alert)
                last_currency_check = now
            except Exception:
                logging.exception("Currency check failed")

        if config.run_once:
            return 0

        active = effective_config(config)
        last_prune = _prune_if_needed(config, active.price_history_retention_days, last_prune)
        last_vacuum = _vacuum_if_needed(config, last_vacuum)
        if active.chart_interval_hours > 0:
            last_chart_sent = _send_chart_if_needed(config, active.chart_interval_hours, last_chart_sent)

        sleep_seconds = adaptive_interval(active.departure_from, active.interval_seconds)
        logging.info("Next check in %s", format_interval(sleep_seconds))
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
