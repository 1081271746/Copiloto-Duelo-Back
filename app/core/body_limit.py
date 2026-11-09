from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = 65536):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length", b"0")
        try:
            oversized = int(length) > self.max_bytes
        except ValueError:
            oversized = True
        if oversized:
            await JSONResponse({"detail": "request_too_large"}, status_code=413)(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await JSONResponse({"detail": "request_too_large"}, status_code=413)(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)
