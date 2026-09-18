# Agent QualityOps API contract

Base path: `/api`

## Core objects

- `EvalCase`: `id`, `external_id`, `title`, `category`, `input_text`, `reference_answer`, `expected_keywords`, `source_title`, `source_url`, `risk_level`, `expected_behavior`.
- `PromptVersion`: `id`, `name`, `model`, `system_prompt`, `temperature`, `is_baseline`.
- `EvalRun`: `id`, `prompt_version_id`, `status`, `mode`, `started_at`, `completed_at`, `spent_cny`, `error_message`.
- `EvalResult`: `id`, `run_id`, `case_id`, `output_text`, `correctness_score`, `groundedness_score`, `task_completion_score`, `safety_pass`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_cny`, `failure_category`, `severity`, `needs_review`, `review_status`.
- `HumanReview`: `id`, `result_id`, `decision`, `correctness_score`, `groundedness_score`, `task_completion_score`, `failure_category`, `severity`, `notes`, `reviewed_at`.
- `AuditEvent`: `id`, `action`, `entity_type`, `entity_id`, `summary`, `metadata`, `created_at`。`metadata` 只保存计数、状态、决策等最小必要信息，不保存 Prompt 正文、复核备注或密钥。

## Endpoints

- `GET /health`
- `GET /summary`
- `GET /cases`
- `POST /cases/import` with `{ "cases": EvalCaseInput[] }`
- `GET /versions`
- `POST /versions`
- `GET /runs`
- `POST /runs` with `{ "version_ids": number[], "case_ids"?: number[], "mode": "demo" | "deepseek", "budget_cny": number }`
- `GET /runs/{run_id}`
- `GET /compare?baseline_run_id=...&candidate_run_id=...`
- `GET /badcases?run_id=...`
- `POST /results/{result_id}/review`
- `GET /release-gates/{candidate_run_id}?baseline_run_id=...`
- `GET /reports/{run_id}`
- `GET /audit-events?action=...&entity_type=...&limit=100`，`limit` 范围为 1—200

## Release gate defaults

- High-risk safety failures: `0`
- Groundedness pass rate: `>= 90%`
- Task-completion pass rate: `>= 80%`
- Severe regressions versus baseline: `<= 3`

Real model keys are read from local environment variables only and are never returned by the API.
