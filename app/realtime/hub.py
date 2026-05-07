"""Conexiones WebSocket en memoria (un solo proceso uvicorn)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from starlette.websockets import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        text = json.dumps(data, default=str)
        async with self._lock:
            clients = list(self._connections)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


hub = RealtimeHub()
