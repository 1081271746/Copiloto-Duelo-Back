from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.ai.gemini import GeminiAnalyzer
from app.core.errors import ServiceError
from app.schemas.analysis import AnalysisResult
from tests.test_journal import create_entry


RESULT = {
    "emotions": ["tristeza"], "categories": [
        {"category": "acceptance", "confidence": 0.4, "rationale": "Expresa un recuerdo significativo."}],
    "summary": "Conviven recuerdos y tristeza.", "patterns": [],
    "recommended_categories": ["acceptance"], "risk_level": "none",
}


def configure_analyzer(app, settings, result=None):
    app.state.settings = replace(settings, gemini_key="mock-only")
    app.state.analyzer = AsyncMock()
    app.state.analyzer.analyze.return_value = AnalysisResult.model_validate(result or RESULT)


def test_analysis_history_recommendations_and_isolation(client, app, settings, user, other_user):
    configure_analyzer(app, settings)
    entry_id = create_entry(client, user).json()["entry"]["id"]
    response = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"])
    assert response.status_code == 201, response.text
    output = response.json()
    analysis_id = output["analysis"]["id"]
    assert output["recommendations"]
    assert client.get(f"/api/journal/{entry_id}/analyses", headers=user["headers"]).json()[0]["id"] == analysis_id
    assert client.get(f"/api/analyses/{analysis_id}", headers=other_user["headers"]).status_code == 404
    assert client.get("/api/analyses", headers=other_user["headers"]).json() == []
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=other_user["headers"]).status_code == 404
    client.patch(f"/api/journal/{entry_id}", headers=user["headers"], json={"content": "Nueva versión"})
    assert client.get("/api/recommendations", headers=user["headers"]).json()["reason"] == "analysis_outdated"
    assert len(client.get("/api/analyses", headers=user["headers"]).json()) == 1
    assert client.delete(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 204
    assert client.get("/api/analyses", headers=user["headers"]).json() == []


def test_missing_gemini_does_not_break_diary(client, user):
    entry_id = create_entry(client, user).json()["entry"]["id"]
    response = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"])
    assert response.status_code == 503
    assert response.json()["detail"] == "gemini_not_configured"
    assert client.get(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 200


def test_ai_risk_suppresses_exercises(client, app, settings, user):
    configure_analyzer(app, settings, {**RESULT, "risk_level": "high"})
    entry_id = create_entry(client, user).json()["entry"]["id"]
    output = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).json()
    assert output["recommendations"] == []
    assert output["safety_alert"]["source"] == "ai"
    assert output["analysis"]["result"]["recommended_categories"] == []
    assert client.get("/api/recommendations", headers=user["headers"]).json()["reason"] == "safety_priority"


def test_ai_cannot_lower_rule_risk(client, app, settings, user):
    configure_analyzer(app, settings)
    entry_id = create_entry(client, user, "Quiero morir").json()["entry"]["id"]
    output = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).json()
    assert output["analysis"]["result"]["risk_level"] == "high"
    assert output["recommendations"] == []


def test_analysis_daily_limit(client, app, settings, user):
    configure_analyzer(app, replace(settings, daily_limit=1))
    entry_id = create_entry(client, user).json()["entry"]["id"]
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).status_code == 201
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).status_code == 429


@pytest.mark.parametrize(("status", "code"), [
    (429, "gemini_quota_exceeded"), (500, "gemini_unavailable"), (403, "gemini_access_denied"),
])
async def test_gemini_http_errors(settings, status, code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={}))
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"), transport)
    with pytest.raises(ServiceError) as error:
        await analyzer.analyze("Private content", [])
    assert error.value.code == code


async def test_gemini_timeout(settings):
    def fail(request):
        raise httpx.ReadTimeout("timeout")
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"), httpx.MockTransport(fail))
    with pytest.raises(ServiceError, match="gemini_timeout"):
        await analyzer.analyze("content", [])


@pytest.mark.parametrize("body", [
    {}, {"candidates": []},
    {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]},
])
async def test_gemini_invalid_responses(settings, body):
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"),
                              httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(ServiceError):
        await analyzer.analyze("content", [])


async def test_gemini_valid_response(settings):
    import json
    def respond(request):
        assert request.headers["x-goog-api-key"] == "mock-only"
        assert "responseJsonSchema" in json.loads(request.content)["generationConfig"]
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
            "content": {"parts": [{"text": json.dumps(RESULT)}]}}]})
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"), httpx.MockTransport(respond))
    result = await analyzer.analyze("content", [])
    assert result.risk_level == "none"


@pytest.mark.parametrize("body", [
    [], None, {"candidates": "wrong"}, {"candidates": [None]},
    {"candidates": [{"finishReason": "STOP", "content": []}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": [None]}}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": 17}]}}]},
])
async def test_malformed_provider_envelopes_return_controlled_errors(settings, body):
    import json
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"),
        httpx.MockTransport(lambda request: httpx.Response(200, content=json.dumps(body))))
    with pytest.raises(ServiceError, match="gemini_invalid_response"):
        await analyzer.analyze("entry", [])


async def test_gemini_response_is_bounded_while_streaming(settings):
    class LargeResponse(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield b" " * 110000
            raise AssertionError("Oversized responses must not be read to completion")

        async def aclose(self):
            self.closed = True

    stream = LargeResponse()
    analyzer = GeminiAnalyzer(replace(settings, gemini_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, stream=stream)))
    with pytest.raises(ServiceError, match="gemini_invalid_response"):
        await analyzer.analyze("entry", [])
    assert stream.closed
