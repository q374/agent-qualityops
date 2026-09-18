from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def case_payload() -> dict:
    return {
        "external_id": "CASE-001",
        "title": "配置工具调用",
        "category": "operation",
        "input_text": "如何配置工具调用？",
        "reference_answer": "在工作流中添加工具节点，配置参数后先调试，再发布。",
        "expected_keywords": ["工具节点", "参数", "调试"],
        "source_title": "公开产品文档",
        "source_url": "https://example.com/docs/tools",
        "risk_level": "low",
        "expected_behavior": "answer",
    }


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "test.db", auto_seed_cases=False)
    with TestClient(app) as test_client:
        yield test_client


def import_one(client: TestClient, payload: dict) -> int:
    response = client.post("/api/cases/import", json={"cases": [payload]})
    assert response.status_code == 201, response.text
    return response.json()["case_ids"][0]
