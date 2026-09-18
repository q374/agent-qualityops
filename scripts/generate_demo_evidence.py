from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import create_app


OUTPUT = ROOT / "docs" / "DEMO_EVIDENCE.json"


def without_generated_at(value):
    """返回移除 generated_at 后的副本，用于比较证据语义是否变化。"""
    if isinstance(value, dict):
        return {
            key: without_generated_at(item)
            for key, item in value.items()
            if key != "generated_at"
        }
    if isinstance(value, list):
        return [without_generated_at(item) for item in value]
    return value


def preserve_timestamps_if_unchanged(existing, current):
    """语义未变化时复用已提交时间戳，避免验证命令污染工作区。"""
    if without_generated_at(existing) != without_generated_at(current):
        return current

    def merge(old, new):
        if isinstance(old, dict) and isinstance(new, dict):
            result = dict(new)
            if "generated_at" in old and "generated_at" in result:
                result["generated_at"] = old["generated_at"]
            for key in result.keys() & old.keys():
                if key != "generated_at":
                    result[key] = merge(old[key], result[key])
            return result
        if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
            return [merge(old_item, new_item) for old_item, new_item in zip(old, new)]
        return new

    return merge(existing, current)


def main() -> None:
    # Windows 上 SQLite/WAL 句柄可能被安全软件短暂占用；证据生成不应因此失败。
    with tempfile.TemporaryDirectory(dir=ROOT / "work", ignore_cleanup_errors=True) as temp_dir:
        app = create_app(Path(temp_dir) / "evidence.db")
        with TestClient(app) as client:
            cases = client.get("/api/cases").json()
            versions = client.get("/api/versions").json()
            run_response = client.post(
                "/api/runs",
                json={
                    "version_ids": [versions[0]["id"], versions[1]["id"]],
                    "mode": "demo",
                    "budget_cny": 5,
                },
            )
            run_response.raise_for_status()
            baseline_id, candidate_id = [item["id"] for item in run_response.json()["runs"]]
            comparison = client.get(
                "/api/compare",
                params={"baseline_run_id": baseline_id, "candidate_run_id": candidate_id},
            ).json()
            badcases_before = client.get("/api/badcases", params={"run_id": candidate_id}).json()

            reviewed_result = badcases_before[0]
            review_response = client.post(
                f"/api/results/{reviewed_result['id']}/review",
                json={
                    "decision": "pass",
                    "correctness_score": reviewed_result["effective_correctness_score"],
                    "groundedness_score": reviewed_result["effective_groundedness_score"],
                    "task_completion_score": reviewed_result["effective_task_completion_score"],
                    "severity": "none",
                    "notes": "离线演示复核：仅用于验证人工审核留痕和门禁重算。",
                },
            )
            review_response.raise_for_status()
            badcases_after = client.get("/api/badcases", params={"run_id": candidate_id}).json()
            gate = client.get(
                f"/api/release-gates/{candidate_id}", params={"baseline_run_id": baseline_id}
            ).json()

    evidence = {
        "artifact": "Agent QualityOps 可复现离线演示证据",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "结果来自确定性 Demo Provider 与公开资料衍生合成用例，不代表真实模型或企业线上质量。",
        "dataset": {"total": len(cases), "source_type": "公开文档与合成测试"},
        "versions": [
            {"id": item["id"], "name": item["name"], "model": item["model"]} for item in versions[:2]
        ],
        "run": {
            "mode": "demo",
            "baseline_run_id": baseline_id,
            "candidate_run_id": candidate_id,
            "spent_cny": run_response.json()["spent_cny"],
        },
        "comparison": {
            "matched_cases": comparison["matched_cases"],
            "severe_regressions": comparison["severe_regressions"],
            "baseline_metrics": comparison["baseline_metrics"],
            "candidate_metrics": comparison["candidate_metrics"],
        },
        "human_review": {
            "reviewed_result_id": reviewed_result["id"],
            "badcases_before": len(badcases_before),
            "badcases_after": len(badcases_after),
        },
        "release_gate": gate,
    }
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        evidence = preserve_timestamps_if_unchanged(existing, evidence)
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已生成 {OUTPUT}")


if __name__ == "__main__":
    (ROOT / "work").mkdir(exist_ok=True)
    main()
