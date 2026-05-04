import logging
from pathlib import Path

import threading

from price_monitor.monitor import (
    ANOMALY_PRESETS,
    MonitorConfig,
    TelegramControlBot,
    adaptive_interval,
    best_by_departure_and_nights,
    escape_markdown_v2,
    effective_config,
    initialize_storage,
    extract_hotel_name,
    filter_offers,
    find_overall_best,
    format_changes,
    format_duration_anomalies,
    format_new_minimums,
    format_report,
    format_strong_diff_line,
    format_target_alerts,
    format_trend_report,
    format_interval,
    format_settings,
    load_price_history,
    load_runtime_settings,
    load_search_targets,
    load_snapshot,
    main_keyboard,
    parse_external_price,
    parse_date_range_text,
    parse_diff_text,
    parse_interval_text,
    normalize_search_url,
    parse_offers,
    run_check,
    save_runtime_settings,
    save_snapshot,
    settings_keyboard,
    snapshot,
)


def test_parse_offers_extracts_price_and_booking_fields():
    html = """
    <table>
      <tr>
        <td class="c_dn"><b>12</b></td>
        <td class="c_ar">Carrier</td>
        <td class="c_ns c_ns__ai">SUPERIOR DELUXE Garden View AI<br>ALL INCLUSIVE</td>
        <td class="c_pe">
          <div class="pe">
            <b class=r>286230</b> р.
            <a href="https://www.bgoperator.ru/zaya?dt=14.09.2026&kol=12&otn=104610620518" title="3542 USD">
              <b>Buy</b>
            </a>
          </div>
        </td>
      </tr>
    </table>
    """

    offers = parse_offers(html)

    assert len(offers) == 1
    assert offers[0].departure_date == "14.09.2026"
    assert offers[0].nights == 12
    assert offers[0].price_rub == 286230
    assert offers[0].price_usd == 3542
    assert offers[0].hotel_option_id == "104610620518"


def test_filter_and_best_offer_by_departure_and_nights():
    html = """
    <table>
      <tr><td class="c_ns">Room A</td><td class="c_pe"><b class=r>300000</b><a href="/zaya?dt=14.09.2026&kol=12&otn=a" title="3700 USD">Buy</a></td></tr>
      <tr><td class="c_ns">Room B</td><td class="c_pe"><b class=r>280000</b><a href="/zaya?dt=14.09.2026&kol=12&otn=b" title="3500 USD">Buy</a></td></tr>
      <tr><td class="c_ns">Room C</td><td class="c_pe"><b class=r>340000</b><a href="/zaya?dt=14.09.2026&kol=13&otn=c" title="4200 USD">Buy</a></td></tr>
      <tr><td class="c_ns">Room D</td><td class="c_pe"><b class=r>290000</b><a href="/zaya?dt=18.09.2026&kol=12&otn=d" title="3600 USD">Buy</a></td></tr>
    </table>
    """
    config = MonitorConfig(
        url="https://example.test",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=(),
        interval_seconds=1,
        run_once=True,
        db_path=Path("price_monitor.sqlite3"),
        state_path=Path("state.json"),
        settings_path=Path("settings.json"),
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=Path("price_history.json"),
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )

    best = best_by_departure_and_nights(filter_offers(parse_offers(html), config))

    assert best["14.09.2026"][12].price_rub == 280000
    assert best["14.09.2026"][13].price_rub == 340000
    assert "18.09.2026" not in best


def test_strong_diff_line_flags_large_12_13_gap():
    html = """
    <table>
      <tr><td class="c_ns">Room A</td><td class="c_pe"><b class=r>280000</b><a href="/zaya?dt=14.09.2026&kol=12&otn=a" title="3500 USD">Buy</a></td></tr>
      <tr><td class="c_ns">Room B</td><td class="c_pe"><b class=r>340000</b><a href="/zaya?dt=14.09.2026&kol=13&otn=b" title="4200 USD">Buy</a></td></tr>
    </table>
    """
    config = MonitorConfig(
        url="https://example.test",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=(),
        interval_seconds=1,
        run_once=True,
        db_path=Path("price_monitor.sqlite3"),
        state_path=Path("state.json"),
        settings_path=Path("settings.json"),
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=Path("price_history.json"),
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )
    best = best_by_departure_and_nights(filter_offers(parse_offers(html), config))

    line = format_strong_diff_line("14.09.2026", best["14.09.2026"], config)

    assert line is not None
    assert "60 000 RUB" in line


def test_parse_date_range_text():
    assert parse_date_range_text("14.09.2026 17.09.2026") == (
        "14.09.2026",
        "17.09.2026",
    )


def test_parse_diff_text():
    assert parse_diff_text("10000 4.5", default_percent=7) == (10000, 4.5)
    assert parse_diff_text("15000", default_percent=7) == (15000, 7)


def test_normalize_bg_url_accepts_price_page():
    url = "https://www.bgoperator.ru/price.shtml?action=price"
    assert normalize_search_url(url) == url


def test_normalize_search_url_accepts_level_and_travelata():
    assert normalize_search_url("https://level.travel/hotels/629-test") == "https://level.travel/hotels/629-test"
    assert normalize_search_url("https://travelata.ru/") == "https://travelata.ru/"


def test_escape_markdown_v2_keeps_format_markers_and_escapes_plain_text():
    text = "🏨 *Main search*\n🏩 Отель: `JAZ MAKADI 5*`\n📅 Period: `14.09.2026 - 17.09.2026`"

    escaped = escape_markdown_v2(text)

    assert "*Main search*" in escaped
    assert "`JAZ MAKADI 5*`" in escaped
    assert "`14.09.2026 - 17.09.2026`" in escaped


def test_parse_and_format_interval_text():
    assert parse_interval_text("30m") == 1800
    assert parse_interval_text("6h") == 21600
    assert format_interval(21600) == "6 ч."


def test_extract_hotel_name_from_hotel_id_catalog():
    html = '[102632942104,{"c":"5*", "n":"JAZ MAKADI SARAYA RESORT (ex. IBEROTEL) 5*"}]'
    url = "https://www.bgoperator.ru/price.shtml?F4=102632942104"

    assert extract_hotel_name(html, url) == "JAZ MAKADI SARAYA RESORT (ex. IBEROTEL) 5*"


def test_parse_external_price_from_level_microdata():
    html = """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Hotel","name":"Jaz Makadi Oasis","priceRange":"от 138 920 руб."}
    </script>
    <script>{"minPrice":153949}</script>
    """

    price = parse_external_price(html, "https://level.travel/hotels/629-test")

    assert price.provider == "Level.Travel"
    assert price.hotel_name == "Jaz Makadi Oasis"
    assert price.price_rub == 138920


def test_monitor_config_reads_db_path(monkeypatch):
    monkeypatch.delenv("BG_DB_PATH", raising=False)

    assert MonitorConfig.from_env().db_path == Path("/data/price_monitor.sqlite3")

    monkeypatch.setenv("BG_DB_PATH", "custom.sqlite3")

    assert MonitorConfig.from_env().db_path == Path("custom.sqlite3")


def test_monitor_storage_wrappers_use_sqlite(tmp_path: Path):
    config = MonitorConfig(
        url="https://example.test",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=(),
        interval_seconds=1,
        run_once=True,
        db_path=tmp_path / "price_monitor.sqlite3",
        state_path=tmp_path / "state.json",
        settings_path=tmp_path / "settings.json",
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=tmp_path / "price_history.json",
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )

    initialize_storage(config)
    save_runtime_settings(config, {"nights": [12], "target_price_rub": 180000})
    save_snapshot(
        config,
        {
            "Main search|14.09.2026|12|a": {
                "departure_date": "14.09.2026",
                "nights": 12,
                "price_rub": 180000,
            }
        },
    )

    assert load_runtime_settings(config) == {
        "nights": [12],
        "target_price_rub": 180000,
    }
    assert load_snapshot(config)["Main search|14.09.2026|12|a"]["price_rub"] == 180000
    assert load_price_history(config) == {}
    assert not config.settings_path.exists()
    assert not config.state_path.exists()


def test_run_check_persists_snapshot_and_history_in_sqlite(tmp_path: Path, monkeypatch):
    html = """
    <table>
      <tr>
        <td class="c_ns">Room A</td>
        <td class="c_pe">
          <b class=r>180000</b>
          <a href="/zaya?dt=14.09.2026&kol=12&otn=a" title="2200 USD">Buy</a>
        </td>
      </tr>
    </table>
    """
    config = MonitorConfig(
        url="https://www.bgoperator.ru/price.shtml?action=price",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12,),
        room_filters=(),
        interval_seconds=1,
        run_once=True,
        db_path=tmp_path / "price_monitor.sqlite3",
        state_path=tmp_path / "state.json",
        settings_path=tmp_path / "settings.json",
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=tmp_path / "price_history.json",
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )
    monkeypatch.setattr("price_monitor.monitor.fetch_html", lambda url: html)

    initialize_storage(config)
    run_check(config)

    persisted_snapshot = load_snapshot(config)
    persisted_history = load_price_history(config)
    snapshot_key = next(iter(persisted_snapshot))

    assert snapshot_key.endswith("|14.09.2026|12|a")
    assert persisted_snapshot[snapshot_key]["price_rub"] == 180000
    assert persisted_history == {
        snapshot_key: [[persisted_history[snapshot_key][0][0], 180000]]
    }
    assert not config.state_path.exists()
    assert not config.history_path.exists()


def test_effective_config_ignores_invalid_runtime_settings(
    tmp_path: Path,
    caplog,
):
    config = MonitorConfig(
        url="https://example.test",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=("SUPERIOR",),
        interval_seconds=3600,
        run_once=True,
        db_path=tmp_path / "price_monitor.sqlite3",
        state_path=tmp_path / "state.json",
        settings_path=tmp_path / "settings.json",
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=tmp_path / "price_history.json",
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )
    initialize_storage(config)
    save_runtime_settings(
        config,
        {
            "nights": ["bad"],
            "room_filters": 123,
            "target_price_rub": "bad",
            "strong_diff_rub": "bad",
            "strong_diff_percent": "bad",
            "interval_seconds": "bad",
        },
    )

    with caplog.at_level(logging.WARNING):
        active = effective_config(config)

    assert active.nights == config.nights
    assert active.room_filters == config.room_filters
    assert active.target_price_rub == config.target_price_rub
    assert active.strong_diff_rub == config.strong_diff_rub
    assert active.strong_diff_percent == config.strong_diff_percent
    assert active.interval_seconds == config.interval_seconds
    assert "Ignoring invalid runtime setting nights" in caplog.text
    assert "Ignoring invalid runtime setting room_filters" in caplog.text


def test_load_search_targets_skips_malformed_entries(tmp_path: Path):
    config = MonitorConfig(
        url="https://example.test",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=(),
        interval_seconds=3600,
        run_once=True,
        db_path=tmp_path / "price_monitor.sqlite3",
        state_path=tmp_path / "state.json",
        settings_path=tmp_path / "settings.json",
        strong_diff_rub=20000,
        strong_diff_percent=7,
        telegram_bot_token=None,
        telegram_chat_id=None,
        target_price_rub=None,
        history_path=tmp_path / "price_history.json",
        currency_source_url="https://example.test/rates",
        currency_alert_threshold_pct=1.0,
        currency_check_hours=24,
        price_history_retention_days=90,
        chart_interval_hours=168,
        anomaly_preset="balanced",
    )
    initialize_storage(config)
    save_runtime_settings(
        config,
        {
            "searches": [
                "bad",
                {"url": ""},
                {"name": "Broken filters", "url": "https://level.travel/hotels/629-test", "room_filters": None},
                {"name": "Valid", "url": "https://travelata.ru/", "room_filters": ["Room"]},
            ]
        },
    )

    targets = load_search_targets(config)

    assert len(targets) == 2
    assert targets[1].name == "Valid"
    assert targets[1].room_filters == ("Room",)


def test_normalize_search_url_rejects_lookalike_domains():
    import pytest

    lookalikes = [
        "https://bgoperator.ru.evil.com/price.shtml",
        "https://evil-bgoperator.ru/price.shtml",
        "https://not-bgoperator.ru/price.shtml",
        "https://bgoperator.ru.phishing.net/",
        "https://fake-level.travel.evil.com/hotels/629",
        "https://level.travel.hacked.ru/",
        "https://travelata.ru.scam.ru/",
    ]
    for url in lookalikes:
        with pytest.raises(ValueError, match="поддерживаются только"):
            normalize_search_url(url)


def test_normalize_search_url_accepts_www_prefix():
    assert "https://www.bgoperator.ru/price.shtml" == normalize_search_url(
        "https://www.bgoperator.ru/price.shtml"
    )
    assert "https://www.level.travel/hotels/629" == normalize_search_url(
        "https://www.level.travel/hotels/629"
    )


def _make_bot_config(**kwargs):
    defaults = {
        "url": "https://example.test",
        "departure_from": "14.09.2026",
        "departure_to": "17.09.2026",
        "nights": (12, 13),
        "room_filters": (),
        "interval_seconds": 3600,
        "run_once": True,
        "db_path": Path("price_monitor.sqlite3"),
        "state_path": Path("state.json"),
        "settings_path": Path("settings.json"),
        "strong_diff_rub": 20000,
        "strong_diff_percent": 7,
        "telegram_bot_token": "test-token",
        "telegram_chat_id": None,
        "target_price_rub": None,
        "history_path": Path("price_history.json"),
        "currency_source_url": "https://example.test/rates",
        "currency_alert_threshold_pct": 1.0,
        "currency_check_hours": 24,
        "price_history_retention_days": 90,
        "chart_interval_hours": 168,
        "anomaly_preset": "balanced",
    }
    defaults.update(kwargs)
    return MonitorConfig(**defaults)


def test_is_authorized_blocks_unrecognized_chat():
    config = _make_bot_config(telegram_chat_id="123")
    bot = TelegramControlBot(config, threading.Lock())

    assert bot.is_authorized(123) is True
    assert bot.is_authorized(456) is False
    assert bot.is_authorized(999) is False


def test_is_authorized_allows_all_when_chat_id_unset():
    config = _make_bot_config(telegram_chat_id=None)
    bot = TelegramControlBot(config, threading.Lock())

    assert bot.is_authorized(123) is True
    assert bot.is_authorized(456) is True
    assert bot.is_authorized(999) is True


def test_main_keyboard_structure():
    kb = main_keyboard()

    assert "inline_keyboard" in kb
    rows = kb["inline_keyboard"]
    assert isinstance(rows, list)

    callback_data_values = {
        btn["callback_data"]
        for row in rows
        for btn in row
    }

    expected = {
        "check", "settings", "add_search", "clear_searches",
        "add_filter", "clear_filters", "set_dates", "set_nights",
        "set_diff", "set_interval", "set_target", "clear_target",
    }
    assert callback_data_values == expected


def test_settings_keyboard_structure():
    kb = settings_keyboard()

    assert "inline_keyboard" in kb
    rows = kb["inline_keyboard"]
    assert isinstance(rows, list)

    callback_data_values = {
        btn["callback_data"]
        for row in rows
        for btn in row
    }

    expected = {
        "check", "add_search", "clear_searches",
        "add_filter", "clear_filters", "set_dates", "set_nights",
        "set_diff", "set_interval", "set_target", "clear_target",
    }
    assert callback_data_values == expected


def test_format_settings_contains_key_fields(tmp_path: Path):
    config = _make_bot_config(
        db_path=tmp_path / "price_monitor.sqlite3",
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        target_price_rub=180000,
        interval_seconds=3600,
    )
    initialize_storage(config)

    output = format_settings(config)

    assert "14.09.2026" in output
    assert "17.09.2026" in output
    assert "12" in output
    assert "13" in output
    assert "180 000" in output
    assert "1 ч." in output
    assert "Поиски:" in output
    assert "Ночей:" in output
    assert "Целевая цена:" in output
    assert "Фильтры:" in output


def _make_offer(departure_date="14.09.2026", nights=12, room="Standard", price_rub=200000, price_usd=None, booking_url="https://example.test/book", hotel_option_id="a1"):
    return __import__("price_monitor.monitor", fromlist=["Offer"]).Offer(
        departure_date=departure_date,
        nights=nights,
        room=room,
        price_rub=price_rub,
        price_usd=price_usd,
        booking_url=booking_url,
        hotel_option_id=hotel_option_id,
    )


def test_find_overall_best_selects_cheapest():
    best = {
        "14.09.2026": {12: _make_offer("14.09.2026", 12, price_rub=280000)},
        "15.09.2026": {12: _make_offer("15.09.2026", 12, price_rub=220000), 13: _make_offer("15.09.2026", 13, price_rub=310000)},
    }

    overall = find_overall_best(best)

    assert overall is not None
    assert overall.departure_date == "15.09.2026"
    assert overall.nights == 12
    assert overall.price_rub == 220000


def test_find_overall_best_returns_none_for_empty():
    assert find_overall_best({}) is None
    assert find_overall_best({"14.09.2026": {}}) is None


def test_format_report_includes_all_sections():
    config = _make_bot_config(
        departure_from="14.09.2026",
        departure_to="17.09.2026",
        nights=(12, 13),
        room_filters=("Superior",),
    )
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, "Superior", 250000, 3200),
            13: _make_offer("14.09.2026", 13, "Superior", 340000, 4400),
        },
    }

    report = format_report(best, config, "Test Hotel", "Grand Resort 5*")

    assert "Test Hotel" in report
    assert "Grand Resort 5*" in report
    assert "14.09.2026" in report
    assert "17.09.2026" in report
    assert "12" in report
    assert "13" in report
    assert "Superior" in report
    assert "250 000 RUB" in report
    assert "Лучшая цена" in report
    assert "По датам вылета" in report


def test_format_report_handles_empty_best():
    config = _make_bot_config()

    report = format_report({}, config, "Test Hotel")

    assert "Подходящие предложения не найдены" in report


def test_snapshot_creates_identity_keys():
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, "Room A", 200000, hotel_option_id="opt1"),
            13: _make_offer("14.09.2026", 13, "Room B", 300000, hotel_option_id="opt2"),
        },
    }

    snap = snapshot(best, "Main")

    assert "Main|14.09.2026|12|opt1" in snap
    assert "Main|14.09.2026|13|opt2" in snap
    assert snap["Main|14.09.2026|12|opt1"]["price_rub"] == 200000
    assert snap["Main|14.09.2026|13|opt2"]["price_rub"] == 300000


def test_format_changes_returns_none_for_empty_previous():
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 200000},
    }

    changes = format_changes({}, current)

    assert changes is None


def test_format_changes_detects_new_offers():
    previous = {
        "Main|14.09.2026|12|old": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 200000},
    }
    current = {
        "Main|14.09.2026|12|old": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 200000},
        "Main|14.09.2026|12|new": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 180000},
    }

    changes = format_changes(previous, current)

    assert changes is not None
    assert "Новое предложение" in changes
    assert "180000" in changes


def test_format_changes_detects_price_increase():
    previous = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 200000},
    }
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 220000},
    }

    changes = format_changes(previous, current)

    assert changes is not None
    # Price increase uses 📈 emoji, not text "выросла"
    assert "📈" in changes
    assert "220 000 RUB" in changes


def test_format_changes_detects_price_decrease():
    previous = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 250000},
    }
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 180000, "booking_url": "https://test.test/book"},
    }

    changes = format_changes(previous, current)

    assert changes is not None
    # Price decrease uses 📉 emoji, not text "упала"
    assert "📉" in changes
    assert "180 000 RUB" in changes
    assert "Забронировать" in changes


def test_format_new_minimums_detects_historical_low():
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 150000},
    }
    history = {
        "Main|14.09.2026|12|a": [
            ["2026-05-01T10:00", 200000],
            ["2026-05-02T10:00", 180000],
        ],
    }

    result = format_new_minimums(current, history)

    assert result is not None
    assert "Исторический минимум" in result
    assert "150 000 RUB" in result


def test_format_new_minimums_skips_when_not_minimum():
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 200000},
    }
    history = {
        "Main|14.09.2026|12|a": [
            ["2026-05-01T10:00", 150000],
            ["2026-05-02T10:00", 180000],
        ],
    }

    result = format_new_minimums(current, history)

    assert result is None


def test_format_target_alerts_detects_target_met():
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 180000},
        "Main|15.09.2026|12|b": {"departure_date": "15.09.2026", "nights": 12, "price_rub": 250000},
    }

    result = format_target_alerts(current, target_price_rub=200000)

    assert result is not None
    assert "Цена достигла цели" in result
    assert "180 000 RUB" in result
    assert "15.09.2026" not in result


def test_format_target_alerts_skips_above_target():
    current = {
        "Main|14.09.2026|12|a": {"departure_date": "14.09.2026", "nights": 12, "price_rub": 250000},
    }

    result = format_target_alerts(current, target_price_rub=200000)

    assert result is None


def test_adaptive_interval_reduces_when_close(monkeypatch):
    from datetime import datetime as dt

    # Mock datetime.now to a fixed date
    class MockDateTime(dt):
        @classmethod
        def now(cls, tz=None):
            return dt(2026, 9, 10)

    monkeypatch.setattr("price_monitor.monitor.datetime", MockDateTime)

    # 4 days until departure → should use max 900s
    assert adaptive_interval("14.09.2026", 3600) == 900

    # 20 days → max 3600s
    assert adaptive_interval("30.09.2026", 7200) == 3600

    # 45 days → max 21600s  
    assert adaptive_interval("25.10.2026", 86400) == 21600

    # 90 days → unchanged
    assert adaptive_interval("01.12.2026", 43200) == 43200


def test_duration_anomalies_detects_longer_cheaper():
    config = _make_bot_config(
        nights=(12, 13, 14),
        strong_diff_rub=5000,
        strong_diff_percent=5,
    )
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, price_rub=250000),
            13: _make_offer("14.09.2026", 13, price_rub=230000),
            14: _make_offer("14.09.2026", 14, price_rub=260000),
        },
    }

    result = format_duration_anomalies(best, config)

    assert result is not None
    # 13 nights cheaper than 12 by 20,000 (8%)
    assert "13н дешевле 12н" in result
    assert "20 000 RUB" in result
    # 14 nights NOT cheaper than 12 or 13
    assert "14н дешевле" not in result


def test_duration_anomalies_respects_threshold():
    config = _make_bot_config(
        nights=(12, 13),
        strong_diff_rub=50000,
        strong_diff_percent=20,
    )
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, price_rub=250000),
            13: _make_offer("14.09.2026", 13, price_rub=240000),
        },
    }

    result = format_duration_anomalies(best, config)

    # 10,000 RUB (4%) is below both thresholds → suppressed
    assert result is None


def test_duration_anomalies_returns_none_when_no_anomaly():
    config = _make_bot_config(nights=(12, 13, 14))
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, price_rub=200000),
            13: _make_offer("14.09.2026", 13, price_rub=300000),
            14: _make_offer("14.09.2026", 14, price_rub=400000),
        },
    }

    result = format_duration_anomalies(best, config)

    assert result is None


def test_duration_anomalies_multiple_dates():
    config = _make_bot_config(
        nights=(12, 13),
        strong_diff_rub=5000,
        strong_diff_percent=5,
    )
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, price_rub=250000),
            13: _make_offer("14.09.2026", 13, price_rub=220000),
        },
        "15.09.2026": {
            12: _make_offer("15.09.2026", 12, price_rub=200000),
            13: _make_offer("15.09.2026", 13, price_rub=180000),
        },
    }

    result = format_duration_anomalies(best, config)

    assert result is not None
    assert "14.09.2026" in result
    assert "15.09.2026" in result
    assert result.count("13н дешевле 12н") == 2


def test_format_report_includes_anomaly_section():
    config = _make_bot_config(
        nights=(12, 13),
        strong_diff_rub=5000,
        strong_diff_percent=5,
    )
    best = {
        "14.09.2026": {
            12: _make_offer("14.09.2026", 12, "A", 250000),
            13: _make_offer("14.09.2026", 13, "B", 220000),
        },
    }

    report = format_report(best, config, "Test")

    assert "Аномалии длительности" in report
    assert "13н дешевле 12н" in report


def test_anomaly_preset_applied_in_effective_config():
    """Verify anomaly preset overrides strong_diff_rub and strong_diff_percent."""
    config = _make_bot_config(
        anomaly_preset="conservative",
        strong_diff_rub=20000,
        strong_diff_percent=7.0,
    )
    save_runtime_settings(config, {"anomaly_preset": "aggressive"})
    effective = effective_config(config)
    assert effective.anomaly_preset == "aggressive"
    assert effective.strong_diff_rub == 10000
    assert effective.strong_diff_percent == 4.0


def test_anomaly_preset_ignores_invalid_name():
    config = _make_bot_config(anomaly_preset="balanced")
    save_runtime_settings(config, {"anomaly_preset": "nonexistent"})
    effective = effective_config(config)
    assert effective.strong_diff_rub == 20000
    assert effective.strong_diff_percent == 7.0


def test_format_trend_report_no_data(tmp_path: Path):
    """Trend report returns placeholder when no history exists."""
    from price_monitor import storage
    db_path = tmp_path / "test_trend_empty.sqlite3"
    storage.initialize_storage(db_path)
    report = format_trend_report(db_path)
    assert "Нет данных" in report


def test_format_trend_report_with_data(tmp_path: Path):
    """Trend report includes price direction for each group."""
    from price_monitor import storage
    db_path = tmp_path / "test_trend_data.sqlite3"
    storage.initialize_storage(db_path)
    snap = {
        "Основной поиск|14.09.2026|12|Room": {
            "departure_date": "14.09.2026",
            "nights": 12,
            "price_rub": 280000,
        }
    }
    storage.append_price_history(db_path, snap, "2026-05-01T10:00")
    snap2 = {
        "Основной поиск|14.09.2026|12|Room": {
            "departure_date": "14.09.2026",
            "nights": 12,
            "price_rub": 260000,
        }
    }
    storage.append_price_history(db_path, snap2, "2026-05-03T10:00")
    report = format_trend_report(db_path)
    assert "↓" in report
    assert "260 000" in report


def test_prune_price_history_removes_old_rows(tmp_path: Path):
    """Prune deletes rows older than retention_days."""
    from datetime import datetime, timedelta, timezone
    from price_monitor import storage
    db_path = tmp_path / "test_prune.sqlite3"
    storage.initialize_storage(db_path)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat(timespec="seconds")
    recent_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snap = {"test|1": {"departure_date": "01.01.2026", "nights": 12, "price_rub": 1000}}
    # Direct SQL insert for old row
    with storage._connection(db_path) as con:
        con.execute(
            "INSERT INTO price_history(snapshot_key, target_name, provider, departure_date, nights, price_rub, observed_at, payload_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("test|1", "test", "test", "01.01.2026", 12, 1000, old_ts, "{}"),
        )
    storage.append_price_history(db_path, snap, recent_ts)
    deleted = storage.prune_price_history(db_path, retention_days=90)
    assert deleted >= 1
    remaining = storage.load_price_history(db_path)
    for entries in remaining.values():
        for entry in entries:
            assert entry[0] == recent_ts


def test_retention_setting_in_effective_config():
    """Retention days from runtime settings override env default."""
    config = _make_bot_config(price_history_retention_days=90)
    save_runtime_settings(config, {"price_history_retention_days": 30})
    effective = effective_config(config)
    assert effective.price_history_retention_days == 30


def test_anomaly_presets_valid():
    """Verify all three presets have valid thresholds."""
    assert set(ANOMALY_PRESETS.keys()) == {"conservative", "balanced", "aggressive"}
    for preset in ANOMALY_PRESETS.values():
        assert preset["strong_diff_rub"] > 0
        assert preset["strong_diff_percent"] > 0


def test_format_trend_report_direction_stable(tmp_path: Path):
    """Stable prices show стабильно."""
    from price_monitor import storage
    db_path = tmp_path / "test_trend_stable.sqlite3"
    storage.initialize_storage(db_path)
    snap = {"t|d|12|r": {"departure_date": "d", "nights": 12, "price_rub": 100000}}
    storage.append_price_history(db_path, snap, "2026-05-01T10:00")
    storage.append_price_history(db_path, snap, "2026-05-03T10:00")
    report = format_trend_report(db_path)
    assert "стабильно" in report
