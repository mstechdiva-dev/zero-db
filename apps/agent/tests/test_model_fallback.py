"""Zero picks Sonnet for high/critical changes and falls back across models on failure."""

import json

import pytest

from services.anthropic_service import AnthropicService
from zero.impact_analyzer import ImpactAnalyzer, STRONG_MODEL

GOOD = json.dumps({"affected_queries": [], "affected_services": [], "affected_indexes": [],
                   "summary": "ok", "next_action": "", "recommendations": []})
EVENT = {"id": "e1", "change_type": "column_dropped", "object_type": "column", "object_name": "x"}


def _analyzer(monkeypatch, behaviour):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    calls = []

    async def fake_chat(self, message, history, model=None):
        calls.append(model)
        return behaviour(model)

    monkeypatch.setattr(AnthropicService, "chat", fake_chat)
    return ImpactAnalyzer(agent_prompts={"zero": "Model: claude-haiku-5-5"}), calls


@pytest.mark.asyncio
async def test_low_risk_uses_haiku(monkeypatch):
    a, calls = _analyzer(monkeypatch, lambda m: GOOD)
    await a.analyze(EVENT, "low")
    assert calls == ["claude-haiku-5-5"]


@pytest.mark.asyncio
async def test_high_risk_uses_sonnet(monkeypatch):
    a, calls = _analyzer(monkeypatch, lambda m: GOOD)
    await a.analyze(EVENT, "high")
    assert calls == [STRONG_MODEL]


@pytest.mark.asyncio
async def test_haiku_failure_falls_back_to_sonnet(monkeypatch):
    def behaviour(model):
        if model == "claude-haiku-5-5":
            raise RuntimeError("model unavailable")
        return GOOD

    a, calls = _analyzer(monkeypatch, behaviour)
    result = await a.analyze(EVENT, "low")
    assert calls == ["claude-haiku-5-5", STRONG_MODEL]
    assert result["summary"] == "ok"


@pytest.mark.asyncio
async def test_both_fail_gives_canned_result(monkeypatch):
    def behaviour(model):
        raise RuntimeError("down")

    a, calls = _analyzer(monkeypatch, behaviour)
    result = await a.analyze(EVENT, "high")
    assert len(calls) == 2
    assert result.get("summary")
