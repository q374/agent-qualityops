from __future__ import annotations

import sqlite3

from backend.database import Database, SCHEMA_VERSION


def test_v2_database_migrates_evidence_text(tmp_path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE eval_cases (
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
            )"""
        )
        conn.execute(
            """INSERT INTO eval_cases
               (external_id, title, category, input_text, reference_answer,
                expected_keywords, source_title, source_url, risk_level, expected_behavior)
               VALUES ('LEGACY-1', '旧用例', 'operation', '问题', '公开资料答案', '[]',
                       '资料', 'https://example.com', 'low', 'answer')"""
        )

    database = Database(path)
    database.initialize()

    row = database.fetch_one(
        "SELECT evidence_text FROM eval_cases WHERE external_id = 'LEGACY-1'"
    )
    version = database.fetch_one(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    )
    assert row == {"evidence_text": "公开资料答案"}
    assert version == {"value": str(SCHEMA_VERSION)}
