from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .comfy_client import ComfyClient
from .comfy_workflow import build_txt2img_workflow
from .db import Database
from .events import WebSocketManager
from .storage import ensure_dir, new_asset_filename, write_bytes


load_dotenv()


@dataclass
class Settings:
    comfy_url: str
    comfy_checkpoint: str
    host: str
    port: int
    data_dir: str
    xai_api_key: str
    xai_base_url: str
    xai_model: str
    xai_models: List[str]


def get_settings() -> Settings:
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    config: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    config = loaded
        except Exception as e:
            print(f"[config] Failed to read {config_path}: {e}", file=sys.stderr)

    xai_model = str(config.get("xai_model") or os.getenv("XAI_MODEL", "grok-2-latest"))
    raw_models = config.get("xai_models")
    if isinstance(raw_models, list):
        models = [str(m).strip() for m in raw_models if str(m).strip()]
    elif isinstance(raw_models, str):
        models = [m.strip() for m in raw_models.split(",") if m.strip()]
    else:
        env_models = os.getenv("XAI_MODELS", "")
        models = [m.strip() for m in env_models.split(",") if m.strip()]
    if xai_model and xai_model not in models:
        models = [xai_model] + models

    return Settings(
        comfy_url=str(config.get("comfy_url") or os.getenv("COMFY_URL", "http://127.0.0.1:8188")).rstrip("/"),
        comfy_checkpoint=str(config.get("comfy_checkpoint") or os.getenv("COMFY_CHECKPOINT", "")),
        host=str(config.get("host") or os.getenv("HOST", "127.0.0.1")),
        port=int(config.get("port") or os.getenv("PORT", "8787")),
        data_dir=str(config.get("data_dir") or os.getenv("DATA_DIR", "./data")),
        xai_api_key=str(config.get("xai_api_key") or os.getenv("XAI_API_KEY", "")),
        xai_base_url=str(config.get("xai_base_url") or os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")).rstrip("/"),
        xai_model=xai_model,
        xai_models=models or ([xai_model] if xai_model else []),
    )


settings = get_settings()

DATA_DIR = os.path.abspath(settings.data_dir)
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
DB_PATH = os.path.join(DATA_DIR, "cockpit.sqlite3")
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
WEB_DIR = os.path.abspath(WEB_DIR)

ensure_dir(DATA_DIR)
ensure_dir(ASSETS_DIR)


db = Database(DB_PATH)
ws_manager = WebSocketManager()
comfy = ComfyClient(settings.comfy_url)

# ComfyUI uses a 'clientId' in websocket query params.
COMFY_CLIENT_ID = str(uuid.uuid4())

# Cached options (best-effort)
CACHED_CHECKPOINTS: List[str] = []
CACHED_SAMPLERS: List[str] = []
CACHED_SCHEDULERS: List[str] = []
CACHED_VAES: List[str] = []


# ------------------------------
# Grok (xAI) chat (MVP)
# ------------------------------

GROK_SYSTEM_PROMPT = (
    "You are Grok. Keep responses concise unless the user asks for detail. "
    "When returning JSON, return ONLY JSON with no extra commentary."
)

_grok_lock = asyncio.Lock()
GROK_RECENT_LIMIT = 30


def _extract_chat_text(data: Dict[str, Any]) -> str:
    """Best-effort: accept both OpenAI Chat Completions and Responses-style payloads."""
    # Chat Completions shape
    try:
        choices = data.get("choices")
        if choices:
            c0 = choices[0] or {}
            msg = c0.get("message") or {}
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg.get("content"))
            if c0.get("text"):
                return str(c0.get("text"))
    except Exception:
        pass

    # Responses-ish shape
    if data.get("output_text"):
        return str(data.get("output_text"))

    # Fallback
    return json.dumps(data)[:2000]


class JobCreate(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = "(worst quality, low quality:1.4), (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), cloned face, malformed hands, long neck, extra breasts, mutated pussy, bad pussy, blurry, watermark, text, error, cropped"

    # Core params
    width: int = 832
    height: int = 1024
    steps: int = 20
    cfg: float = 4.0
    sampler_name: str = "euler_ancestral"
    scheduler: str = "normal"
    seed: int = -1
    batch_size: int = 1
    clip_skip: int = Field(1, ge=1, le=24)
    vae: Optional[str] = None

    # Optional override
    checkpoint: Optional[str] = None


class JobOut(BaseModel):
    id: str
    engine: str
    status: str
    prompt_id: Optional[str]
    prompt: str
    negative_prompt: str
    params: Dict[str, Any]
    created_at: str
    updated_at: str
    progress_value: float
    progress_max: float
    error: Optional[str] = None


class AssetOut(BaseModel):
    id: str
    job_id: str
    engine: str
    filename: str
    url: str
    created_at: str
    favorite: bool
    recipe: Dict[str, Any]
    meta: Dict[str, Any]


class GrokConfigOut(BaseModel):
    ok: bool
    model: str
    base_url: str
    models: List[str]


class GrokChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    reset: bool = False
    send_full_history: bool = False
    model: Optional[str] = None


class GrokChatOut(BaseModel):
    reply: str


class GrokMessageOut(BaseModel):
    role: str
    content: str
    created_at: str


class TemplateOut(BaseModel):
    name: str
    checkpoint: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    cfg: Optional[float] = None
    sampler_name: Optional[str] = None
    scheduler: Optional[str] = None
    seed: Optional[int] = None
    batch_size: Optional[int] = None
    clip_skip: Optional[int] = None
    vae: Optional[str] = None
    negative_prompt: Optional[str] = None
    trigger_words: Optional[List[str]] = None
    notes: Optional[str] = None


class GrokImageIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    n: int = Field(1, ge=1, le=4)


def jobrow_to_out(row) -> JobOut:
    params = json.loads(row.params_json) if row.params_json else {}
    return JobOut(
        id=row.id,
        engine=row.engine,
        status=row.status,
        prompt_id=row.prompt_id,
        prompt=row.prompt,
        negative_prompt=row.negative_prompt,
        params=params,
        created_at=row.created_at,
        updated_at=row.updated_at,
        progress_value=row.progress_value,
        progress_max=row.progress_max,
        error=row.error,
    )


def assetrow_to_out(row) -> AssetOut:
    recipe = json.loads(row.recipe_json) if row.recipe_json else {}
    meta = json.loads(row.meta_json) if row.meta_json else {}
    return AssetOut(
        id=row.id,
        job_id=row.job_id,
        engine=row.engine,
        filename=row.filename,
        url=f"/assets/{row.filename}",
        created_at=row.created_at,
        favorite=bool(row.favorite),
        recipe=recipe,
        meta=meta,
    )


async def refresh_comfy_options() -> None:
    global CACHED_CHECKPOINTS, CACHED_SAMPLERS, CACHED_SCHEDULERS, CACHED_VAES

    # Checkpoints
    checkpoints: List[str] = []
    try:
        checkpoints = await comfy.get_models_in_folder("checkpoints")
    except Exception:
        checkpoints = []

    # Samplers / schedulers via object_info (best-effort)
    sampler_name_choices: List[str] = []
    scheduler_choices: List[str] = []
    try:
        opts = await comfy.get_ksampler_options()
        sampler_name_choices = opts.get("sampler_name", [])
        scheduler_choices = opts.get("scheduler", [])
    except Exception:
        sampler_name_choices = []
        scheduler_choices = []

    # VAEs
    vae_choices: List[str] = []
    try:
        vae_choices = await comfy.get_models_in_folder("vae")
    except Exception:
        vae_choices = []

    if not vae_choices:
        try:
            info = await comfy.get_object_info("VAELoader")
            node = info.get("VAELoader") if isinstance(info, dict) else {}
            required = (node or {}).get("input", {}).get("required", {})
            raw = required.get("vae_name")
            if isinstance(raw, list) and raw:
                if isinstance(raw[0], list):
                    vae_choices = [str(x) for x in raw[0]]
                elif all(isinstance(x, (str, int, float)) for x in raw):
                    vae_choices = [str(x) for x in raw]
        except Exception:
            vae_choices = []

    # Fallbacks
    if not sampler_name_choices:
        sampler_name_choices = [
            "euler",
            "euler_a",
            "heun",
            "dpm_2",
            "dpm_2_a",
            "dpmpp_2m",
            "dpmpp_2m_sde",
            "dpmpp_3m_sde",
            "lcm",
        ]

    if not scheduler_choices:
        scheduler_choices = ["normal", "karras", "exponential", "simple", "ddim_uniform"]

    CACHED_CHECKPOINTS = sorted(set([c for c in checkpoints if c]))
    CACHED_SAMPLERS = sorted(set([s for s in sampler_name_choices if s]))
    CACHED_SCHEDULERS = sorted(set([s for s in scheduler_choices if s]))
    CACHED_VAES = sorted(set([v for v in vae_choices if v]))


def pick_checkpoint(override: Optional[str] = None) -> str:
    if override:
        return override
    if settings.comfy_checkpoint:
        return settings.comfy_checkpoint
    if CACHED_CHECKPOINTS:
        return CACHED_CHECKPOINTS[0]
    # Last resort (may not exist on your machine)
    return "v1-5-pruned-emaonly.safetensors"


async def grok_chat(
    message: str,
    reset: bool = False,
    send_full_history: bool = False,
    model: Optional[str] = None,
) -> str:
    """Send a message to xAI Grok (OpenAI-compatible Chat Completions).

    Notes:
    - We persist full history to DB.
    - You can toggle between full history and recent messages for each request.
    """
    if not settings.xai_api_key:
        raise HTTPException(status_code=400, detail="XAI_API_KEY is not set")

    async with _grok_lock:
        if reset:
            db.clear_grok_messages()

        db.create_grok_message(role="user", content=message)

        history_limit = None if send_full_history else GROK_RECENT_LIMIT
        history_rows = db.list_grok_messages(limit=history_limit)

        messages = [{"role": "system", "content": GROK_SYSTEM_PROMPT}]
        messages.extend([{"role": row.role, "content": row.content} for row in history_rows])

        model_to_use = (model or "").strip() or settings.xai_model
        payload = {
            "model": model_to_use,
            "messages": messages,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {settings.xai_api_key}",
            "Content-Type": "application/json",
        }

        url = f"{settings.xai_base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as e:
            # Surface server response (truncate)
            body = ""
            try:
                body = e.response.text[:2000]
            except Exception:
                body = ""
            raise HTTPException(status_code=502, detail=f"xAI error: {e.response.status_code} {body}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"xAI request failed: {str(e)}")

        reply = _extract_chat_text(data)
        db.create_grok_message(role="assistant", content=reply)
        return reply


def _image_ext_from_url(url: str) -> str:
    path = url.split("?")[0]
    ext = os.path.splitext(path)[1]
    return ext if ext else ".png"


async def harvest_assets_for_prompt(job_id: str, prompt_id: str) -> List[AssetOut]:
    """Fetch outputs from /history and download images via /view."""
    created_assets: List[AssetOut] = []

    history = await comfy.get_history(prompt_id)
    item = history.get(prompt_id)
    if not item:
        return []

    outputs = item.get("outputs") or {}

    job = db.get_job(job_id)
    if not job:
        return []

    recipe = {
        "engine": job.engine,
        "prompt": job.prompt,
        "negative_prompt": job.negative_prompt,
        "params": json.loads(job.params_json) if job.params_json else {},
    }

    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue
        images = node_output.get("images")
        if not images:
            continue
        for image_info in images:
            try:
                filename = image_info.get("filename")
                subfolder = image_info.get("subfolder", "")
                folder_type = image_info.get("type", "output")
                if not filename:
                    continue

                img_bytes = await comfy.get_view_image(filename=filename, subfolder=subfolder, folder_type=folder_type)

                stored_name = new_asset_filename(prefix="comfy", ext=os.path.splitext(filename)[1] or ".png")
                write_bytes(os.path.join(ASSETS_DIR, stored_name), img_bytes)

                asset_id = str(uuid.uuid4())
                meta = {
                    "prompt_id": prompt_id,
                    "node_id": str(node_id),
                    "comfy": {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": folder_type,
                    },
                }

                db.create_asset(
                    asset_id=asset_id,
                    job_id=job_id,
                    engine="comfy",
                    filename=stored_name,
                    recipe=recipe,
                    meta=meta,
                )

                row = db.get_asset(asset_id)
                if row:
                    created_assets.append(assetrow_to_out(row))

            except Exception as e:
                # swallow per-image failure; other images may still download
                continue

    return created_assets


async def comfy_ws_loop() -> None:
    """Maintain a websocket connection to ComfyUI and translate its events into our app events."""
    import websockets

    ws_url = comfy.ws_url(COMFY_CLIENT_ID)

    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                # Connection established
                await ws_manager.broadcast({"type": "comfy_connected", "payload": {"url": settings.comfy_url}})

                while True:
                    raw = await ws.recv()
                    if isinstance(raw, (bytes, bytearray)):
                        continue

                    msg = json.loads(raw)
                    mtype = msg.get("type")
                    data = msg.get("data") or {}
                    prompt_id = data.get("prompt_id")

                    if not prompt_id:
                        continue

                    job = db.get_job_by_prompt_id(str(prompt_id))
                    if not job:
                        continue

                    # Update running state
                    if mtype == "execution_start":
                        db.update_job(job.id, status="running")
                        await ws_manager.broadcast({"type": "job_update", "payload": jobrow_to_out(db.get_job(job.id)).model_dump()})

                    # Progress updates
                    if mtype == "progress":
                        value = float(data.get("value", 0))
                        maxv = float(data.get("max", 0))
                        db.update_job(job.id, progress_value=value, progress_max=maxv)
                        await ws_manager.broadcast({"type": "job_progress", "payload": {"job_id": job.id, "prompt_id": prompt_id, "value": value, "max": maxv}})

                    # Errors
                    if mtype in ("execution_error", "execution_interrupted"):
                        err = json.dumps(data)[:2000]
                        db.update_job(job.id, status="failed", error=err)
                        await ws_manager.broadcast({"type": "job_update", "payload": jobrow_to_out(db.get_job(job.id)).model_dump()})

                    # Completion
                    # Per ComfyUI docs, `executing` with node=None indicates completion.
                    # Some builds also send execution_success. We treat either as a completion signal,
                    # but we guard harvesting with a DB flag to avoid duplicating assets.
                    is_done_signal = (mtype == "executing" and data.get("node") is None) or (mtype == "execution_success")
                    if is_done_signal:
                        latest = db.get_job(job.id)
                        if latest and int(latest.harvested) == 1:
                            # Already harvested; nothing to do.
                            continue

                        db.update_job(job.id, status="completed")
                        await ws_manager.broadcast({"type": "job_update", "payload": jobrow_to_out(db.get_job(job.id)).model_dump()})

                        assets = await harvest_assets_for_prompt(job.id, str(prompt_id))
                        db.update_job(job.id, harvested=1)
                        for a in assets:
                            await ws_manager.broadcast({"type": "asset_created", "payload": a.model_dump()})

        except Exception:
            # Connection lost; retry.
            await ws_manager.broadcast({"type": "comfy_disconnected", "payload": {"url": settings.comfy_url}})
            await asyncio.sleep(2.0)


app = FastAPI(title="Grok-Comfy Cockpit (MVP)")


@app.on_event("startup")
async def on_startup() -> None:
    await refresh_comfy_options()
    asyncio.create_task(comfy_ws_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await comfy.close()


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "comfy_url": settings.comfy_url}


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    return {
        "comfy_url": settings.comfy_url,
        "defaults": {
            "width": 832,
            "height": 1024,
            "steps": 20,
            "cfg": 4.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "seed": -1,
            "batch_size": 1,
            "clip_skip": 2,
            "vae": None,
            "negative_prompt": "(worst quality, low quality:1.4), (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), cloned face, malformed hands, long neck, extra breasts, mutated pussy, bad pussy, blurry, watermark, text, error, cropped",
            "checkpoint": pick_checkpoint(None),
        },
        "choices": {
            "checkpoints": CACHED_CHECKPOINTS,
            "samplers": CACHED_SAMPLERS,
            "schedulers": CACHED_SCHEDULERS,
            "vaes": CACHED_VAES,
        },
        "client_id": COMFY_CLIENT_ID,
    }


@app.get("/api/grok/config", response_model=GrokConfigOut)
async def grok_config() -> GrokConfigOut:
    return GrokConfigOut(
        ok=bool(settings.xai_api_key),
        model=settings.xai_model,
        base_url=settings.xai_base_url,
        models=settings.xai_models,
    )


@app.post("/api/grok/chat", response_model=GrokChatOut)
async def grok_chat_api(req: GrokChatIn) -> GrokChatOut:
    reply = await grok_chat(
        req.message,
        reset=req.reset,
        send_full_history=req.send_full_history,
        model=req.model,
    )
    return GrokChatOut(reply=reply)


@app.get("/api/grok/history", response_model=List[GrokMessageOut])
async def grok_history(limit: Optional[int] = None) -> List[GrokMessageOut]:
    rows = db.list_grok_messages(limit=limit)
    return [GrokMessageOut(role=r.role, content=r.content, created_at=r.created_at) for r in rows]


@app.get("/api/templates", response_model=List[TemplateOut])
async def list_templates() -> List[TemplateOut]:
    templates_path = Path(__file__).resolve().parent.parent / "templates.json"
    if templates_path.exists():
        try:
            with templates_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("templates") if isinstance(data, dict) else data
            if isinstance(items, list):
                out = []
                for item in items:
                    if isinstance(item, dict) and item.get("name"):
                        out.append(TemplateOut(**item))
                if out:
                    return out
        except Exception:
            pass
    return []


@app.post("/api/grok/image", response_model=List[AssetOut])
async def grok_image(req: GrokImageIn) -> List[AssetOut]:
    if not settings.xai_api_key:
        raise HTTPException(status_code=400, detail="XAI_API_KEY is not set")

    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is empty")

    model_to_use = (req.model or "").strip() or settings.xai_model
    if "image" not in model_to_use:
        raise HTTPException(status_code=400, detail=f"model is not image-capable: {model_to_use}")

    payload = {
        "model": model_to_use,
        "prompt": prompt,
        "n": int(req.n),
    }

    headers = {
        "Authorization": f"Bearer {settings.xai_api_key}",
        "Content-Type": "application/json",
    }

    url = f"{settings.xai_base_url}/images/generations"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:2000]
        except Exception:
            body = ""
        raise HTTPException(status_code=502, detail=f"xAI error: {e.response.status_code} {body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"xAI request failed: {str(e)}")

    items = data.get("data") or []
    if not isinstance(items, list):
        items = []

    created: List[AssetOut] = []
    job_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            img_bytes: Optional[bytes] = None
            img_url = item.get("url")
            b64 = item.get("b64_json")

            if b64:
                try:
                    img_bytes = base64.b64decode(b64)
                except Exception:
                    img_bytes = None
            elif img_url:
                try:
                    resp = await client.get(img_url)
                    resp.raise_for_status()
                    img_bytes = resp.content
                except Exception:
                    img_bytes = None

            if not img_bytes:
                continue

            ext = _image_ext_from_url(str(img_url)) if img_url else ".png"
            stored_name = new_asset_filename(prefix="grok", ext=ext)
            write_bytes(os.path.join(ASSETS_DIR, stored_name), img_bytes)

            asset_id = str(uuid.uuid4())
            recipe = {
                "engine": "grok-image",
                "prompt": prompt,
                "model": model_to_use,
                "params": {"n": int(req.n)},
            }
            meta = {
                "source": "xai",
                "model": model_to_use,
                "index": idx,
                "image_url": img_url,
                "revised_prompt": item.get("revised_prompt"),
            }

            db.create_asset(
                asset_id=asset_id,
                job_id=job_id,
                engine="grok-image",
                filename=stored_name,
                recipe=recipe,
                meta=meta,
            )

            row = db.get_asset(asset_id)
            if row:
                out = assetrow_to_out(row)
                created.append(out)
                await ws_manager.broadcast({"type": "asset_created", "payload": out.model_dump()})

    if not created:
        raise HTTPException(status_code=502, detail="xAI returned no images or downloads failed")

    return created


@app.post("/api/jobs", response_model=JobOut)
async def create_job(req: JobCreate) -> JobOut:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is empty")

    job_id = str(uuid.uuid4())

    sampler_name = req.sampler_name
    scheduler = req.scheduler
    checkpoint = pick_checkpoint(req.checkpoint)

    if CACHED_SAMPLERS and sampler_name not in CACHED_SAMPLERS:
        await refresh_comfy_options()
    if CACHED_SAMPLERS and sampler_name not in CACHED_SAMPLERS:
        sampler_name = CACHED_SAMPLERS[0]

    if CACHED_SCHEDULERS and scheduler not in CACHED_SCHEDULERS:
        await refresh_comfy_options()
    if CACHED_SCHEDULERS and scheduler not in CACHED_SCHEDULERS:
        scheduler = CACHED_SCHEDULERS[0]

    if CACHED_CHECKPOINTS and checkpoint not in CACHED_CHECKPOINTS:
        await refresh_comfy_options()
    if CACHED_CHECKPOINTS and checkpoint not in CACHED_CHECKPOINTS:
        checkpoint = CACHED_CHECKPOINTS[0]

    vae = (req.vae or "").strip() or None
    if vae and CACHED_VAES and vae not in CACHED_VAES:
        await refresh_comfy_options()
    if vae and CACHED_VAES and vae not in CACHED_VAES:
        vae = None

    params = {
        "width": req.width,
        "height": req.height,
        "steps": req.steps,
        "cfg": req.cfg,
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "seed": req.seed,
        "batch_size": req.batch_size,
        "clip_skip": req.clip_skip,
        "vae": vae,
        "checkpoint": checkpoint,
    }

    db.create_job(
        job_id=job_id,
        engine="comfy",
        status="queued",
        prompt=prompt,
        negative_prompt=req.negative_prompt or "",
        params=params,
    )

    await ws_manager.broadcast({"type": "job_created", "payload": jobrow_to_out(db.get_job(job_id)).model_dump()})

    try:
        workflow = build_txt2img_workflow(
            prompt=prompt,
            negative_prompt=req.negative_prompt or "",
            checkpoint=params["checkpoint"],
            width=req.width,
            height=req.height,
            steps=req.steps,
            cfg=req.cfg,
            sampler_name=params["sampler_name"],
            scheduler=params["scheduler"],
            seed=req.seed,
            batch_size=req.batch_size,
            clip_skip=req.clip_skip,
            vae=params["vae"],
        )

        res = await comfy.submit_prompt(workflow, COMFY_CLIENT_ID)
        prompt_id = res.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {res}")

        db.update_job(job_id, prompt_id=str(prompt_id))
        await ws_manager.broadcast({"type": "job_update", "payload": jobrow_to_out(db.get_job(job_id)).model_dump()})

    except Exception as e:
        db.update_job(job_id, status="failed", error=str(e))
        await ws_manager.broadcast({"type": "job_update", "payload": jobrow_to_out(db.get_job(job_id)).model_dump()})

    row = db.get_job(job_id)
    return jobrow_to_out(row)


@app.get("/api/jobs", response_model=List[JobOut])
async def list_jobs(limit: int = 200) -> List[JobOut]:
    return [jobrow_to_out(r) for r in db.list_jobs(limit=limit)]


@app.get("/api/assets", response_model=List[AssetOut])
async def list_assets(limit: int = 200) -> List[AssetOut]:
    return [assetrow_to_out(r) for r in db.list_assets(limit=limit)]


@app.get("/api/assets/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: str) -> AssetOut:
    row = db.get_asset(asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="asset not found")
    return assetrow_to_out(row)


@app.post("/api/assets/{asset_id}/favorite", response_model=AssetOut)
async def toggle_favorite(asset_id: str) -> AssetOut:
    row = db.toggle_favorite(asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="asset not found")
    out = assetrow_to_out(row)
    await ws_manager.broadcast({"type": "asset_updated", "payload": out.model_dump()})
    return out


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws_manager.connect(ws)
    try:
        # On connect, push initial state.
        await ws.send_json({"type": "hello", "payload": {"ok": True}})
        await ws.send_json({"type": "jobs_snapshot", "payload": [jobrow_to_out(r).model_dump() for r in db.list_jobs(limit=200)]})
        await ws.send_json({"type": "assets_snapshot", "payload": [assetrow_to_out(r).model_dump() for r in db.list_assets(limit=200)]})

        while True:
            # We don't currently accept inbound messages; keep socket alive.
            await ws.receive_text()
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(ws)


# Static: stored assets
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Static: web UI
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
