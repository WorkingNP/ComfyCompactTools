#!/usr/bin/env python3
"""
Generate images with ComfyUI (local) using the official-ish FLUX.2 [klein] 4B node pipeline
(UNETLoader + CLIPLoader(qwen_3_4b) + CLIPTextEncode + CFGGuider + Flux2Scheduler + SamplerCustomAdvanced + VAE).

This is designed to be called by another program / local LLM tool without you touching the ComfyUI canvas.

How it works:
- POST /prompt (queue)
- Poll GET /history/{prompt_id}
- Download images via GET /view

Usage:
  pip install requests

  # Distilled FP8 (recommended defaults: steps=4, cfg=1)
  python comfy_flux2_klein_generate.py \
    --prompt "a hedgehog wearing a tiny party hat, 2000s digicam vibe" \
    --template flux2_klein_4b_fp8_prompt_template.json \
    --out ./outputs

  # Base FP8 (more steps + higher cfg)
  python comfy_flux2_klein_generate.py \
    --prompt "a cinematic wide shot of a neon city in rain" \
    --template flux2_klein_base_4b_fp8_prompt_template.json \
    --steps 20 --cfg 5 \
    --out ./outputs

Notes:
- Put models in:
    ComfyUI/models/text_encoders/qwen_3_4b.safetensors
    ComfyUI/models/diffusion_models/flux-2-klein-4b-fp8.safetensors  (or base variant)
    ComfyUI/models/vae/flux2-vae.safetensors
- ComfyUI must be new enough to have Flux2Scheduler / EmptyFlux2LatentImage / SamplerCustomAdvanced etc.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import requests


def load_template(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_params(prompt: Dict[str, Any], *,
               text: str,
               negative: str,
               width: int,
               height: int,
               steps: int,
               cfg: float,
               seed: int,
               sampler_name: str,
               filename_prefix: str,
               text_encoder: str,
               unet: str,
               vae: str,
               batch: int) -> None:
    # Prompts
    prompt["2"]["inputs"]["text"] = text
    prompt["3"]["inputs"]["text"] = negative

    # Models
    prompt["1"]["inputs"]["clip_name"] = text_encoder
    prompt["4"]["inputs"]["unet_name"] = unet
    prompt["11"]["inputs"]["vae_name"] = vae

    # Guidance / seed
    prompt["5"]["inputs"]["cfg"] = float(cfg)
    prompt["6"]["inputs"]["noise_seed"] = int(seed)

    # Resolution / steps / batch
    prompt["7"]["inputs"]["width"] = int(width)
    prompt["7"]["inputs"]["height"] = int(height)
    prompt["7"]["inputs"]["batch_size"] = int(batch)

    prompt["8"]["inputs"]["steps"] = int(steps)
    prompt["8"]["inputs"]["width"] = int(width)
    prompt["8"]["inputs"]["height"] = int(height)

    # Sampler
    prompt["9"]["inputs"]["sampler_name"] = sampler_name

    # Output naming
    prompt["13"]["inputs"]["filename_prefix"] = filename_prefix


def queue_prompt(base_url: str, prompt: Dict[str, Any], client_id: str) -> str:
    url = f"{base_url.rstrip('/')}/prompt"
    payload = {"prompt": prompt, "client_id": client_id}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "prompt_id" not in data:
        raise RuntimeError(f"Queue failed: {data}")
    return data["prompt_id"]


def wait_history(base_url: str, prompt_id: str, *, poll_interval: float = 0.5, timeout_s: float = 600) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    t0 = time.time()
    while True:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        hist = r.json()
        if isinstance(hist, dict) and prompt_id in hist:
            return hist[prompt_id]
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"Timed out waiting for prompt_id={prompt_id}")
        time.sleep(poll_interval)


def extract_images(history_item: Dict[str, Any]) -> List[Dict[str, str]]:
    outs = history_item.get("outputs", {})
    images: List[Dict[str, str]] = []
    for node_id, out in outs.items():
        for img in (out.get("images", []) or []):
            if all(k in img for k in ("filename", "subfolder", "type")):
                images.append({
                    "node_id": str(node_id),
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                })
    return images


def download_image(base_url: str, img_meta: Dict[str, str], out_dir: Path) -> Path:
    params = {
        "filename": img_meta["filename"],
        "subfolder": img_meta.get("subfolder", ""),
        "type": img_meta.get("type", "output"),
    }
    url = f"{base_url.rstrip('/')}/view"
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / img_meta["filename"]
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8188")
    ap.add_argument("--template", default=str(Path(__file__).with_name("flux2_klein_4b_fp8_prompt_template.json")))
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default="")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)

    # Distilled defaults (4-step model). Override if using base.
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--cfg", type=float, default=1.0)

    ap.add_argument("--sampler", default="euler")
    ap.add_argument("--seed", type=int, default=-1, help="-1 => random")
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--filename-prefix", default="Flux2-Klein")
    ap.add_argument("--text-encoder", default="qwen_3_4b.safetensors")
    ap.add_argument("--unet", default="flux-2-klein-4b-fp8.safetensors")
    ap.add_argument("--vae", default="flux2-vae.safetensors")
    ap.add_argument("--out", default="./comfy_outputs")
    args = ap.parse_args()

    seed = args.seed if args.seed != -1 else random.randrange(0, 2**63)

    prompt = load_template(args.template)
    set_params(
        prompt,
        text=args.prompt,
        negative=args.negative,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg=args.cfg,
        seed=seed,
        sampler_name=args.sampler,
        filename_prefix=args.filename_prefix,
        text_encoder=args.text_encoder,
        unet=args.unet,
        vae=args.vae,
        batch=args.batch,
    )

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(args.base_url, prompt, client_id)
    print(f"queued prompt_id={prompt_id}")

    hist_item = wait_history(args.base_url, prompt_id)
    images = extract_images(hist_item)
    if not images:
        raise RuntimeError(f"No images found in history outputs. history_item keys={list(hist_item.keys())}")

    out_dir = Path(args.out)
    paths = [download_image(args.base_url, meta, out_dir) for meta in images]

    print("downloaded:")
    for p in paths:
        print(str(p))


if __name__ == "__main__":
    main()
