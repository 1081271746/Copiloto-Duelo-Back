import asyncio
import contextlib
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError
from starlette.websockets import WebSocketState

from app.schemas.auth import StrictModel
from app.security.tokens import authenticate


router = APIRouter(tags=["realtime"])


async def close_socket(socket: WebSocket, code: int) -> None:
    if socket.application_state == WebSocketState.CONNECTED:
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await socket.close(code=code)


class SocketAuthentication(StrictModel):
    type: Literal["authenticate"]
    access_token: str = Field(min_length=20, max_length=4096)


class SocketMessage(StrictModel):
    type: Literal["ping"]


async def receive_limited(socket: WebSocket, timeout: float):
    text = await asyncio.wait_for(socket.receive_text(), timeout=timeout)
    if len(text.encode()) > 8192:
        await close_socket(socket, 1009)
        raise WebSocketDisconnect(1009)
    return json.loads(text)


@router.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    settings = socket.app.state.settings
    origin = socket.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        await socket.close(code=1008)
        return
    await socket.accept()
    user_id = None
    try:
        message = SocketAuthentication.model_validate(await receive_limited(socket, 10))
        with socket.app.state.session_factory() as db:
            user, claims = authenticate(message.access_token, db, settings)
            user_id = user.id
        socket.scope["token_session"] = claims["jti"]
        socket.scope["token_expires"] = claims["exp"]
        if not await socket.app.state.events.healthy():
            await close_socket(socket, 1013)
            return
        socket.app.state.manager.register(user_id, socket)
        await socket.send_json({"type": "ready", "user_id": user_id, "delivery": "at_most_once"})
        while True:
            remaining = claims["exp"] - datetime.now(timezone.utc).timestamp()
            if remaining <= 0:
                await close_socket(socket, 1008)
                return
            try:
                payload = await receive_limited(socket, min(15, remaining))
            except TimeoutError:
                with socket.app.state.session_factory() as db:
                    authenticate(message.access_token, db, settings)
                continue
            with socket.app.state.session_factory() as db:
                authenticate(message.access_token, db, settings)
            SocketMessage.model_validate(payload)
            await socket.app.state.events.rate_limit(f"socket:{user_id}", 120, 60)
            await socket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except (TimeoutError, ValidationError, ValueError, HTTPException):
        await close_socket(socket, 1008)
    except Exception:
        await close_socket(socket, 1011)
    finally:
        if user_id:
            socket.app.state.manager.disconnect(user_id, socket)
