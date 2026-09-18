from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 2


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS eval_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    reference_answer TEXT NOT NULL,
                    expected_keywords TEXT NOT NULL,
                    source_title TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    expected_behavior TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    model TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    is_baseline INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_version_id INTEGER NOT NULL REFERENCES prompt_versions(id),
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    spent_cny REAL NOT NULL DEFAULT 0,
                    budget_cny REAL NOT NULL,
                    error_message TEXT
                );
                CREATE TABLE IF NOT EXISTS eval_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES eval_runs(id),
                    case_id INTEGER NOT NULL REFERENCES eval_cases(id),
                    output_text TEXT NOT NULL,
                    correctness_score REAL NOT NULL,
                    groundedness_score REAL NOT NULL,
                    task_completion_score REAL NOT NULL,
                    safety_pass INTEGER NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_cny REAL NOT NULL,
                    failure_category TEXT,
                    severity TEXT NOT NULL,
                    needs_review INTEGER NOT NULL,
                    review_status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(run_id, case_id)
                );
                CREATE TABLE IF NOT EXISTS human_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER NOT NULL REFERENCES eval_results(id),
                    decision TEXT NOT NULL,
                    correctness_score REAL,
                    groundedness_score REAL,
                    task_completion_score REAL,
                    failure_category TEXT,
                    severity TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    summary TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_results_run ON eval_results(run_id);
                CREATE INDEX IF NOT EXISTS idx_reviews_result ON human_reviews(result_id, id DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_action_created ON audit_events(action, id DESC);
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None


def decode_case(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["expected_keywords"] = json.loads(item["expected_keywords"])
    return item


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in ("is_baseline", "safety_pass", "needs_review"):
        if key in item:
            item[key] = bool(item[key])
    return item


def decode_audit_event(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    return item
