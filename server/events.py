from __future__ import annotations

import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket


DEFAULT_WS_PREFS: Dict[str, bool] = {
    "jobs": False,
    "job_progress": False,
    "assets": True,
    "system": True,
}


def normalize_ws_prefs(payload: Dict[str, Any] | None, current: Dict[str, bool]) -> Dict[str, bool]:
    if not isinstance(payload, dict):
        return current
    updated = current.copy()
    for key in DEFAULT_WS_PREFS:
        if key in payload:
            updated[key] = bool(payload[key])
    return updated


def event_allowed(event_type: str | None, prefs: Dict[str, bool]) -> bool:
    if not event_type:
        return True
    if event_type in ("job_update", "job_created", "jobs_snapshot"):
        return prefs.get("jobs", True)
    if event_type == "job_progress":
        return prefs.get("job_progress", True)
    if event_type in ("asset_created", "asset_updated", "assets_snapshot"):
        return prefs.get("assets", True)
    if event_type in ("comfy_connected", "comfy_disconnected"):
        return prefs.get("system", True)
    return True


class WebSocketManager:
    """Simple broadcast hub for frontend clients."""

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        # serialize sends per socket to avoid "concurrent send" issues
        self._send_locks: Dict[WebSocket, asyncio.Lock] = {}
        self._prefs: Dict[WebSocket, Dict[str, bool]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
            self._send_locks[ws] = asyncio.Lock()
            self._prefs[ws] = DEFAULT_WS_PREFS.copy()


    def get_prefs(self, ws: WebSocket) -> Dict[str, bool]:
        return self._prefs.get(ws, DEFAULT_WS_PREFS.copy())
    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
            self._send_locks.pop(ws, None)
            self._prefs.pop(ws, None)

    async def update_prefs(self, ws: WebSocket, payload: Dict[str, Any] | None) -> None:
        async with self._lock:
            current = self._prefs.get(ws, DEFAULT_WS_PREFS.copy())
            self._prefs[ws] = normalize_ws_prefs(payload, current)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        # Make a snapshot to avoid holding the lock while sending.
        async with self._lock:
            clients = list(self._clients)
            locks = {ws: self._send_locks.get(ws) for ws in clients}
            prefs = {ws: self._prefs.get(ws, DEFAULT_WS_PREFS) for ws in clients}

        if not clients:
            return

        event_type = message.get("type") if isinstance(message, dict) else None
        dead: list[WebSocket] = []
        for ws in clients:
            if not event_allowed(event_type, prefs.get(ws, DEFAULT_WS_PREFS)):
                continue
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
