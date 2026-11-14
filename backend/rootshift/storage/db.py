"""Persistence layer.

The running MVP keeps farms and rotations in memory for speed, but a restart used
to lose everything. This module writes them through to SQLite (stdlib, no server)
and hydrates them back on demand. The target schema is PostGIS (spec 12); the
repository interface is deliberately small so the swap stays contained.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS farm (
    id               TEXT PRIMARY KEY,
    demo_id          TEXT,
    session_id       TEXT,
    profile          TEXT NOT NULL,
    fixture_path     TEXT,
    boundary         TEXT,
    last_rotation_id TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rotation (
    id          TEXT PRIMARY KEY,
    farm_id     TEXT NOT NULL,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS rotation_farm_idx ON rotation (farm_id);
"""


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else config.db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # ------------------------------------------------------------------
    def save_farm(self, record: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO farm (id, demo_id, session_id, profile, fixture_path, boundary, last_rotation_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    demo_id = excluded.demo_id,
                    session_id = excluded.session_id,
                    profile = excluded.profile,
                    fixture_path = excluded.fixture_path,
                    boundary = excluded.boundary,
                    last_rotation_id = excluded.last_rotation_id
                """,
                (
                    record["farm_id"],
                    record.get("demo_id"),
                    record.get("session_id"),
                    json.dumps(record.get("profile") or {}, default=_json_default),
                    record.get("fixture_path"),
                    json.dumps(record.get("boundary"), default=_json_default) if record.get("boundary") else None,
                    record.get("last_rotation_id"),
                    record.get("created_at") or _now(),
                ),
            )

    def get_farm(self, farm_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM farm WHERE id = ?", (farm_id,)).fetchone()
        if row is None:
            return None
        return {
            "farm_id": row["id"],
            "demo_id": row["demo_id"],
            "session_id": row["session_id"],
            "profile": json.loads(row["profile"]),
            "fixture_path": row["fixture_path"],
            "boundary": json.loads(row["boundary"]) if row["boundary"] else None,
            "last_rotation_id": row["last_rotation_id"],
            "created_at": row["created_at"],
        }

    def set_last_rotation(self, farm_id: str, rotation_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE farm SET last_rotation_id = ? WHERE id = ?", (rotation_id, farm_id))

    def count_farms(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM farm").fetchone()[0])

    # ------------------------------------------------------------------
    def save_rotation(self, rotation_id: str, farm_id: str, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rotation (id, farm_id, payload, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                (rotation_id, farm_id, json.dumps(payload, default=_json_default), _now()),
            )

    def get_rotation(self, rotation_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM rotation WHERE id = ?", (rotation_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def count_rotations(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM rotation").fetchone()[0])

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM rotation")
            conn.execute("DELETE FROM farm")


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def reset_store(path: Path | str | None = None) -> Store:
    """Test hook: point the singleton at a different database."""
    global _store
    _store = Store(path)
    return _store
