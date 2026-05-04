from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


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

CREATE TABLE IF NOT EXISTS currency_observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair TEXT NOT NULL,
  rate REAL NOT NULL,
  observed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_currency_observations_lookup
ON currency_observations(pair, observed_at);
"""


def initialize_storage(
    db_path: Path,
    *,
    settings_path: Path | None = None,
    state_path: Path | None = None,
    history_path: Path | None = None,
) -> None:
    with _WRITE_LOCK:
        try:
            _raise_if_not_sqlite_file(db_path)
            _initialize_storage(
                db_path,
                settings_path=settings_path,
                state_path=state_path,
                history_path=history_path,
            )
        except (sqlite3.DatabaseError, sqlite3.OperationalError):
            if not db_path.exists():
                raise
            quarantined = _quarantine_database(db_path)
            logging.warning(
                "Corrupt SQLite database at %s quarantined as %s; replacement database initialized at %s",
                db_path,
                ", ".join(str(path) for path in quarantined),
                db_path,
            )
            _initialize_storage(
                db_path,
                settings_path=settings_path,
                state_path=state_path,
                history_path=history_path,
            )


def load_runtime_settings(db_path: Path) -> dict[str, object]:
    with _connection(db_path) as con:
        rows = con.execute(
            "SELECT key, value_json FROM runtime_settings ORDER BY key"
        ).fetchall()
    return {str(row["key"]): json.loads(str(row["value_json"])) for row in rows}


def save_runtime_settings(db_path: Path, settings: dict[str, object]) -> None:
    with _WRITE_LOCK:
        with _connection(db_path) as con:
            _save_runtime_settings(con, settings)


def load_snapshot(db_path: Path) -> dict[str, dict[str, object]]:
    with _connection(db_path) as con:
        rows = con.execute(
            "SELECT snapshot_key, payload_json FROM latest_snapshots ORDER BY snapshot_key"
        ).fetchall()
    return {
        str(row["snapshot_key"]): json.loads(str(row["payload_json"]))
        for row in rows
    }


def save_snapshot(db_path: Path, data: dict[str, dict[str, object]]) -> None:
    with _WRITE_LOCK:
        with _connection(db_path) as con:
            _save_snapshot(con, data)


def load_price_history(db_path: Path) -> dict[str, list[list]]:
    history: dict[str, list[list]] = {}
    with _connection(db_path) as con:
        rows = con.execute(
            """
            SELECT snapshot_key, observed_at, price_rub
            FROM price_history
            ORDER BY id
            """
        ).fetchall()
    for row in rows:
        key = str(row["snapshot_key"])
        history.setdefault(key, []).append(
            [str(row["observed_at"]), int(row["price_rub"])]
        )
    return history


def append_price_history(
    db_path: Path,
    current_snapshot: dict[str, dict[str, object]],
    observed_at: str,
) -> None:
    with _WRITE_LOCK:
        with _connection(db_path) as con:
            _append_price_history(con, current_snapshot, observed_at)


def _initialize_storage(
    db_path: Path,
    *,
    settings_path: Path | None,
    state_path: Path | None,
    history_path: Path | None,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connection(db_path) as con:
        con.executescript(_SCHEMA_SQL)
        _verify_database(con)
        _upsert_metadata(con, "schema_version", SCHEMA_VERSION)
        if _metadata_value(con, "json_import_completed") is None:
            _import_legacy_json(
                con,
                settings_path=settings_path,
                state_path=state_path,
                history_path=history_path,
            )
            _upsert_metadata(con, "json_import_completed", "1")


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


def _raise_if_not_sqlite_file(db_path: Path) -> None:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return
    with db_path.open("rb") as file:
        header = file.read(16)
    if header != b"SQLite format 3\x00":
        raise sqlite3.DatabaseError(f"{db_path} is not a SQLite database")


@contextmanager
def _connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    con = _connect(db_path)
    try:
        with con:
            yield con
    finally:
        con.close()


def _verify_database(con: sqlite3.Connection) -> None:
    row = con.execute("PRAGMA quick_check").fetchone()
    result = str(row[0]) if row else ""
    if result.lower() != "ok":
        raise sqlite3.DatabaseError(f"SQLite quick_check failed: {result}")


def _quarantine_database(db_path: Path) -> list[Path]:
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    quarantined: list[Path] = []
    for path in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        if not path.exists():
            continue
        target = path.with_name(f"{path.name}.corrupt-{suffix}")
        path.rename(target)
        quarantined.append(target)
    return quarantined


def _import_legacy_json(
    con: sqlite3.Connection,
    *,
    settings_path: Path | None,
    state_path: Path | None,
    history_path: Path | None,
) -> None:
    settings = _load_legacy_json(settings_path, "runtime settings")
    if isinstance(settings, dict):
        _save_runtime_settings(con, settings)

    snapshot = _load_legacy_json(state_path, "latest snapshot")
    if isinstance(snapshot, dict):
        _save_snapshot(con, snapshot)

    history = _load_legacy_json(history_path, "price history")
    if isinstance(history, dict):
        _import_price_history(con, history)


def _load_legacy_json(path: Path | None, label: str) -> object | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logging.warning(
            "Skipping malformed legacy JSON for %s at %s: %s",
            label,
            path,
            exc,
        )
        return None


def _save_runtime_settings(
    con: sqlite3.Connection,
    settings: dict[str, object],
) -> None:
    now = _utc_now()
    con.execute("DELETE FROM runtime_settings")
    con.executemany(
        """
        INSERT INTO runtime_settings(key, value_type, value_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value_type = excluded.value_type,
          value_json = excluded.value_json,
          updated_at = excluded.updated_at
        """,
        [
            (
                str(key),
                type(value).__name__,
                json.dumps(value, ensure_ascii=False, sort_keys=True),
                now,
            )
            for key, value in settings.items()
        ],
    )


def _save_snapshot(
    con: sqlite3.Connection,
    data: dict[str, dict[str, object]],
) -> None:
    con.execute("DELETE FROM latest_snapshots")
    for snapshot_key, payload in data.items():
        row = _snapshot_row(snapshot_key, payload, _utc_now())
        if row is None:
            continue
        con.execute(
            """
            INSERT INTO latest_snapshots(
              snapshot_key, target_name, provider, departure_date, nights,
              offer_identity, price_rub, observed_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_key) DO UPDATE SET
              target_name = excluded.target_name,
              provider = excluded.provider,
              departure_date = excluded.departure_date,
              nights = excluded.nights,
              offer_identity = excluded.offer_identity,
              price_rub = excluded.price_rub,
              observed_at = excluded.observed_at,
              payload_json = excluded.payload_json
            """,
            row,
        )


def _append_price_history(
    con: sqlite3.Connection,
    current_snapshot: dict[str, dict[str, object]],
    observed_at: str,
) -> None:
    for snapshot_key, payload in current_snapshot.items():
        row = _history_row(snapshot_key, payload, observed_at)
        if row is None:
            continue
        con.execute(
            """
            INSERT INTO price_history(
              snapshot_key, target_name, provider, departure_date, nights,
              price_rub, observed_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )


def _import_price_history(
    con: sqlite3.Connection,
    history: dict[object, object],
) -> None:
    for raw_key, raw_entries in history.items():
        if not isinstance(raw_entries, list):
            continue
        for entry in raw_entries:
            if (
                not isinstance(entry, list)
                or len(entry) < 2
                or entry[0] is None
                or entry[1] is None
            ):
                continue
            snapshot_key = str(raw_key)
            observed_at = str(entry[0])
            payload = {
                "observed_at": observed_at,
                "price_rub": int(entry[1]),
            }
            row = _history_row(snapshot_key, payload, observed_at)
            if row is None:
                continue
            con.execute(
                """
                INSERT INTO price_history(
                  snapshot_key, target_name, provider, departure_date, nights,
                  price_rub, observed_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )


def _snapshot_row(
    snapshot_key: object,
    payload: dict[str, object],
    observed_at: str,
) -> tuple[str, str, str, str, int, str, int, str, str] | None:
    key = str(snapshot_key)
    price = payload.get("price_rub")
    if price is None:
        return None
    target_name, offer_identity = _split_snapshot_key(key)
    departure_date = str(payload.get("departure_date") or _key_part(key, 0) or "")
    nights = _coerce_int(payload.get("nights"), _key_part(key, 1), default=0)
    provider = _provider_for_key(key, payload)
    row_observed_at = str(payload.get("observed_at") or observed_at)
    return (
        key,
        target_name,
        provider,
        departure_date,
        nights,
        offer_identity,
        int(price),
        row_observed_at,
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
    )


def _history_row(
    snapshot_key: object,
    payload: dict[str, object],
    observed_at: str,
) -> tuple[str, str, str, str, int, int, str, str] | None:
    key = str(snapshot_key)
    price = payload.get("price_rub")
    if price is None:
        return None
    target_name, _offer_identity = _split_snapshot_key(key)
    departure_date = str(payload.get("departure_date") or _key_part(key, 0) or "")
    nights = _coerce_int(payload.get("nights"), _key_part(key, 1), default=0)
    provider = _provider_for_key(key, payload)
    return (
        key,
        target_name,
        provider,
        departure_date,
        nights,
        int(price),
        observed_at,
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
    )


def _split_snapshot_key(snapshot_key: str) -> tuple[str, str]:
    if "|" not in snapshot_key:
        return snapshot_key, snapshot_key
    target_name, offer_identity = snapshot_key.split("|", 1)
    return target_name, offer_identity


def _key_part(snapshot_key: str, index: int) -> str | None:
    _target_name, offer_identity = _split_snapshot_key(snapshot_key)
    parts = offer_identity.split("|")
    if index >= len(parts):
        return None
    return parts[index]


def _provider_for_key(snapshot_key: str, payload: dict[str, object]) -> str:
    provider = payload.get("provider")
    if provider:
        return str(provider)
    if snapshot_key.endswith("|external"):
        return "external"
    return "Biblio-Globus"


def _coerce_int(
    primary: object,
    secondary: object,
    *,
    default: int,
) -> int:
    for value in (primary, secondary):
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


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


def save_currency_observation(db_path: Path, pair: str, rate: float, observed_at: str) -> None:
    with _connection(db_path) as con:
        con.execute(
            "INSERT INTO currency_observations(pair, rate, observed_at) VALUES (?, ?, ?)",
            (pair, rate, observed_at),
        )


def load_currency_observations(
    db_path: Path,
    pair: str,
    limit: int = 2,
) -> list[tuple[str, float]]:
    """Return list of (observed_at, rate) tuples ordered by recency."""
    with _connection(db_path) as con:
        rows = con.execute(
            "SELECT observed_at, rate FROM currency_observations "
            "WHERE pair = ? ORDER BY observed_at DESC LIMIT ?",
            (pair, limit),
        ).fetchall()
    return [(row["observed_at"], row["rate"]) for row in rows]


def prune_price_history(db_path: Path, retention_days: int) -> int:
    """Delete price_history rows older than retention_days. Returns count of deleted rows."""
    with _WRITE_LOCK:
        with _connection(db_path) as con:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
            cursor = con.execute(
                "DELETE FROM price_history WHERE observed_at < ?",
                (cutoff,),
            )
            deleted = cursor.rowcount
            if deleted:
                logging.info("Pruned %d price_history rows older than %d days", deleted, retention_days)
            return deleted


def vacuum_db(db_path: Path) -> None:
    """Optimize and compact the database file."""
    with _WRITE_LOCK:
        with _connection(db_path) as con:
            con.execute("PRAGMA optimize")
            con.execute("VACUUM")


def load_price_history_grouped(
    db_path: Path,
) -> dict[str, dict[str, dict[int, list[tuple[str, int]]]]]:
    """Return price history grouped by target_name -> departure_date -> nights -> [(observed_at, price_rub), ...].

    Example: {"Основной поиск": {"14.09.2026": {12: [("2026-05-01T10:00", 280000), ...]}}}
    """
    grouped: dict[str, dict[str, dict[int, list[tuple[str, int]]]]] = {}
    with _connection(db_path) as con:
        rows = con.execute(
            """
            SELECT target_name, departure_date, nights, observed_at, price_rub
            FROM price_history
            ORDER BY target_name, departure_date, nights, observed_at
            """
        ).fetchall()
    for row in rows:
        target = str(row["target_name"])
        date = str(row["departure_date"])
        nights = int(row["nights"])
        ts = str(row["observed_at"])
        price = int(row["price_rub"])
        (grouped
            .setdefault(target, {})
            .setdefault(date, {})
            .setdefault(nights, [])
            .append((ts, price)))
    return grouped
