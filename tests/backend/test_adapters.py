from __future__ import annotations

import json

import pytest

from backend.adapters import DeepSeekAdapter, InvalidModelResponse, ModelError


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(
            {
                "choices": [{"message": {"content": "最终回答"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
            ensure_ascii=False,
        ).encode("utf-8")


class EmptyContentResponse(FakeResponse):
    def read(self) -> bytes:
        return json.dumps(
            {
                "choices": [{"message": {"content": ""}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 800},
            }
        ).encode("utf-8")


def test_deepseek_disables_thinking_by_default(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("DEEPSEEK_THINKING_MODE", raising=False)
    monkeypatch.setattr("backend.adapters.urllib.request.urlopen", fake_urlopen)
    adapter = DeepSeekAdapter(timeout_seconds=12)

    response = adapter.generate(
        {
            "input_text": "如何配置？",
            "source_title": "公开文档",
            "source_url": "https://example.com/docs",
        },
        {
            "model": "deepseek-flash",
            "system_prompt": "基于资料回答。",
            "temperature": 0.1,
        },
    )

    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert captured["timeout"] == 12
    assert response.text == "最终回答"


def test_deepseek_rejects_invalid_thinking_mode(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_THINKING_MODE", "sometimes")

    with pytest.raises(ModelError, match="DEEPSEEK_THINKING_MODE"):
        DeepSeekAdapter()


def test_invalid_response_keeps_billable_usage(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.adapters.urllib.request.urlopen",
        lambda request, timeout: EmptyContentResponse(),
    )

    with pytest.raises(InvalidModelResponse) as caught:
        DeepSeekAdapter().generate(
            {
                "input_text": "如何配置？",
                "source_title": "公开文档",
                "source_url": "https://example.com/docs",
            },
            {
                "model": "deepseek-flash",
                "system_prompt": "基于资料回答。",
                "temperature": 0.1,
            },
        )

    assert caught.value.input_tokens == 12
    assert caught.value.output_tokens == 800
    assert caught.value.latency_ms >= 1
