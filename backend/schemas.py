from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Category = Literal[
    "operation",
    "troubleshooting",
    "ambiguous",
    "out_of_scope",
    "prompt_injection",
]
RiskLevel = Literal["low", "medium", "high"]


class EvalCaseInput(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    category: Category
    input_text: str = Field(min_length=1, max_length=20_000)
    reference_answer: str = Field(min_length=1, max_length=30_000)
    expected_keywords: list[str] = Field(default_factory=list, max_length=30)
    source_title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=1, max_length=2_000)
    risk_level: RiskLevel
    expected_behavior: str = Field(min_length=1, max_length=100)

    @field_validator("external_id", "title", "input_text", "reference_answer", "source_title", "source_url", "expected_behavior")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("source_url 必须是 http 或 https 地址")
        return value

    @field_validator("expected_keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("expected_keywords 不能重复")
        return cleaned


class CasesImport(BaseModel):
    cases: list[EvalCaseInput] = Field(min_length=1, max_length=1_000)


class PromptVersionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    system_prompt: str = Field(min_length=1, max_length=20_000)
    temperature: float = Field(default=0.1, ge=0, le=2)
    is_baseline: bool = False


class RunCreate(BaseModel):
    version_ids: list[int] = Field(min_length=1, max_length=10)
    case_ids: list[int] | None = Field(default=None, min_length=1, max_length=1_000)
    mode: Literal["demo", "deepseek"] = "demo"
    budget_cny: float = Field(default=5.0, gt=0, le=5.0)

    @field_validator("version_ids", "case_ids")
    @classmethod
    def unique_ids(cls, values: list[int] | None) -> list[int] | None:
        if values is not None and (any(item <= 0 for item in values) or len(values) != len(set(values))):
            raise ValueError("ID 必须为不重复的正整数")
        return values


class HumanReviewInput(BaseModel):
    decision: Literal["pass", "fail"]
    correctness_score: float | None = Field(default=None, ge=0, le=100)
    groundedness_score: float | None = Field(default=None, ge=0, le=100)
    task_completion_score: float | None = Field(default=None, ge=0, le=100)
    failure_category: str | None = Field(default=None, max_length=100)
    severity: Literal["none", "low", "medium", "high", "critical"] | None = None
    notes: str = Field(default="", max_length=5_000)

    model_config = ConfigDict(extra="forbid")
