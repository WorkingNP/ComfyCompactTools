#!/usr/bin/env python3
"""
Capture fixtures from a running ComfyUI/Cockpit instance for offline testing.

This script connects to the cockpit server, runs a generation with a specified
workflow, and saves the responses as fixtures for offline testing.

Usage:
    python scripts/capture_fixtures.py \
        --workflow-id flux2_klein_distilled \
        --prompt "a cute cat sitting on a windowsill" \
        --output tests/fixtures/

Requirements:
    - ComfyUI must be running (default: http://127.0.0.1:8188)
    - Cockpit server must be running (default: http://127.0.0.1:8787)

Output Structure:
    <output_dir>/<timestamp>_<workflow_id>/
        capture_meta.json    - Capture metadata (timestamp, status, workflow_id)
        request.json         - The job request payload sent to the server
        object_info.json     - ComfyUI node definitions
        job_response.json    - Initial job creation response
        job_final.json       - Final job state (success or failure)
        sample_output.png    - Generated image (if successful)
        error_summary.txt    - Error details (if failed)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx


class CaptureContext:
    """Context for fixture capture with automatic error handling."""

    def __init__(self, output_dir: Path, workflow_id: str):
        self.output_dir = output_dir
        self.workflow_id = workflow_id
        self.start_time = datetime.now()
        self.errors: list[str] = []
        self.status = "in_progress"
        self.job_id: Optional[str] = None

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, filename: str, data: Any) -> Path:
        """Save JSON data to a file."""
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def save_text(self, filename: str, text: str) -> Path:
        """Save text to a file."""
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def save_bytes(self, filename: str, data: bytes) -> Path:
        """Save binary data to a file."""
        path = self.output_dir / filename
        with open(path, "wb") as f:
            f.write(data)
        return path

    def add_error(self, error: str, exception: Optional[Exception] = None):
        """Record an error."""
        error_msg = error
        if exception:
            error_msg += f"\n  Exception: {type(exception).__name__}: {exception}"
            error_msg += f"\n  Traceback:\n{traceback.format_exc()}"
        self.errors.append(error_msg)

    def save_meta(self):
        """Save capture metadata."""
        meta = {
            "workflow_id": self.workflow_id,
            "timestamp": self.start_time.isoformat(),
            "timestamp_unix": self.start_time.timestamp(),
            "status": self.status,
            "job_id": self.job_id,
            "errors": self.errors,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
        }
        self.save_json("capture_meta.json", meta)

    def save_error_summary(self):
        """Save error summary to text file."""
        if self.errors:
            summary = f"Capture Failed: {self.workflow_id}\n"
            summary += f"Timestamp: {self.start_time.isoformat()}\n"
            summary += f"Job ID: {self.job_id or 'N/A'}\n"
            summary += "=" * 50 + "\n\n"
            for i, error in enumerate(self.errors, 1):
                summary += f"Error {i}:\n{error}\n\n"
            self.save_text("error_summary.txt", summary)


def get_object_info(comfy_url: str) -> dict:
    """GET /object_info from ComfyUI."""
    url = f"{comfy_url.rstrip('/')}/object_info"
    r = httpx.get(url, timeout=30.0)
    r.raise_for_status()
    return r.json()


def create_job(server_url: str, payload: dict) -> tuple[dict, httpx.Response]:
    """Create a job via the cockpit server. Returns (response_json, raw_response)."""
    url = f"{server_url.rstrip('/')}/api/jobs"
    r = httpx.post(url, json=payload, timeout=60.0)
    r.raise_for_status()
    return r.json(), r


def get_job_status(server_url: str, job_id: str) -> Optional[dict]:
    """Get current job status."""
    url = f"{server_url.rstrip('/')}/api/jobs"
    r = httpx.get(url, timeout=10.0)
    r.raise_for_status()
    jobs = r.json()
    return next((j for j in jobs if j["id"] == job_id), None)


def wait_for_job(
    server_url: str, job_id: str, timeout_s: float = 300
) -> tuple[dict, str]:
    """Poll until job completes or fails. Returns (job_data, status)."""
    t0 = time.time()
    while True:
        job = get_job_status(server_url, job_id)
        if job:
            if job["status"] == "completed":
                return job, "completed"
            if job["status"] == "failed":
                return job, "failed"
        elapsed = time.time() - t0
        if elapsed > timeout_s:
            return job or {}, "timeout"
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


def generate_output_dir(base_dir: Path, workflow_id: str) -> Path:
    """Generate timestamped output directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / f"{timestamp}_{workflow_id}"


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
        help="Base output directory for fixtures (timestamp subdirectory will be created)",
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
    ap.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Don't create timestamped subdirectory (use output dir directly)",
    )

    args = ap.parse_args()

    # Determine output directory
    base_dir = Path(args.output)
    if args.no_timestamp:
        output_dir = base_dir
    else:
        output_dir = generate_output_dir(base_dir, args.workflow_id)

    # Create capture context
    ctx = CaptureContext(output_dir, args.workflow_id)

    print(f"Capturing fixtures for workflow: {args.workflow_id}")
    print(f"Output directory: {output_dir}")
    print()

    # Build request payload
    request_payload = {
        "prompt": args.prompt,
        "workflow_id": args.workflow_id,
        "width": args.width,
        "height": args.height,
        "steps": args.steps,
    }

    # Save request immediately
    ctx.save_json("request.json", request_payload)
    print(f"  Saved: request.json")

    # 1. Capture object_info from ComfyUI
    print("[1/5] Fetching /object_info from ComfyUI...")
    try:
        object_info = get_object_info(args.comfy_url)
        ctx.save_json("object_info.json", object_info)
        print(f"  Saved: object_info.json")
    except Exception as e:
        ctx.add_error(f"Failed to connect to ComfyUI at {args.comfy_url}", e)
        print(f"  ERROR: {e}")
        # Continue anyway - we can still try the server

    # 2. Check server is running
    print("[2/5] Checking cockpit server...")
    try:
        r = httpx.get(f"{args.server_url}/api/health", timeout=5.0)
        if r.status_code != 200:
            raise RuntimeError(f"Server returned {r.status_code}")
        print(f"  Server is up at {args.server_url}")
    except Exception as e:
        ctx.add_error(f"Failed to connect to server at {args.server_url}", e)
        ctx.status = "failed"
        ctx.save_meta()
        ctx.save_error_summary()
        print(f"  ERROR: {e}")
        return 1

    # 3. Create a job
    print("[3/5] Creating job...")
    try:
        job_response, raw_response = create_job(args.server_url, request_payload)
        ctx.job_id = job_response.get("id")
        ctx.save_json("job_response.json", job_response)
        print(f"  Job created: {ctx.job_id}")
        print(f"  Saved: job_response.json")
    except httpx.HTTPStatusError as e:
        ctx.add_error(
            f"Failed to create job: HTTP {e.response.status_code}\nResponse: {e.response.text}",
            e,
        )
        ctx.status = "failed"
        ctx.save_meta()
        ctx.save_error_summary()
        print(f"  ERROR: {e.response.status_code}")
        return 1
    except Exception as e:
        ctx.add_error(f"Failed to create job", e)
        ctx.status = "failed"
        ctx.save_meta()
        ctx.save_error_summary()
        print(f"  ERROR: {e}")
        return 1

    # 4. Wait for completion
    print("[4/5] Waiting for job completion...")
    try:
        final_job, job_status = wait_for_job(
            args.server_url, ctx.job_id, args.timeout
        )
        ctx.save_json("job_final.json", final_job)
        print(f"  Saved: job_final.json")

        if job_status == "completed":
            print(f"  Job completed!")
        elif job_status == "failed":
            error_msg = final_job.get("error", "Unknown error")
            ctx.add_error(f"Job failed: {error_msg}")
            ctx.status = "failed"
            ctx.save_meta()
            ctx.save_error_summary()
            print(f"  ERROR: Job failed: {error_msg}")
            return 1
        elif job_status == "timeout":
            ctx.add_error(f"Job {ctx.job_id} did not complete within {args.timeout}s")
            ctx.status = "timeout"
            ctx.save_meta()
            ctx.save_error_summary()
            print(f"  ERROR: Timeout")
            return 1
    except Exception as e:
        ctx.add_error(f"Error waiting for job completion", e)
        ctx.status = "failed"
        ctx.save_meta()
        ctx.save_error_summary()
        print(f"  ERROR: {e}")
        return 1

    # 5. Download and save image
    print("[5/5] Downloading generated image...")
    try:
        assets = get_job_assets(args.server_url, ctx.job_id)
        if not assets:
            ctx.add_error("No assets found for job")
            ctx.status = "failed"
            ctx.save_meta()
            ctx.save_error_summary()
            print("  ERROR: No assets found")
            return 1

        asset = assets[0]
        asset_url = asset.get("url")
        if not asset_url:
            ctx.add_error("Asset has no URL")
            ctx.status = "failed"
            ctx.save_meta()
            ctx.save_error_summary()
            print("  ERROR: Asset has no URL")
            return 1

        image_bytes = download_asset(args.server_url, asset_url)
        ctx.save_bytes("sample_output.png", image_bytes)
        print(f"  Saved: sample_output.png ({len(image_bytes)} bytes)")

        # Save asset metadata
        ctx.save_json("assets.json", assets)
        print(f"  Saved: assets.json")

    except Exception as e:
        ctx.add_error(f"Failed to download image", e)
        ctx.status = "failed"
        ctx.save_meta()
        ctx.save_error_summary()
        print(f"  ERROR: {e}")
        return 1

    # Success!
    ctx.status = "completed"
    ctx.save_meta()

    print()
    print("=" * 50)
    print("Fixture capture complete!")
    print(f"  Workflow: {args.workflow_id}")
    print(f"  Directory: {output_dir}")
    print("  Files:")
    for f in sorted(output_dir.iterdir()):
        print(f"    - {f.name}")
    print()
    print("Run offline tests with:")
    print(f"  pytest server/tests/ -v -m 'not e2e'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
