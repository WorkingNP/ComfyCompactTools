from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRow:
    id: str
    engine: str
    status: str
    prompt_id: Optional[str]
    prompt: str
    negative_prompt: str
    params_json: str
    created_at: str
    updated_at: str
    progress_value: float
    progress_max: float
    harvested: int
    error: Optional[str]


@dataclass
class AssetRow:
    id: str
    job_id: str
    engine: str
    filename: str
    created_at: str
    favorite: int
    recipe_json: str
    meta_json: str


@dataclass
class GrokMessageRow:
    id: int
    role: str
    content: str
    created_at: str


class Database:
    """Tiny SQLite wrapper (sync, protected by a lock).

    This MVP keeps it intentionally simple.
    """

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    engine TEXT NOT NULL,
                    status TEXT NOT NULL,
                    prompt_id TEXT,
                    prompt TEXT NOT NULL,
                    negative_prompt TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    progress_value REAL NOT NULL DEFAULT 0,
                    progress_max REAL NOT NULL DEFAULT 0,
                    harvested INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    recipe_json TEXT NOT NULL,
                    meta_json TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS grok_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_grok_messages_created_at ON grok_messages(created_at DESC);")
            self._conn.commit()

            # Lightweight migration: add 'harvested' column if the DB was created by an older version.
            try:
                cur.execute("ALTER TABLE jobs ADD COLUMN harvested INTEGER NOT NULL DEFAULT 0;")
                self._conn.commit()
            except Exception:
                pass

    # ---- Jobs ----

    def create_job(
        self,
        *,
        job_id: str,
        engine: str,
        status: str,
        prompt: str,
        negative_prompt: str,
        params: Dict[str, Any],
        prompt_id: Optional[str] = None,
    ) -> None:
        now = utc_now_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO jobs (id, engine, status, prompt_id, prompt, negative_prompt, params_json, created_at, updated_at, progress_value, progress_max, harvested, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, NULL);
                """,
                (job_id, engine, status, prompt_id, prompt, negative_prompt, json.dumps(params), now, now),
            )
            self._conn.commit()

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        prompt_id: Optional[str] = None,
        progress_value: Optional[float] = None,
        progress_max: Optional[float] = None,
        error: Optional[str] = None,
        harvested: Optional[int] = None,
    ) -> None:
        fields: List[str] = []
        values: List[Any] = []

        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if prompt_id is not None:
            fields.append("prompt_id = ?")
            values.append(prompt_id)
        if progress_value is not None:
            fields.append("progress_value = ?")
            values.append(progress_value)
        if progress_max is not None:
            fields.append("progress_max = ?")
            values.append(progress_max)
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if harvested is not None:
            fields.append("harvested = ?")
            values.append(int(harvested))

        if not fields:
            return

        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.append(job_id)

        sql = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?;"
        with self._lock:
            self._conn.execute(sql, tuple(values))
            self._conn.commit()

    def get_job(self, job_id: str) -> Optional[JobRow]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE id = ?;", (job_id,)).fetchone()
        return JobRow(**dict(row)) if row else None

    def get_job_by_prompt_id(self, prompt_id: str) -> Optional[JobRow]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE prompt_id = ?;", (prompt_id,)).fetchone()
        return JobRow(**dict(row)) if row else None

    def list_jobs(self, limit: int = 200) -> List[JobRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        return [JobRow(**dict(r)) for r in rows]

    # ---- Assets ----

    def create_asset(
        self,
        *,
        asset_id: str,
        job_id: str,
        engine: str,
        filename: str,
        recipe: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> None:
        now = utc_now_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO assets (id, job_id, engine, filename, created_at, favorite, recipe_json, meta_json)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?);
                """,
                (asset_id, job_id, engine, filename, now, json.dumps(recipe), json.dumps(meta)),
            )
            self._conn.commit()

    def list_assets(self, limit: int = 200) -> List[AssetRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM assets ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        return [AssetRow(**dict(r)) for r in rows]

    def get_asset(self, asset_id: str) -> Optional[AssetRow]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM assets WHERE id = ?;", (asset_id,)).fetchone()
        return AssetRow(**dict(row)) if row else None

    def toggle_favorite(self, asset_id: str) -> Optional[AssetRow]:
        with self._lock:
            row = self._conn.execute("SELECT favorite FROM assets WHERE id = ?;", (asset_id,)).fetchone()
            if not row:
                return None
            new_val = 0 if int(row[0]) == 1 else 1
            self._conn.execute("UPDATE assets SET favorite = ? WHERE id = ?;", (new_val, asset_id))
            self._conn.commit()

        return self.get_asset(asset_id)

    # ---- Grok messages ----

    def create_grok_message(self, *, role: str, content: str) -> GrokMessageRow:
        now = utc_now_iso()
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO grok_messages (role, content, created_at)
                VALUES (?, ?, ?);
                """,
                (role, content, now),
            )
            self._conn.commit()
            msg_id = int(cur.lastrowid)
        return GrokMessageRow(id=msg_id, role=role, content=content, created_at=now)

    def list_grok_messages(self, limit: Optional[int] = None) -> List[GrokMessageRow]:
        with self._lock:
            if limit and limit > 0:
                rows = self._conn.execute(
                    """
                    SELECT * FROM (
                        SELECT * FROM grok_messages ORDER BY id DESC LIMIT ?
                    ) ORDER BY id ASC;
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM grok_messages ORDER BY id ASC;").fetchall()
        return [GrokMessageRow(**dict(r)) for r in rows]

    def clear_grok_messages(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM grok_messages;")
            self._conn.commit()
