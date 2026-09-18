from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from tests.backend.conftest import import_one


def test_audit_timeline_records_quality_operations_without_sensitive_content(
    client: TestClient, case_payload: dict
) -> None:
    case_id = import_one(client, case_payload)
    version_response = client.post(
        "/api/versions",
        json={
            "name": "Audit Candidate",
            "model": "deepseek-flash",
            "system_prompt": "仅依据资料回答。",
            "temperature": 0.1,
            "is_baseline": False,
        },
    )
    assert version_response.status_code == 201
    version_id = version_response.json()["id"]

    run_response = client.post(
        "/api/runs",
        json={
            "version_ids": [version_id],
            "case_ids": [case_id],
            "mode": "demo",
            "budget_cny": 5,
        },
    )
    assert run_response.status_code == 201
    run_id = run_response.json()["runs"][0]["id"]
    result_id = client.get(f"/api/runs/{run_id}").json()["results"][0]["id"]

    review_response = client.post(
        f"/api/results/{result_id}/review",
        json={
            "decision": "pass",
            "correctness_score": 100,
            "groundedness_score": 100,
            "task_completion_score": 100,
            "notes": "仅供内部复核，不应进入审计摘要。",
        },
    )
    assert review_response.status_code == 201
    gate_response = client.get(f"/api/release-gates/{run_id}")
    assert gate_response.status_code == 200

    response = client.get("/api/audit-events", params={"limit": 100})
    assert response.status_code == 200
    events = response.json()
    actions = {event["action"] for event in events}
    assert {
        "cases.imported",
        "version.created",
        "run.completed",
        "review.submitted",
        "gate.evaluated",
    } <= actions
    assert [event["id"] for event in events] == sorted(
        [event["id"] for event in events], reverse=True
    )
    assert all(
        datetime.fromisoformat(event["created_at"]).tzinfo is not None for event in events
    )

    serialized = str(events)
    assert "仅供内部复核" not in serialized
    assert "仅依据资料回答" not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized

    filtered = client.get(
        "/api/audit-events", params={"action": "review.submitted", "limit": 10}
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["metadata"]["decision"] == "pass"


def test_audit_timeline_validates_limit(client: TestClient) -> None:
    response = client.get("/api/audit-events", params={"limit": 201})
    assert response.status_code == 422
