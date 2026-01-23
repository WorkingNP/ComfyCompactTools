#!/usr/bin/env python3
"""
Record fixtures from a running ComfyUI instance for offline testing.

This script connects to ComfyUI, runs a generation, and saves:
- object_info.json: Node definitions from GET /object_info
- history_success.json: History response from GET /history/{prompt_id}
- sample_output.png: Generated image from GET /view

Usage:
    python tools/record_fixtures.py \
        --base-url http://127.0.0.1:8188 \
        --template flux2_klein_4b_fp8_prompt_template.json \
        --prompt "a cute cat sitting on a windowsill" \
        --profile klein_distilled_fp8

    # With custom parameters:
    python tools/record_fixtures.py \
        --template flux2_klein_4b_fp8_prompt_template.json \
        --prompt "a beautiful landscape" \
        --profile klein_distilled_fp8 \
        --width 512 --height 512 --steps 4 --cfg 1.0 --seed 12345
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from pathlib import Path

import requests


def get_object_info(base_url: str) -> dict:
    """GET /object_info - retrieve node definitions."""
    url = f"{base_url.rstrip('/')}/object_info"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def load_template(path: str) -> dict:
    """Load JSON template file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_params(
    prompt: dict,
    *,
    text: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    cfg: float = 1.0,
    seed: int = 0,
    batch: int = 1,
) -> None:
    """Apply parameters to the prompt template."""
    # Prompts (nodes 2 and 3)
    if "2" in prompt and "inputs" in prompt["2"]:
        prompt["2"]["inputs"]["text"] = text
    if "3" in prompt and "inputs" in prompt["3"]:
        prompt["3"]["inputs"]["text"] = negative

    # CFG (node 5)
    if "5" in prompt and "inputs" in prompt["5"]:
        prompt["5"]["inputs"]["cfg"] = float(cfg)

    # Seed (node 6)
    if "6" in prompt and "inputs" in prompt["6"]:
        prompt["6"]["inputs"]["noise_seed"] = int(seed)

    # Resolution and batch (node 7)
    if "7" in prompt and "inputs" in prompt["7"]:
        prompt["7"]["inputs"]["width"] = int(width)
        prompt["7"]["inputs"]["height"] = int(height)
        prompt["7"]["inputs"]["batch_size"] = int(batch)

    # Steps and resolution (node 8)
    if "8" in prompt and "inputs" in prompt["8"]:
        prompt["8"]["inputs"]["steps"] = int(steps)
        prompt["8"]["inputs"]["width"] = int(width)
        prompt["8"]["inputs"]["height"] = int(height)


def queue_prompt(base_url: str, prompt: dict, client_id: str) -> str:
    """POST /prompt - queue a generation and return prompt_id."""
    url = f"{base_url.rstrip('/')}/prompt"
    payload = {"prompt": prompt, "client_id": client_id}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "prompt_id" not in data:
        raise RuntimeError(f"Queue failed: {data}")
    return data["prompt_id"]


def wait_history(
    base_url: str,
    prompt_id: str,
    *,
    poll_interval: float = 1.0,
    timeout_s: float = 600,
) -> dict:
    """Poll GET /history/{prompt_id} until completion."""
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    t0 = time.time()
    while True:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        hist = r.json()
        if isinstance(hist, dict) and prompt_id in hist:
            return hist[prompt_id]
        elapsed = time.time() - t0
        if elapsed > timeout_s:
            raise TimeoutError(
                f"Timed out waiting for prompt_id={prompt_id} after {elapsed:.1f}s"
            )
        print(f"  waiting... ({elapsed:.1f}s)", end="\r")
        time.sleep(poll_interval)


def extract_first_image(history_item: dict) -> dict | None:
    """Extract first image metadata from history outputs."""
    outputs = history_item.get("outputs", {})
    for node_id, out in outputs.items():
        for img in out.get("images", []) or []:
            if all(k in img for k in ("filename", "subfolder", "type")):
                return {
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                }
    return None


def download_image(base_url: str, img_meta: dict) -> bytes:
    """GET /view - download image bytes."""
    params = {
        "filename": img_meta["filename"],
        "subfolder": img_meta.get("subfolder", ""),
        "type": img_meta.get("type", "output"),
    }
    url = f"{base_url.rstrip('/')}/view"
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.content


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Record fixtures from ComfyUI for offline testing"
    )
    ap.add_argument(
        "--base-url",
        default="http://127.0.0.1:8188",
        help="ComfyUI API base URL",
    )
    ap.add_argument(
        "--template",
        required=True,
        help="Path to prompt template JSON",
    )
    ap.add_argument(
        "--prompt",
        required=True,
        help="Text prompt for generation",
    )
    ap.add_argument(
        "--profile",
        required=True,
        help="Profile name (fixture folder name under tests/fixtures/)",
    )
    ap.add_argument("--negative", default="", help="Negative prompt")
    ap.add_argument("--width", type=int, default=512, help="Image width")
    ap.add_argument("--height", type=int, default=512, help="Image height")
    ap.add_argument("--steps", type=int, default=4, help="Sampling steps")
    ap.add_argument("--cfg", type=float, default=1.0, help="CFG scale")
    ap.add_argument("--seed", type=int, default=-1, help="Seed (-1 for random)")
    ap.add_argument("--batch", type=int, default=1, help="Batch size")
    ap.add_argument(
        "--timeout",
        type=float,
        default=600,
        help="Timeout in seconds for generation",
    )

    args = ap.parse_args()

    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    template_path = Path(args.template)
    if not template_path.is_absolute():
        template_path = repo_root / template_path

    fixtures_dir = repo_root / "tests" / "fixtures" / args.profile
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    print(f"Recording fixtures to: {fixtures_dir}")
    print(f"Template: {template_path}")
    print(f"ComfyUI URL: {args.base_url}")
    print()

    # 1. GET /object_info
    print("[1/6] Fetching /object_info...")
    try:
        object_info = get_object_info(args.base_url)
        object_info_path = fixtures_dir / "object_info.json"
        with open(object_info_path, "w", encoding="utf-8") as f:
            json.dump(object_info, f, indent=2)
        print(f"  Saved: {object_info_path}")
    except requests.RequestException as e:
        print(f"  ERROR: Failed to connect to ComfyUI: {e}")
        print("  Make sure ComfyUI is running and accessible.")
        return 1

    # 2. Load and patch template
    print("[2/6] Loading template...")
    if not template_path.exists():
        print(f"  ERROR: Template not found: {template_path}")
        return 1
    prompt = load_template(str(template_path))

    seed = args.seed if args.seed != -1 else random.randrange(0, 2**63)
    apply_params(
        prompt,
        text=args.prompt,
        negative=args.negative,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg=args.cfg,
        seed=seed,
        batch=args.batch,
    )
    print(f"  Prompt: {args.prompt[:50]}...")
    print(f"  Size: {args.width}x{args.height}, Steps: {args.steps}, CFG: {args.cfg}")
    print(f"  Seed: {seed}")

    # 3. POST /prompt
    print("[3/6] Queueing prompt...")
    client_id = str(uuid.uuid4())
    try:
        prompt_id = queue_prompt(args.base_url, prompt, client_id)
        print(f"  prompt_id: {prompt_id}")
    except requests.RequestException as e:
        print(f"  ERROR: Failed to queue prompt: {e}")
        return 1

    # 4. Poll /history until done
    print("[4/6] Waiting for generation...")
    try:
        history_item = wait_history(
            args.base_url,
            prompt_id,
            timeout_s=args.timeout,
        )
        print("  Generation complete!")
    except TimeoutError as e:
        print(f"  ERROR: {e}")
        return 1

    # 5. Save history
    print("[5/6] Saving history...")
    history_path = fixtures_dir / "history_success.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_item, f, indent=2)
    print(f"  Saved: {history_path}")

    # 6. Download and save image
    print("[6/6] Downloading image...")
    img_meta = extract_first_image(history_item)
    if not img_meta:
        print("  ERROR: No image found in history outputs")
        return 1

    try:
        img_bytes = download_image(args.base_url, img_meta)
        img_path = fixtures_dir / "sample_output.png"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        print(f"  Saved: {img_path} ({len(img_bytes)} bytes)")
    except requests.RequestException as e:
        print(f"  ERROR: Failed to download image: {e}")
        return 1

    print()
    print("=" * 50)
    print("Fixture recording complete!")
    print(f"  Profile: {args.profile}")
    print(f"  Directory: {fixtures_dir}")
    print("  Files:")
    for f in fixtures_dir.iterdir():
        print(f"    - {f.name}")
    print()
    print("Run offline tests with:")
    print("  pytest tests/test_offline_replay_from_fixtures.py -v")

    return 0


if __name__ == "__main__":
    sys.exit(main())
