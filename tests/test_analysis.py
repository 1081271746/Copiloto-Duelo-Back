import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.ai.groq import GroqAnalyzer, SYSTEM_INSTRUCTION
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
    app.state.settings = replace(settings, groq_key="mock-only")
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


def test_missing_groq_does_not_break_diary(client, user):
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
    (401, "gemini_access_denied"), (400, "gemini_unavailable"), (302, "gemini_unavailable"),
])
async def test_groq_http_errors(settings, status, code):
    transport = httpx.MockTransport(lambda request: httpx.Response(
        status, json={"error": {"message": "private provider diagnostic"}}))
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), transport)
    with pytest.raises(ServiceError) as error:
        await analyzer.analyze("Private content", [])
    assert error.value.code == code
    assert error.value.status_code == (429 if status == 429 else 503)
    assert "private" not in str(error.value)


async def test_groq_timeout(settings):
    def fail(request):
        raise httpx.ReadTimeout("timeout")
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(fail))
    with pytest.raises(ServiceError, match="gemini_timeout"):
        await analyzer.analyze("content", [])


@pytest.mark.parametrize("body", [
    {}, {"choices": []},
    {"choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}]},
])
async def test_groq_invalid_responses(settings, body):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"),
                              httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(ServiceError):
        await analyzer.analyze("content", [])


async def test_groq_valid_response(settings):
    def respond(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer mock-only"
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-oss-120b"
        assert payload["response_format"] == {
            "type": "json_schema", "json_schema": {
                "name": "grief_analysis", "strict": True, "schema": AnalysisResult.model_json_schema(),
            },
        }
        assert payload["messages"][0] == {"role": "system", "content": SYSTEM_INSTRUCTION}
        assert json.loads(payload["messages"][1]["content"]) == {
            "current_entry": "Recuerdo ficticio", "previous_entries": [{"content": "Antes"}],
        }
        assert payload["max_completion_tokens"] == 4096
        assert payload["stream"] is False
        assert "tools" not in payload
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(RESULT)}}]})
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(respond))
    result = await analyzer.analyze("Recuerdo ficticio", [{"content": "Antes"}])
    assert result.risk_level == "none"
    assert result.model_dump(mode="json") == RESULT


@pytest.mark.parametrize("body", [
    [], None, {"choices": "wrong"}, {"choices": [None]},
    {"choices": [{"finish_reason": "stop", "message": []}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": [None]}}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": 17}}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "user", "content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": None}}]},
    {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "  "}}]},
    {"choices": [{"finish_reason": "stop"}, {"finish_reason": "stop"}]},
])
async def test_malformed_provider_envelopes_return_controlled_errors(settings, body):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"),
        httpx.MockTransport(lambda request: httpx.Response(200, content=json.dumps(body))))
    with pytest.raises(ServiceError, match="gemini_invalid_response"):
        await analyzer.analyze("entry", [])


async def test_groq_response_is_bounded_while_streaming(settings):
    class LargeResponse(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield b" " * 110000
            raise AssertionError("Oversized responses must not be read to completion")

        async def aclose(self):
            self.closed = True

    stream = LargeResponse()
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, stream=stream)))
    with pytest.raises(ServiceError, match="gemini_invalid_response"):
        await analyzer.analyze("entry", [])
    assert stream.closed


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.RemoteProtocolError])
async def test_provider_network_errors_do_not_expose_details(settings, failure):
    def disconnect(request):
        raise failure("private provider diagnostic")
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(disconnect))
    with pytest.raises(ServiceError) as error:
        await analyzer.analyze("sensitive fictional journal", [])
    assert error.value.code == "gemini_unavailable"
    assert "private" not in str(error.value)


async def test_safety_blocked_provider_response_is_not_fabricated(settings):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "content_filter",
            "message": {"role": "assistant", "content": None}}]})))
    with pytest.raises(ServiceError) as error:
        await analyzer.analyze("entry", [])
    assert error.value.status_code == 502


async def test_groq_without_key_never_calls_provider(settings):
    def unexpected_request(request):
        raise AssertionError("No request is allowed without a key")
    analyzer = GroqAnalyzer(settings, httpx.MockTransport(unexpected_request))
    with pytest.raises(ServiceError, match="gemini_not_configured") as error:
        await analyzer.analyze("Fictional entry", [])
    assert error.value.status_code == 503


@pytest.mark.parametrize("body", [b"not JSON", b"\xff", b'{"choices":'])
async def test_groq_invalid_transport_json(settings, body):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, content=body)))
    with pytest.raises(ServiceError, match="gemini_invalid_response") as error:
        await analyzer.analyze("Fictional entry", [])
    assert error.value.status_code == 502


@pytest.mark.parametrize("output", ["{bad", "[]", "null", "{}", '{"summary":"Only one field"}'])
async def test_groq_invalid_analysis_json(settings, output):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": output}}]})))
    with pytest.raises(ServiceError, match="gemini_invalid_response"):
        await analyzer.analyze("Fictional entry", [])


@pytest.mark.parametrize("finish_reason", ["length", "content_filter", "tool_calls", None])
async def test_groq_rejects_incomplete_results_even_with_valid_content(settings, finish_reason):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": finish_reason,
            "message": {"role": "assistant", "content": json.dumps(RESULT)}}]})))
    with pytest.raises(ServiceError, match="gemini_incomplete_response"):
        await analyzer.analyze("Fictional entry", [])


@pytest.mark.parametrize("extra", [
    {"refusal": "private provider diagnostic"}, {"tool_calls": [{"id": "fictional-tool"}]},
    {"function_call": {"name": "forbidden"}},
])
async def test_groq_rejects_refusals_and_tool_requests(settings, extra):
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only"), httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(RESULT), **extra}}]})))
    with pytest.raises(ServiceError, match="gemini_incomplete_response"):
        await analyzer.analyze("Fictional entry", [])


@pytest.mark.parametrize(("model", "mode", "strict"), [
    ("openai/gpt-oss-20b", "json_schema", True),
    ("openai/gpt-oss-safeguard-20b", "json_schema", False),
    ("llama-3.3-70b-versatile", "json_object", None),
])
async def test_groq_structured_output_capabilities(settings, model, mode, strict):
    def respond(request):
        payload = json.loads(request.content)
        assert payload["model"] == model
        assert payload["response_format"]["type"] == mode
        if mode == "json_schema":
            assert payload["response_format"]["json_schema"]["strict"] is strict
        else:
            instruction = payload["messages"][0]["content"]
            assert instruction.startswith(SYSTEM_INSTRUCTION)
            assert json.loads(instruction.split("\nJSON Schema:\n", 1)[1]) == AnalysisResult.model_json_schema()
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(RESULT)}}]})
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only", groq_model=model),
                            httpx.MockTransport(respond))
    assert (await analyzer.analyze("Fictional entry", [])).risk_level == "none"


async def test_groq_total_timeout_bounds_slow_download_and_closes_stream(settings):
    import asyncio

    class SlowResponse(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield b" "
            await asyncio.sleep(1)
            yield b"{}"

        async def aclose(self):
            self.closed = True

    stream = SlowResponse()
    analyzer = GroqAnalyzer(replace(settings, groq_key="mock-only", groq_timeout=0.02),
                            httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)))
    with pytest.raises(ServiceError, match="gemini_timeout") as error:
        await analyzer.analyze("Fictional entry", [])
    assert error.value.status_code == 504
    assert stream.closed


def test_groq_client_integrates_with_analysis_endpoint(client, app, settings, user):
    app.state.settings = replace(settings, groq_key="mock-only")
    app.state.analyzer = GroqAnalyzer(app.state.settings, httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(RESULT)}}]})))
    entry_id = create_entry(client, user).json()["entry"]["id"]
    response = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"])
    assert response.status_code == 201, response.text
    assert response.json()["analysis"]["model"] == "openai/gpt-oss-120b"
    assert response.json()["analysis"]["result"] == RESULT
    assert response.json()["recommendations"]


@pytest.mark.parametrize(("status", "code", "public_status"), [
    (401, "gemini_access_denied", 503), (403, "gemini_access_denied", 503),
    (429, "gemini_quota_exceeded", 429), (500, "gemini_unavailable", 503),
])
def test_groq_endpoint_errors_preserve_contract_and_release_lock(client, app, settings, user, status, code, public_status):
    app.state.settings = replace(settings, groq_key="mock-only")
    app.state.analyzer = GroqAnalyzer(app.state.settings, httpx.MockTransport(
        lambda request: httpx.Response(status, json={"error": {"message": "private diagnostic"}})))
    entry_id = create_entry(client, user).json()["entry"]["id"]
    for _ in range(2):
        response = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"])
        assert response.status_code == public_status
        assert response.json() == {"detail": code}
        if status == 429:
            assert response.headers["Retry-After"] == "60"
    assert client.get(f"/api/journal/{entry_id}/analyses", headers=user["headers"]).json() == []


@pytest.mark.parametrize("change", [
    {"emotions": []}, {"emotions": ["x" * 501]}, {"risk_level": "diagnosis"},
    {"unexpected": "database command"},
    {"categories": [{"category": "unknown", "confidence": 0.5, "rationale": "Test"}]},
    {"categories": [{"category": "anger", "confidence": 1.1, "rationale": "Test"}]},
    {"categories": [{"category": "anger", "confidence": float("nan"), "rationale": "Test"}]},
    {"recommended_categories": ["unlisted"]},
])
def test_analysis_contract_rejects_uncontrolled_values(change):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({**RESULT, **change})
