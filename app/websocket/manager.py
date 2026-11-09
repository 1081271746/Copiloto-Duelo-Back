import asyncio
import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, socket: WebSocket) -> None:
        await socket.accept()
        self.connections.setdefault(user_id, set()).add(socket)

    def disconnect(self, user_id: str, socket: WebSocket) -> None:
        sockets = self.connections.get(user_id)
        if sockets is not None:
            sockets.discard(socket)
            if not sockets:
                self.connections.pop(user_id, None)

    async def broadcast(self, user_id: str, payload: dict) -> None:
        sockets = tuple(self.connections.get(user_id, ()))
        if not sockets:
            return
        message = json.dumps(payload)
        results = await asyncio.gather(
            *(asyncio.wait_for(socket.send_text(message), timeout=3) for socket in sockets),
            return_exceptions=True,
        )
        for socket, result in zip(sockets, results):
            if isinstance(result, BaseException):
                self.disconnect(user_id, socket)

    async def close_all(self, code: int = 1012) -> None:
        sockets = [socket for items in self.connections.values() for socket in items]
        self.connections.clear()
        await asyncio.gather(*(socket.close(code=code) for socket in sockets), return_exceptions=True)
