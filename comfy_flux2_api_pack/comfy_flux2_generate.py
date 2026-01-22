#!/usr/bin/env python3
"""Generate images with ComfyUI (local) using the official FLUX.2-dev node pipeline.

- POST /prompt (queue)
- Poll GET /history/{prompt_id}
- Download images via GET /view

This script is deliberately dependency-light (requests + Pillow optional).

Usage example:
  python comfy_flux2_generate.py \
    --prompt "a studio photo of a red robot" \
    --width 1024 --height 1024 --steps 20 --guidance 4 \
    --out ./outputs

Prereqs:
  pip install requests
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


def load_template(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_common_params(prompt: Dict[str, Any], *,
                      text: str,
                      width: int,
                      height: int,
                      steps: int,
                      guidance: float,
                      seed: int,
                      sampler_name: str,
                      filename_prefix: str,
                      text_encoder: str,
                      unet: str,
                      vae: str) -> None:
    # Text prompt
    prompt["6"]["inputs"]["text"] = text

    # Model file names
    prompt["38"]["inputs"]["clip_name"] = text_encoder
    prompt["12"]["inputs"]["unet_name"] = unet
    prompt["10"]["inputs"]["vae_name"] = vae

    # Sampler / schedule / size
    prompt["16"]["inputs"]["sampler_name"] = sampler_name
    prompt["48"]["inputs"]["steps"] = steps
    prompt["48"]["inputs"]["width"] = width
    prompt["48"]["inputs"]["height"] = height

    prompt["47"]["inputs"]["width"] = width
    prompt["47"]["inputs"]["height"] = height

    # Guidance and seed
    prompt["26"]["inputs"]["guidance"] = float(guidance)
    prompt["25"]["inputs"]["noise_seed"] = int(seed)

    # Output naming
    prompt["9"]["inputs"]["filename_prefix"] = filename_prefix


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
        # When finished, history usually contains prompt_id key with outputs.
        if isinstance(hist, dict) and prompt_id in hist:
            return hist[prompt_id]
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"Timed out waiting for prompt_id={prompt_id}")
        time.sleep(poll_interval)


def extract_images(history_item: Dict[str, Any]) -> List[Dict[str, str]]:
    # history_item['outputs'] is a map from node_id to { 'images': [ {filename, subfolder, type}, ... ] }
    outs = history_item.get("outputs", {})
    images: List[Dict[str, str]] = []
    for node_id, out in outs.items():
        for img in out.get("images", []) or []:
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
    ap.add_argument("--template", default=str(Path(__file__).with_name("flux2_dev_prompt_template.json")))
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--guidance", type=float, default=4.0)
    ap.add_argument("--sampler", default="euler")
    ap.add_argument("--seed", type=int, default=-1, help="-1 => random")
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--filename-prefix", default="Flux2")
    ap.add_argument("--text-encoder", default="mistral_3_small_flux2_bf16.safetensors")
    ap.add_argument("--unet", default="flux2_dev_fp8mixed.safetensors")
    ap.add_argument("--vae", default="flux2-vae.safetensors")
    ap.add_argument("--out", default="./comfy_outputs")
    args = ap.parse_args()

    seed = args.seed if args.seed != -1 else random.randrange(0, 2**63)

    prompt = load_template(args.template)
    # batch_size lives in EmptyFlux2LatentImage
    prompt["47"]["inputs"]["batch_size"] = int(args.batch)

    set_common_params(
        prompt,
        text=args.prompt,
        width=args.width,
        height=args.height,
        steps=args.steps,
        guidance=args.guidance,
        seed=seed,
        sampler_name=args.sampler,
        filename_prefix=args.filename_prefix,
        text_encoder=args.text_encoder,
        unet=args.unet,
        vae=args.vae,
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
