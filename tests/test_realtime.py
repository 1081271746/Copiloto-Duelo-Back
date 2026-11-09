import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.services.events import RedisEventService
from app.websocket.manager import ConnectionManager
from tests.test_journal import create_entry


def socket_auth(socket, user):
    socket.send_json({"type": "authenticate", "access_token": user["headers"]["Authorization"].split()[1]})
    assert socket.receive_json()["type"] == "ready"


def test_websocket_fanout_between_instances_and_private_channels(client, app, settings, user, other_user):
    second_app = create_app(settings)
    with TestClient(second_app) as second_client:
        with client.websocket_connect("/api/ws") as first, second_client.websocket_connect("/api/ws") as second, client.websocket_connect("/api/ws") as private:
            socket_auth(first, user)
            socket_auth(second, user)
            socket_auth(private, other_user)
            output = create_entry(client, user)
            event = first.receive_json()
            assert event["type"] == "journal.created"
            assert event["data"]["entry_id"] == output.json()["entry"]["id"]
            assert second.receive_json()["id"] == event["id"]
            private.send_json({"type": "ping"})
            assert private.receive_json() == {"type": "pong"}
    assert app.state.manager.connections == {}
    assert second_app.state.manager.connections == {}


def test_reject_invalid_token_and_origin(client):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws") as socket:
            socket.send_json({"type": "authenticate", "access_token": "x" * 30})
            socket.receive_json()
    assert error.value.code == 1008
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws", headers={"origin": "https://untrusted.example"}):
            pass


def test_reject_channel_subscription_and_revoked_token(client, user, other_user):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws") as socket:
            socket_auth(socket, user)
            socket.send_json({"type": "subscribe", "user_id": other_user["id"]})
            socket.receive_json()
    assert error.value.code == 1008
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws") as socket:
            socket_auth(socket, user)
            assert client.post("/api/auth/logout", headers=user["headers"]).status_code == 204
            socket.send_json({"type": "ping"})
            socket.receive_json()


def test_client_can_reconnect(client, user):
    for _ in range(2):
        with client.websocket_connect("/api/ws") as socket:
            socket_auth(socket, user)
            socket.send_json({"type": "ping"})
            assert socket.receive_json()["type"] == "pong"


async def test_redis_pubsub_real_cross_instance(settings):
    manager_one = ConnectionManager()
    manager_two = ConnectionManager()
    first = RedisEventService(settings.redis_url, manager_one)
    second = RedisEventService(settings.redis_url, manager_two)
    socket_one, socket_two, socket_private = AsyncMock(), AsyncMock(), AsyncMock()
    await manager_one.connect("user-one", socket_one)
    await manager_two.connect("user-one", socket_two)
    await manager_two.connect("user-two", socket_private)
    await first.start()
    await second.start()
    try:
        assert await first.publish("user-one", "tracking.updated", {"id": "test"})
        for _ in range(100):
            if socket_two.send_text.await_count:
                break
            await asyncio.sleep(0.01)
        assert socket_one.send_text.await_count == 1
        assert socket_two.send_text.await_count == 1
        assert socket_private.send_text.await_count == 0
    finally:
        await first.stop()
        await second.stop()


async def test_rate_limit_and_unavailable_redis(settings):
    from app.core.errors import ServiceError
    manager = ConnectionManager()
    service = RedisEventService(settings.redis_url, manager)
    key = "unit-test-counter"
    await service.redis.delete(f"copilot:limits:{key}")
    try:
        await service.rate_limit(key, 1, 60)
        with pytest.raises(ServiceError) as error:
            await service.rate_limit(key, 1, 60)
        assert error.value.status_code == 429
        assert await service.redis.ttl(f"copilot:limits:{key}") > 0
    finally:
        await service.stop()
    broken = RedisEventService("redis://127.0.0.1:6398/0", manager)
    assert await broken.publish("user", "journal.created", {}) is False
    assert await broken.healthy() is False
    with pytest.raises(ServiceError):
        await broken.rate_limit("key", 1, 60)
    await broken.stop()


async def test_failed_connection_does_not_block_other_clients():
    manager = ConnectionManager()
    broken, working = AsyncMock(), AsyncMock()
    broken.send_text.side_effect = RuntimeError("connection lost")
    manager.register("user", broken)
    manager.register("user", working)
    await manager.broadcast("user", {"type": "test"})
    assert broken not in manager.connections["user"]
    working.send_text.assert_awaited_once()


@pytest.mark.parametrize(("payload", "code"), [
    ("not-json", 1008), ("[]" , 1008), ('{"type":"ping","channel":"other"}', 1008),
    ("x" * 8193, 1009),
])
def test_invalid_socket_messages_close_with_protocol_codes(client, user, payload, code):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws") as socket:
            socket_auth(socket, user)
            socket.send_text(payload)
            socket.receive_json()
    assert error.value.code == code


def test_binary_socket_messages_are_rejected_as_invalid_protocol(client, user):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws") as socket:
            socket_auth(socket, user)
            socket.send_bytes(b"binary-input")
            socket.receive_json()
    assert error.value.code == 1008


def test_logout_closes_only_the_corresponding_socket_session(client, user):
    response = client.post("/api/auth/login", json={"email": "first@example.com", "password": user["password"]})
    second_user = {"headers": {"Authorization": f"Bearer {response.json()['access_token']}"}}
    with client.websocket_connect("/api/ws") as first, client.websocket_connect("/api/ws") as second:
        socket_auth(first, user)
        socket_auth(second, second_user)
        assert client.post("/api/auth/logout", headers=user["headers"]).status_code == 204
        with pytest.raises(WebSocketDisconnect) as error:
            first.receive_json()
        assert error.value.code == 1008
        second.send_json({"type": "ping"})
        assert second.receive_json() == {"type": "pong"}


def test_password_change_closes_user_sockets_but_not_other_users(client, user, other_user):
    response = client.post("/api/auth/login", json={"email": "first@example.com", "password": user["password"]})
    second_user = {"headers": {"Authorization": f"Bearer {response.json()['access_token']}"}}
    with client.websocket_connect("/api/ws") as first, client.websocket_connect("/api/ws") as second, client.websocket_connect("/api/ws") as unrelated:
        socket_auth(first, user)
        socket_auth(second, second_user)
        socket_auth(unrelated, other_user)
        assert client.post("/api/users/me/password", headers=user["headers"], json={
            "current_password": user["password"], "new_password": "ChangedPassword123!",
        }).status_code == 204
        for socket in (first, second):
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()
        unrelated.send_json({"type": "ping"})
        assert unrelated.receive_json() == {"type": "pong"}
