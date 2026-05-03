from __future__ import annotations

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

from price_monitor import storage


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
    state_path: Path
    settings_path: Path
    strong_diff_rub: int
    strong_diff_percent: float
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    target_price_rub: int | None
    history_path: Path

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
            state_path=Path(os.getenv("BG_STATE_PATH", "/data/last_snapshot.json")),
            settings_path=Path(os.getenv("BG_SETTINGS_PATH", "/data/settings.json")),
            strong_diff_rub=int(os.getenv("BG_STRONG_DIFF_RUB", "20000")),
            strong_diff_percent=float(os.getenv("BG_STRONG_DIFF_PERCENT", "7")),
            telegram_bot_token=empty_to_none(os.getenv("TELEGRAM_BOT_TOKEN")),
            telegram_chat_id=empty_to_none(os.getenv("TELEGRAM_CHAT_ID")),
            target_price_rub=int(target_raw) if target_raw else None,
            history_path=Path(os.getenv("BG_HISTORY_PATH", "/data/price_history.json")),
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

    for key in (
        "departure_from",
        "departure_to",
        "strong_diff_rub",
        "strong_diff_percent",
        "interval_seconds",
    ):
        if key in settings:
            updates[key] = settings[key]

    if "nights" in settings:
        updates["nights"] = tuple(int(item) for item in settings["nights"])  # type: ignore[index]
    if "room_filters" in settings:
        updates["room_filters"] = tuple(str(item) for item in settings["room_filters"])  # type: ignore[index]
    if "target_price_rub" in settings:
        raw = settings["target_price_rub"]
        updates["target_price_rub"] = int(raw) if raw is not None else None  # type: ignore[arg-type]

    return replace(config, **updates)


def load_search_targets(config: MonitorConfig) -> list[SearchTarget]:
    settings = load_runtime_settings(config)
    targets = [SearchTarget(name="Основной поиск", url=config.url, room_filters=config.room_filters)]

    for index, item in enumerate(settings.get("searches", []), start=2):  # type: ignore[arg-type]
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        name = str(item.get("name") or f"Поиск {index}").strip()
        filters = tuple(str(value) for value in item.get("room_filters", []))  # type: ignore[arg-type]
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
                "✅ *Лучшая цена*",
                f"• `{overall.departure_date}`, `{overall.nights}` ночей",
                f"• *{format_price(overall)}* [Забронировать]({overall.booking_url})",
            ]
        )
    else:
        lines.append("")
        lines.append("⚠️ Подходящие предложения не найдены.")
        return "\n".join(lines)

    lines.extend(["", "📊 *По датам вылета*"])
    for departure_date, by_nights in best.items():
        lines.append("")
        lines.append(f"*{departure_date}*")
        for nights in config.nights:
            offer = by_nights.get(nights)
            if offer:
                lines.append(f"• `{nights}` ночей: `{format_price(offer)}` [Бронь]({offer.booking_url})")
            else:
                lines.append(f"• `{nights}` ночей: не найдено")

        diff_line = format_strong_diff_line(
            departure_date=departure_date,
            by_nights=by_nights,
            config=config,
        )
        if diff_line:
            lines.append(f"⚖️ {diff_line.strip()}")

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
) -> str | None:
    lines: list[str] = []
    for key, item in current_snapshot.items():
        prev_min = historical_min_price(history, key)
        if prev_min is None:
            continue
        current_price = int(item["price_rub"])
        if current_price < prev_min:
            booking_url = str(item.get("booking_url") or "")
            link = f" [Забронировать]({booking_url})" if booking_url else ""
            trend = compute_trend(history, key)
            trend_str = f", {trend}" if trend else ""
            lines.append(
                f"🏆 Исторический минимум: `{item['departure_date']}`, "
                f"`{item['nights']}` ночей — *{format_rub(current_price)}*"
                f"{trend_str}{link}"
            )
    return "\n".join(lines) if lines else None


def format_target_alerts(
    current_snapshot: dict[str, dict[str, object]],
    target_price_rub: int,
) -> str | None:
    lines: list[str] = []
    for item in current_snapshot.values():
        price = int(item["price_rub"])
        if price <= target_price_rub:
            booking_url = str(item.get("booking_url") or "")
            link = f" [Забронировать]({booking_url})" if booking_url else ""
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
) -> str | None:
    if not previous:
        return None

    lines: list[str] = []

    for identity, item in current.items():
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
            link = f" [Забронировать]({booking_url})" if booking_url and fell else ""
            diff = old_price - new_price if fell else new_price - old_price
            sign = "-" if fell else "+"
            lines.append(
                f"{marker} {item['departure_date']}, {item['nights']}н: "
                f"*{format_rub(new_price)}* ({sign}{format_rub(diff)}){link}"
            )

    return "\n".join(lines) if lines else None


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 personal-bg-price-monitor",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    return response.text


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


def parse_external_price(html: str, url: str) -> ExternalPrice:
    provider = provider_from_url(url)
    return ExternalPrice(
        provider=provider,
        hotel_name=extract_external_hotel_name(html, provider),
        price_rub=extract_external_min_price(html),
        url=url,
    )


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

    for match in re.finditer(r"от\s+(\d[\d\s\u00a0]*)\s*(?:руб|₽)", html, flags=re.IGNORECASE):
        candidates.append(parse_int(match.group(1)))

    return min(candidates) if candidates else None


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
) -> dict[str, object]:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        timeout=timeout,
        json=payload,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Telegram API {method} failed: HTTP {response.status_code}, "
            f"body={response.text}"
        )
    return response.json()


def run_check(config: MonitorConfig) -> str:
    active_config = effective_config(config)
    reports: list[str] = []
    current_snapshot: dict[str, dict[str, object]] = {}

    for target in load_search_targets(active_config):
        html = fetch_html(target.url)

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

    previous_snapshot = load_snapshot(active_config)
    history = load_price_history(active_config)

    changes = format_changes(previous_snapshot, current_snapshot)
    # Suppress notification when all changes are new offers (first run after empty snapshot)
    if changes and all(line.startswith("🆕") for line in changes.splitlines()):
        changes = None

    minimums = format_new_minimums(current_snapshot, history)

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M")
    append_price_history(active_config, current_snapshot, ts)
    save_snapshot(active_config, current_snapshot)

    target_alerts = (
        format_target_alerts(current_snapshot, active_config.target_price_rub)
        if active_config.target_price_rub
        else None
    )

    report = "\n\n".join(reports)
    alerts: list[str] = []
    if minimums:
        alerts.append(f"🏆 *Исторические минимумы*\n{minimums}")
    if target_alerts:
        alerts.append(f"🎯 *Цель достигнута*\n{target_alerts}")
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
        elif data == "clear_target":
            settings = load_runtime_settings(self.config)
            settings["target_price_rub"] = None
            save_runtime_settings(self.config, settings)
            self.send_message(chat_id, "Целевая цена сброшена.", reply_markup=main_keyboard())
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
                self.send_message(chat_id, f"Добавлен {name}. Нажми Проверить сейчас.", reply_markup=main_keyboard())
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
        except ValueError as exc:
            self.send_message(chat_id, f"Не удалось сохранить настройку: {exc}", reply_markup=main_keyboard())
        except Exception as exc:
            logging.exception("Unexpected error in apply_pending_action action=%s", action)
            self.send_message(chat_id, "Внутренняя ошибка, попробуй ещё раз.", reply_markup=main_keyboard())

    def run_manual_check(self, chat_id: int) -> None:
        self.send_message(chat_id, "Проверяю цены...")
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
            [{"text": "Проверить сейчас", "callback_data": "check"}],
        ]
    }


def format_settings(config: MonitorConfig) -> str:
    filters = "; ".join(config.room_filters) if config.room_filters else "none"
    targets = load_search_targets(config)
    search_lines = "\n".join(f"  {index}. {target.name}" for index, target in enumerate(targets, start=1))
    target_str = format_rub(config.target_price_rub) if config.target_price_rub else "не задана"
    try:
        days_left = (parse_ru_date(config.departure_from) - datetime.now()).days
        days_str = f"{days_left} дн."
    except ValueError:
        days_str = "?"
    return (
        "Текущие настройки:\n"
        f"Вылет: {config.departure_from}-{config.departure_to} (через {days_str})\n"
        f"Ночей: {', '.join(str(item) for item in config.nights)}\n"
        f"Фильтры: {filters}\n"
        "Разница 12/13 ночей: "
        f"показать, если >= {config.strong_diff_rub} RUB "
        f"или >= {config.strong_diff_percent}%\n"
        f"Частота проверки: {format_interval(config.interval_seconds)}\n"
        f"Целевая цена: {target_str}\n"
        f"Поиски:\n{search_lines}"
    )


def parse_date_range_text(text: str) -> tuple[str, str]:
    dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", text)
    if len(dates) != 2:
        raise ValueError("expected two dates in dd.mm.yyyy format")
    start, end = dates
    if parse_ru_date(start) > parse_ru_date(end):
        raise ValueError("start date must be before end date")
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


def normalize_search_url(text: str) -> str:
    url = text.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("нужна полная ссылка https://...")
    host = parsed.netloc.lower()
    allowed_hosts = ("bgoperator.ru", "level.travel", "travelata.ru")
    if not any(allowed in host for allowed in allowed_hosts):
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


def main() -> int:
    configure_logging()
    config = MonitorConfig.from_env()
    initialize_storage(config)
    check_lock = threading.Lock()
    TelegramControlBot(config, check_lock).start()

    while True:
        try:
            with check_lock:
                message = run_check(config)
            send_telegram(effective_config(config), message)
        except Exception:
            logging.exception("Price check failed")
            if config.run_once:
                return 1

        if config.run_once:
            return 0

        active = effective_config(config)
        sleep_seconds = adaptive_interval(active.departure_from, active.interval_seconds)
        logging.info("Next check in %s", format_interval(sleep_seconds))
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
