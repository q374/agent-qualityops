from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .adapters import ModelAdapter, ModelError
from .database import Database
from .evaluator import Judge
from .schemas import CasesImport, HumanReviewInput, PromptVersionInput, RunCreate
from .service import BadRequestError, ConflictError, NotFoundError, QualityOpsService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_app(
    database_path: str | Path | None = None,
    *,
    adapter_factory: Callable[[str], ModelAdapter] | None = None,
    judge: Judge | None = None,
    auto_seed_cases: bool = True,
) -> FastAPI:
    db_path = database_path or os.getenv("QUALITYOPS_DB_PATH") or PROJECT_ROOT / "backend" / "qualityops.db"
    database = Database(db_path)
    database.initialize()
    service = QualityOpsService(database, adapter_factory=adapter_factory, judge=judge)
    service.seed_versions()
    seed_file = PROJECT_ROOT / "data" / "eval_cases.json"
    if auto_seed_cases and seed_file.exists() and not service.list_cases():
        service.import_cases_file(seed_file)

    application = FastAPI(
        title="Agent QualityOps API",
        version="0.1.0",
        description="企业智能体评测与质量运营平台 MVP。演示数据为公开资料与合成用例。",
    )
    application.state.service = service
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in os.getenv("QUALITYOPS_CORS_ORIGINS", "http://localhost:5173").split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def call(action: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            return action(*args, **kwargs)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (BadRequestError, ModelError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": "ready"}

    @application.get("/api/summary")
    def summary() -> dict[str, Any]:
        return service.summary()

    @application.get("/api/cases")
    def list_cases() -> list[dict[str, Any]]:
        return service.list_cases()

    @application.post("/api/cases/import", status_code=201)
    def import_cases(payload: CasesImport) -> dict[str, Any]:
        return call(service.import_cases, payload.cases)

    @application.get("/api/versions")
    def list_versions() -> list[dict[str, Any]]:
        return service.list_versions()

    @application.post("/api/versions", status_code=201)
    def create_version(payload: PromptVersionInput) -> dict[str, Any]:
        return call(service.create_version, payload)

    @application.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return service.list_runs()

    @application.post("/api/runs", status_code=201)
    def create_runs(payload: RunCreate) -> dict[str, Any]:
        return call(service.run_versions, payload.version_ids, payload.case_ids, payload.mode, payload.budget_cny)

    @application.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        return call(service.get_run, run_id)

    @application.get("/api/compare")
    def compare(baseline_run_id: int = Query(gt=0), candidate_run_id: int = Query(gt=0)) -> dict[str, Any]:
        return call(service.compare, baseline_run_id, candidate_run_id)

    @application.get("/api/badcases")
    def badcases(run_id: int = Query(gt=0)) -> list[dict[str, Any]]:
        return call(service.badcases, run_id)

    @application.post("/api/results/{result_id}/review", status_code=201)
    def review(result_id: int, payload: HumanReviewInput) -> dict[str, Any]:
        return call(service.review_result, result_id, payload)

    @application.get("/api/release-gates/{candidate_run_id}")
    def release_gate(candidate_run_id: int, baseline_run_id: int | None = Query(default=None, gt=0)) -> dict[str, Any]:
        return call(service.release_gate, candidate_run_id, baseline_run_id)

    @application.get("/api/reports/{run_id}")
    def report(run_id: int) -> dict[str, Any]:
        return call(service.report, run_id)

    return application


app = create_app()
