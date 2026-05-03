from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1"

_WRITE_LOCK = threading.RLock()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_settings (
  key TEXT PRIMARY KEY,
  value_type TEXT NOT NULL,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS latest_snapshots (
  snapshot_key TEXT PRIMARY KEY,
  target_name TEXT NOT NULL,
  provider TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  nights INTEGER NOT NULL,
  offer_identity TEXT NOT NULL,
  price_rub INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_key TEXT NOT NULL,
  target_name TEXT NOT NULL,
  provider TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  nights INTEGER NOT NULL,
  price_rub INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_latest_snapshots_lookup
ON latest_snapshots(target_name, provider, departure_date, nights, observed_at);

CREATE INDEX IF NOT EXISTS idx_price_history_lookup
ON price_history(target_name, provider, departure_date, nights, observed_at);
"""


def initialize_storage(
    db_path: Path,
    *,
    settings_path: Path | None = None,
    state_path: Path | None = None,
    history_path: Path | None = None,
) -> None:
    del settings_path, state_path, history_path
    with _WRITE_LOCK:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with _connect(db_path) as con:
            con.executescript(_SCHEMA_SQL)
            _upsert_metadata(con, "schema_version", SCHEMA_VERSION)
            if _metadata_value(con, "json_import_completed") is None:
                _upsert_metadata(con, "json_import_completed", "1")


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


def _upsert_metadata(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        """
        INSERT INTO metadata(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (key, value, _utc_now()),
    )


def _metadata_value(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute(
        "SELECT value FROM metadata WHERE key = ?",
        (key,),
    ).fetchone()
    return str(row["value"]) if row else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
