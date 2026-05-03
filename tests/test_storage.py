from __future__ import annotations

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
