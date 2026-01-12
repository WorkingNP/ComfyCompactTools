from __future__ import annotations

import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket


class WebSocketManager:
    """Simple broadcast hub for frontend clients."""

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        # serialize sends per socket to avoid "concurrent send" issues
        self._send_locks: Dict[WebSocket, asyncio.Lock] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
            self._send_locks[ws] = asyncio.Lock()

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
            self._send_locks.pop(ws, None)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        # Make a snapshot to avoid holding the lock while sending.
        async with self._lock:
            clients = list(self._clients)
            locks = {ws: self._send_locks.get(ws) for ws in clients}

        if not clients:
            return

        dead: list[WebSocket] = []
        for ws in clients:
            try:
                lock = locks.get(ws)
                if lock is None:
                    await ws.send_json(message)
                else:
                    async with lock:
                        await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
                    self._send_locks.pop(ws, None)
