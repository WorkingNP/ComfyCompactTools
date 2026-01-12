from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx


def _http_to_ws(url: str) -> str:
    # http://127.0.0.1:8188 -> ws://127.0.0.1:8188
    if url.startswith("https://"):
        return "wss://" + url[len("https://") :]
    if url.startswith("http://"):
        return "ws://" + url[len("http://") :]
    # Fallback: treat as host:port
    return "ws://" + url


class ComfyClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

    def ws_url(self, client_id: str) -> str:
        return f"{_http_to_ws(self.base_url)}/ws?clientId={client_id}"

    async def close(self) -> None:
        await self.http.aclose()

    async def submit_prompt(self, prompt_workflow: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        payload = {"prompt": prompt_workflow, "client_id": client_id}
        r = await self.http.post(f"{self.base_url}/prompt", json=payload)
        if r.status_code >= 400:
            body = ""
            try:
                body = r.text[:2000]
            except Exception:
                body = ""
            raise RuntimeError(f"ComfyUI error: {r.status_code} {body}")
        return r.json()

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        r = await self.http.get(f"{self.base_url}/history/{prompt_id}")
        r.raise_for_status()
        return r.json()

    async def get_view_image(self, *, filename: str, subfolder: str, folder_type: str) -> bytes:
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        r = await self.http.get(f"{self.base_url}/view", params=params)
        r.raise_for_status()
        return r.content

    async def get_models_in_folder(self, folder: str) -> List[str]:
        """Try ComfyUI's /models/{folder} (local server route).

        Response shape can vary by version; we normalize to List[str].
        """
        r = await self.http.get(f"{self.base_url}/models/{folder}")
        r.raise_for_status()
        data = r.json()

        # Common shapes: ["a.safetensors", ...] OR [{"name":"..."}, ...] OR {"models":[...]}
        if isinstance(data, list):
            if not data:
                return []
            if isinstance(data[0], str):
                return [str(x) for x in data]
            if isinstance(data[0], dict) and "name" in data[0]:
                return [str(x.get("name")) for x in data if x.get("name")]

        if isinstance(data, dict):
            for key in ("models", "items", "data"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    if items and isinstance(items[0], str):
                        return [str(x) for x in items]
                    if items and isinstance(items[0], dict) and "name" in items[0]:
                        return [str(x.get("name")) for x in items if x.get("name")]

        return []

    async def get_object_info(self, node_class: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/object_info" + (f"/{node_class}" if node_class else "")
        r = await self.http.get(url)
        r.raise_for_status()
        return r.json()

    async def get_ksampler_options(self) -> Dict[str, List[str]]:
        """Best-effort discovery of sampler_name / scheduler options."""
        try:
            info = await self.get_object_info("KSampler")
        except Exception:
            return {}

        # The shape is not strongly guaranteed across versions.
        # We'll search for string lists under keys 'sampler_name' and 'scheduler'.
        out: Dict[str, List[str]] = {}

        def pull_choices(v: Any) -> List[str]:
            if isinstance(v, list):
                # Sometimes it's ["STRING", {"default":..., "choices":[...]}]
                if len(v) == 2 and isinstance(v[1], dict) and isinstance(v[1].get("choices"), list):
                    return [str(x) for x in v[1]["choices"]]
                # Sometimes it's [[...choices...], {...}]
                if len(v) == 2 and isinstance(v[0], list) and all(isinstance(x, (str, int, float)) for x in v[0]):
                    return [str(x) for x in v[0]]
                # Sometimes it's [[...choices...]]
                if len(v) == 1 and isinstance(v[0], list) and all(isinstance(x, (str, int, float)) for x in v[0]):
                    return [str(x) for x in v[0]]
                # Sometimes it's ["euler", "euler_a", ...]
                if v and all(isinstance(x, (str, int, float)) for x in v):
                    return [str(x) for x in v]
            if isinstance(v, dict) and isinstance(v.get("choices"), list):
                return [str(x) for x in v["choices"]]
            return []

        # info may be {"KSampler": {...}} or {...}.
        ks = info.get("KSampler") if isinstance(info, dict) and "KSampler" in info else info
        if not isinstance(ks, dict):
            return {}

        inputs = ks.get("input") or {}
        required = inputs.get("required") or {}

        for key in ("sampler_name", "scheduler"):
            if key in required:
                choices = pull_choices(required[key])
                if choices:
                    out[key] = choices

        return out
