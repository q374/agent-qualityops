from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.config import load_local_env
from backend.main import create_app


def test_load_local_env_without_overriding_existing_values(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DEEPSEEK_API_KEY=loaded-from-file\nDEEPSEEK_MODEL=deepseek-flash\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_MODEL", "existing-model")

    loaded = load_local_env(env_file)

    assert loaded is True
    assert os.environ["DEEPSEEK_API_KEY"] == "loaded-from-file"
    assert os.environ["DEEPSEEK_MODEL"] == "existing-model"


def test_health_only_exposes_deepseek_configuration_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-for-test")
    app = create_app(tmp_path / "config.db", auto_seed_cases=False)

    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json()["deepseek_configured"] is True
    assert "secret-for-test" not in health.text
