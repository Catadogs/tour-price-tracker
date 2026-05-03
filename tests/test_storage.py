from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from price_monitor import storage


def table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def metadata_value(db_path: Path, key: str) -> str | None:
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (key,),
        ).fetchone()
    return str(row[0]) if row else None


def test_initialize_storage_creates_schema_and_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "price_monitor.sqlite3"

    storage.initialize_storage(db_path)
    storage.initialize_storage(db_path)

    assert db_path.exists()
    assert {
        "metadata",
        "runtime_settings",
        "latest_snapshots",
        "price_history",
    }.issubset(table_names(db_path))
    assert metadata_value(db_path, "schema_version") == "1"


def test_initialize_storage_allows_missing_legacy_json(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"

    storage.initialize_storage(
        db_path,
        settings_path=tmp_path / "missing-settings.json",
        state_path=tmp_path / "missing-state.json",
        history_path=tmp_path / "missing-history.json",
    )

    assert metadata_value(db_path, "json_import_completed") == "1"


def test_import_legacy_settings_only_once(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"nights": [12, 13], "target_price_rub": 180000}),
        encoding="utf-8",
    )

    storage.initialize_storage(db_path, settings_path=settings_path)

    assert storage.load_runtime_settings(db_path) == {
        "nights": [12, 13],
        "target_price_rub": 180000,
    }

    storage.save_runtime_settings(db_path, {"nights": [14]})
    settings_path.write_text(
        json.dumps({"nights": [1], "target_price_rub": 1}),
        encoding="utf-8",
    )
    storage.initialize_storage(db_path, settings_path=settings_path)

    assert metadata_value(db_path, "json_import_completed") == "1"
    assert storage.load_runtime_settings(db_path) == {"nights": [14]}


def test_runtime_settings_round_trip_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    storage.initialize_storage(db_path)

    storage.save_runtime_settings(
        db_path,
        {
            "departure_from": "14.09.2026",
            "nights": [12, 13],
            "target_price_rub": None,
        },
    )

    assert storage.load_runtime_settings(db_path) == {
        "departure_from": "14.09.2026",
        "nights": [12, 13],
        "target_price_rub": None,
    }


def test_latest_snapshot_round_trip_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    current = {
        "Main search|14.09.2026|12|104610620518": {
            "departure_date": "14.09.2026",
            "nights": 12,
            "room": "SUPERIOR",
            "price_rub": 286230,
            "price_usd": 3542,
            "booking_url": "https://example.test/book",
            "hotel_option_id": "104610620518",
        },
        "Level search|external": {
            "provider": "Level.Travel",
            "hotel_name": "Jaz Makadi",
            "price_rub": 138920,
            "url": "https://level.travel/hotels/629-test",
        },
    }
    storage.initialize_storage(db_path)

    storage.save_snapshot(db_path, current)

    assert storage.load_snapshot(db_path) == current


def test_price_history_append_does_not_rewrite_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    snapshot = {
        "Main search|14.09.2026|12|104610620518": {
            "departure_date": "14.09.2026",
            "nights": 12,
            "price_rub": 286230,
            "room": "SUPERIOR",
            "booking_url": "https://example.test/book",
            "hotel_option_id": "104610620518",
        }
    }
    storage.initialize_storage(db_path)
    storage.save_snapshot(db_path, snapshot)

    storage.append_price_history(db_path, snapshot, "2026-05-03T10:00:00Z")
    storage.append_price_history(db_path, snapshot, "2026-05-03T11:00:00Z")

    assert storage.load_snapshot(db_path) == snapshot
    assert storage.load_price_history(db_path) == {
        "Main search|14.09.2026|12|104610620518": [
            ["2026-05-03T10:00:00Z", 286230],
            ["2026-05-03T11:00:00Z", 286230],
        ]
    }


def test_legacy_snapshot_and_history_import(tmp_path: Path) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    state_path = tmp_path / "last_snapshot.json"
    history_path = tmp_path / "price_history.json"
    snapshot = {
        "Main search|14.09.2026|12|104610620518": {
            "departure_date": "14.09.2026",
            "nights": 12,
            "price_rub": 286230,
            "room": "SUPERIOR",
            "booking_url": "https://example.test/book",
            "hotel_option_id": "104610620518",
        }
    }
    history = {
        "Main search|14.09.2026|12|104610620518": [
            ["2026-05-03T10:00:00Z", 286230]
        ]
    }
    state_path.write_text(json.dumps(snapshot), encoding="utf-8")
    history_path.write_text(json.dumps(history), encoding="utf-8")

    storage.initialize_storage(db_path, state_path=state_path, history_path=history_path)

    assert storage.load_snapshot(db_path) == snapshot
    assert storage.load_price_history(db_path) == history


def test_malformed_legacy_json_logs_warning_and_completes(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_path = tmp_path / "price_monitor.sqlite3"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{bad json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        storage.initialize_storage(db_path, settings_path=settings_path)

    assert storage.load_runtime_settings(db_path) == {}
    assert metadata_value(db_path, "json_import_completed") == "1"
    assert "Skipping malformed legacy JSON" in caplog.text
