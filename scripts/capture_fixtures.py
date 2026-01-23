#!/usr/bin/env python3
"""
Capture fixtures from a running ComfyUI/Cockpit instance for offline testing.

This script connects to the cockpit server, runs a generation with a specified
workflow, and saves the responses as fixtures for offline testing.

Usage:
    python scripts/capture_fixtures.py \
        --workflow-id flux2_klein_distilled \
        --prompt "a cute cat sitting on a windowsill" \
        --output tests/fixtures/flux2_klein_distilled/

Requirements:
    - ComfyUI must be running (default: http://127.0.0.1:8188)
    - Cockpit server must be running (default: http://127.0.0.1:8787)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def get_object_info(comfy_url: str) -> dict:
    """GET /object_info from ComfyUI."""
    url = f"{comfy_url.rstrip('/')}/object_info"
    r = httpx.get(url, timeout=30.0)
    r.raise_for_status()
    return r.json()


def create_job(server_url: str, workflow_id: str, prompt: str, **kwargs) -> dict:
    """Create a job via the cockpit server."""
    url = f"{server_url.rstrip('/')}/api/jobs"
    payload = {
        "prompt": prompt,
        "workflow_id": workflow_id,
        **kwargs,
    }
    r = httpx.post(url, json=payload, timeout=60.0)
    r.raise_for_status()
    return r.json()


def wait_for_job(server_url: str, job_id: str, timeout_s: float = 300) -> dict:
    """Poll until job completes or fails."""
    url = f"{server_url.rstrip('/')}/api/jobs"
    t0 = time.time()
    while True:
        r = httpx.get(url, timeout=10.0)
        r.raise_for_status()
        jobs = r.json()
        job = next((j for j in jobs if j["id"] == job_id), None)
        if job:
            if job["status"] == "completed":
                return job
            if job["status"] == "failed":
                raise RuntimeError(f"Job failed: {job.get('error', 'Unknown error')}")
        elapsed = time.time() - t0
        if elapsed > timeout_s:
            raise TimeoutError(f"Job {job_id} did not complete within {timeout_s}s")
        print(f"  Waiting... ({elapsed:.1f}s)", end="\r")
        time.sleep(2)


def get_job_assets(server_url: str, job_id: str) -> list:
    """Get assets for a job."""
    url = f"{server_url.rstrip('/')}/api/assets"
    r = httpx.get(url, timeout=10.0)
    r.raise_for_status()
    assets = r.json()
    return [a for a in assets if a.get("job_id") == job_id]


def download_asset(server_url: str, asset_url: str) -> bytes:
    """Download asset image bytes."""
    full_url = f"{server_url.rstrip('/')}{asset_url}"
    r = httpx.get(full_url, timeout=60.0)
    r.raise_for_status()
    return r.content


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Capture fixtures from ComfyUI/Cockpit for offline testing"
    )
    ap.add_argument(
        "--workflow-id",
        required=True,
        help="Workflow ID to test (e.g., flux2_klein_distilled)",
    )
    ap.add_argument(
        "--prompt",
        default="a test image, colorful, detailed",
        help="Prompt for generation",
    )
    ap.add_argument(
        "--output",
        required=True,
        help="Output directory for fixtures (e.g., tests/fixtures/flux2_klein_distilled/)",
    )
    ap.add_argument(
        "--comfy-url",
        default="http://127.0.0.1:8188",
        help="ComfyUI URL",
    )
    ap.add_argument(
        "--server-url",
        default="http://127.0.0.1:8787",
        help="Cockpit server URL",
    )
    ap.add_argument(
        "--width",
        type=int,
        default=512,
        help="Image width",
    )
    ap.add_argument(
        "--height",
        type=int,
        default=512,
        help="Image height",
    )
    ap.add_argument(
        "--steps",
        type=int,
        default=4,
        help="Sampling steps",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Timeout in seconds",
    )

    args = ap.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Capturing fixtures for workflow: {args.workflow_id}")
    print(f"Output directory: {output_dir}")
    print()

    # 1. Capture object_info from ComfyUI
    print("[1/5] Fetching /object_info from ComfyUI...")
    try:
        object_info = get_object_info(args.comfy_url)
        object_info_path = output_dir / "object_info.json"
        with open(object_info_path, "w", encoding="utf-8") as f:
            json.dump(object_info, f, indent=2)
        print(f"  Saved: {object_info_path}")
    except Exception as e:
        print(f"  ERROR: Failed to connect to ComfyUI: {e}")
        print(f"  Make sure ComfyUI is running at {args.comfy_url}")
        return 1

    # 2. Check server is running
    print("[2/5] Checking cockpit server...")
    try:
        r = httpx.get(f"{args.server_url}/api/health", timeout=5.0)
        if r.status_code != 200:
            raise RuntimeError(f"Server returned {r.status_code}")
        print(f"  Server is up at {args.server_url}")
    except Exception as e:
        print(f"  ERROR: Failed to connect to server: {e}")
        print(f"  Make sure the cockpit server is running at {args.server_url}")
        return 1

    # 3. Create a job
    print("[3/5] Creating job...")
    try:
        job = create_job(
            args.server_url,
            args.workflow_id,
            args.prompt,
            width=args.width,
            height=args.height,
            steps=args.steps,
        )
        job_id = job["id"]
        print(f"  Job created: {job_id}")
    except httpx.HTTPStatusError as e:
        print(f"  ERROR: Failed to create job: {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        return 1

    # 4. Wait for completion
    print("[4/5] Waiting for job completion...")
    try:
        completed_job = wait_for_job(args.server_url, job_id, args.timeout)
        print(f"  Job completed!")

        # Save job info as a mock history response
        history_path = output_dir / "history_success.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(completed_job, f, indent=2)
        print(f"  Saved: {history_path}")
    except TimeoutError as e:
        print(f"  ERROR: {e}")
        return 1
    except RuntimeError as e:
        print(f"  ERROR: {e}")
        return 1

    # 5. Download and save image
    print("[5/5] Downloading generated image...")
    assets = get_job_assets(args.server_url, job_id)
    if not assets:
        print("  ERROR: No assets found for job")
        return 1

    asset = assets[0]
    asset_url = asset.get("url")
    if not asset_url:
        print("  ERROR: Asset has no URL")
        return 1

    try:
        image_bytes = download_asset(args.server_url, asset_url)
        image_path = output_dir / "sample_output.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print(f"  Saved: {image_path} ({len(image_bytes)} bytes)")
    except Exception as e:
        print(f"  ERROR: Failed to download image: {e}")
        return 1

    print()
    print("=" * 50)
    print("Fixture capture complete!")
    print(f"  Workflow: {args.workflow_id}")
    print(f"  Directory: {output_dir}")
    print("  Files:")
    for f in output_dir.iterdir():
        print(f"    - {f.name}")
    print()
    print("Run offline tests with:")
    print(f"  pytest server/tests/ -v -m 'not e2e'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
