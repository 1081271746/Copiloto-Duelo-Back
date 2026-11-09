import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.errors import ServiceError
from app.services.events import RedisEventService
from app.websocket.manager import ConnectionManager
from tests.test_analysis import RESULT, configure_analyzer
from tests.test_journal import create_entry


async def test_subscriber_reconnects_after_real_redis_disconnect(settings):
    manager = ConnectionManager()
    service = RedisEventService(settings.redis_url, manager)
    socket = AsyncMock()
    socket.scope = {}
    await manager.connect("recovery-user", socket)
    await service.start()
    try:
        assert service.connected
        clients = await service.redis.client_list()
        subscriber_id = next(item["id"] for item in clients
                             if item["name"] == service.client_name and "P" in item["flags"])
        await service.redis.execute_command("CLIENT", "KILL", "ID", subscriber_id)
        for _ in range(200):
            if socket.close.await_count:
                break
            await asyncio.sleep(0.01)
        assert socket.close.await_count == 1
        await asyncio.wait_for(service.ready.wait(), timeout=5)
        reconnected = AsyncMock()
        reconnected.scope = {}
        await manager.connect("recovery-user", reconnected)
        assert await service.publish("recovery-user", "tracking.updated", {})
        for _ in range(100):
            if reconnected.send_text.await_count:
                break
            await asyncio.sleep(0.01)
        reconnected.send_text.assert_awaited_once()
    finally:
        await service.stop()


def test_journal_persists_when_event_publication_fails(client, app, user):
    app.state.events.publish = AsyncMock(return_value=False)
    response = create_entry(client, user)
    assert response.status_code == 201
    assert response.json()["realtime_delivered"] is False
    entry_id = response.json()["entry"]["id"]
    assert client.get(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 200


def test_completion_cannot_link_another_users_analysis(client, app, settings, user, other_user):
    configure_analyzer(app, settings)
    entry_id = create_entry(client, other_user).json()["entry"]["id"]
    analysis_id = client.post(f"/api/journal/{entry_id}/analyze", headers=other_user["headers"]).json()["analysis"]["id"]
    exercise_id = client.get("/api/exercises", headers=user["headers"]).json()[0]["id"]
    response = client.post(f"/api/exercises/{exercise_id}/complete", headers=user["headers"], json={"analysis_id": analysis_id})
    assert response.status_code == 404


def test_analysis_history_excludes_other_users_entries(client, app, settings, user, other_user):
    configure_analyzer(app, settings)
    create_entry(client, other_user, "Other user private text")
    create_entry(client, user, "My earlier reflection")
    entry_id = create_entry(client, user).json()["entry"]["id"]
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).status_code == 201
    history = app.state.analyzer.analyze.call_args.args[1]
    assert len(history) == 1
    assert history[0]["content"] == "My earlier reflection"


@pytest.mark.parametrize("body", [
    [], None, {"user_id": "other", "type": "tracking.updated", "data": {}},
    {"user_id": "user", "type": [], "data": {}},
    {"user_id": "user", "type": "tracking.updated", "data": []},
    {"user_id": "user", "type": "auth.session_revoked", "data": {}},
])
def test_invalid_internal_events_are_rejected(body):
    import json
    with pytest.raises(ValueError):
        RedisEventService.parse_event(json.dumps(body), "user")


async def test_bad_internal_event_does_not_stop_subscription(settings):
    import json
    manager = ConnectionManager()
    service = RedisEventService(settings.redis_url, manager)
    socket = AsyncMock()
    socket.scope = {}
    manager.register("event-user", socket)
    await service.start()
    try:
        await service.redis.publish("copilot:users:event-user", json.dumps({
            "user_id": "event-user", "type": "auth.session_revoked", "data": [],
        }))
        await service.publish("event-user", "tracking.updated", {})
        for _ in range(100):
            if socket.send_text.await_count:
                break
            await asyncio.sleep(0.01)
        assert service.connected
        socket.send_text.assert_awaited_once()
    finally:
        await service.stop()
