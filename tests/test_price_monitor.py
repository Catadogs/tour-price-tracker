from pathlib import Path

from price_monitor.monitor import (
    MonitorConfig,
    best_by_departure_and_nights,
    escape_markdown_v2,
    initialize_storage,
    extract_hotel_name,
    filter_offers,
    format_strong_diff_line,
    format_interval,
    load_price_history,
    load_runtime_settings,
    load_snapshot,
    parse_external_price,
    parse_date_range_text,
    parse_diff_text,
    parse_interval_text,
    normalize_search_url,
    parse_offers,
    run_check,
    save_runtime_settings,
    save_snapshot,
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
