"""
MCP tools for Cockpit image generation.

These tools are designed to be called by LLMs via MCP protocol.
All tools accept a CockpitApiClient for dependency injection (testability).
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from .cockpit_api_client import CockpitApiClient

POLL_INTERVAL_SEC = 2
MAX_COUNT = 100
MAX_PROMPTS = 50


def _coerce_seed(job_params: Dict[str, Any]) -> None:
    """Coerce seed to int, raise if invalid."""
    if "seed" in job_params:
        seed = job_params["seed"]
        if isinstance(seed, bool):
            raise ValueError("seed must be an integer, got bool")
        if not isinstance(seed, int):
            try:
                job_params["seed"] = int(seed)
            except (ValueError, TypeError):
                raise ValueError(
                    f"seed must be an integer, got {type(seed).__name__}"
                )


def _validate_count(count: int) -> None:
    """Validate count parameter."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer")
    if count < 1 or count > MAX_COUNT:
        raise ValueError(f"count must be between 1 and {MAX_COUNT}")


def _validate_prompts(prompts: List[str]) -> None:
    """Validate prompts list."""
    if len(prompts) > MAX_PROMPTS:
        raise ValueError(f"prompts length must not exceed {MAX_PROMPTS}")
    for i, prompt in enumerate(prompts):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"prompts[{i}] is empty or not a string")


def workflows_list(client: CockpitApiClient) -> Dict[str, Any]:
    """
    List all available workflows.

    Returns:
        {
            "workflows": [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "version": str,
                },
                ...
            ]
        }
    """
    workflows = client.list_workflows()
    return {"workflows": workflows}


def workflow_get(client: CockpitApiClient, workflow_id: str) -> Dict[str, Any]:
    """
    Get details about a specific workflow.

    Args:
        workflow_id: The workflow ID to retrieve

    Returns:
        {
            "id": str,
            "name": str,
            "description": str,
            "version": str,
            "params": dict,  # Parameter schema for UI generation
            "presets": dict,
        }

    Raises:
        Exception if workflow not found
    """
    return client.get_workflow(workflow_id)


async def images_generate(
    client: CockpitApiClient,
    workflow_id: str = "flux2_klein_distilled",
    params: Optional[Dict[str, Any]] = None,
    count: int = 1,
    wait: bool = True,
    timeout_sec: int = 600,
    base_url: str = "http://127.0.0.1:8787",
) -> Dict[str, Any]:
    """
    Generate images using a workflow.

    Args:
        client: The CockpitApiClient instance
        workflow_id: The workflow to use (default: flux2_klein_distilled)
        params: Parameters for the workflow (e.g., {"prompt": "a cat", "seed": 42})
        count: Number of images to generate with same params (different seeds)
        wait: If True, poll until jobs complete. If False, return immediately.
        timeout_sec: Maximum time to wait for completion (seconds)
        base_url: Base URL of the Cockpit server (for constructing asset URLs)

    Returns:
        {
            "jobs": [
                {
                    "job_id": str,
                    "status": str,
                    "outputs": [str, ...],  # Asset URLs (if completed)
                    "error": str | None,
                },
                ...
            ],
            "ui_url": str,  # URL to view results in the UI
        }
    """
    # Validate count
    _validate_count(count)

    if params is None:
        params = {}

    # Create jobs with partial failure handling
    jobs = []
    for i in range(count):
        job_params = params.copy()
        # Remove workflow_id from params to prevent collision
        job_params.pop("workflow_id", None)
        # Coerce and validate seed
        _coerce_seed(job_params)
        # If seed not specified or -1, let server generate random seeds
        # If seed is specified, increment for each additional job
        if count > 1 and "seed" in job_params and job_params["seed"] >= 0:
            job_params["seed"] = job_params["seed"] + i

        try:
            job = client.create_job(workflow_id, job_params)
            jobs.append({
                "job_id": job["id"],
                "status": job["status"],
                "outputs": [],
                "error": job.get("error"),
            })
        except Exception as e:
            jobs.append({
                "job_id": None,
                "status": "failed",
                "outputs": [],
                "error": f"Job creation failed: {str(e)}",
            })

    # If wait=True, poll until completion
    if wait:
        start_time = time.time()
        max_iterations = timeout_sec // POLL_INTERVAL_SEC + 10
        iterations = 0
        while True:
            iterations += 1
            if iterations > max_iterations:
                # Force timeout to prevent infinite loop
                for job_info in jobs:
                    if job_info["status"] not in ("completed", "failed"):
                        job_info["status"] = "timeout"
                        job_info["error"] = f"Max iterations reached ({max_iterations})"
                break

            all_done = True
            for job_info in jobs:
                # Skip failed jobs (no job_id)
                if job_info["job_id"] is None:
                    continue
                if job_info["status"] in ("queued", "running") or (
                    job_info["status"] == "completed" and not job_info["outputs"]
                ):
                    # Poll job status
                    job_id = job_info["job_id"]
                    try:
                        job_status = client.get_job(job_id)
                        job_info["status"] = job_status["status"]
                        job_info["error"] = job_status.get("error")
                        if job_status["status"] == "completed":
                            # Extract asset URLs
                            outputs = job_status.get("outputs", [])
                            # Convert to full URLs
                            asset_urls = []
                            for output in outputs:
                                if isinstance(output, dict) and "filename" in output:
                                    filename = output["filename"]
                                    asset_urls.append(f"{base_url}/assets/{filename}")
                                elif isinstance(output, str):
                                    # Already a URL or filename
                                    if output.startswith("http"):
                                        asset_urls.append(output)
                                    else:
                                        asset_urls.append(f"{base_url}/assets/{output}")
                            if asset_urls:
                                job_info["outputs"] = asset_urls
                    except Exception as e:
                        job_info["status"] = "failed"
                        job_info["error"] = str(e)

                if job_info["status"] not in ("completed", "failed") or (
                    job_info["status"] == "completed" and not job_info["outputs"]
                ):
                    all_done = False

            if all_done:
                break

            # Check timeout
            if time.time() - start_time > timeout_sec:
                # Timeout - return partial results
                for job_info in jobs:
                    if job_info["status"] not in ("completed", "failed"):
                        job_info["status"] = "timeout"
                        job_info["error"] = f"Timeout after {timeout_sec}s"
                break

            await asyncio.sleep(POLL_INTERVAL_SEC)  # Non-blocking sleep

    return {
        "jobs": jobs,
        "ui_url": f"{base_url}/",
    }


async def images_generate_many(
    client: CockpitApiClient,
    prompts: List[str],
    workflow_id: str = "flux2_klein_distilled",
    base_params: Optional[Dict[str, Any]] = None,
    wait: bool = True,
    timeout_sec: int = 600,
    base_url: str = "http://127.0.0.1:8787",
) -> Dict[str, Any]:
    """
    Generate multiple images with different prompts in batch.

    This is a convenience function for generating images with multiple different prompts
    (e.g., when an LLM wants to generate 10 variations of a concept).

    Args:
        client: The CockpitApiClient instance
        prompts: List of prompts to generate (e.g., ["a cat", "a dog", "a tree"])
        workflow_id: The workflow to use (default: flux2_klein_distilled)
        base_params: Base parameters to merge with each prompt (e.g., {"width": 512})
        wait: If True, poll until all jobs complete. If False, return immediately.
        timeout_sec: Maximum time to wait for all jobs to complete
        base_url: Base URL of the Cockpit server

    Returns:
        {
            "results": [
                {
                    "prompt": str,
                    "job_id": str,
                    "status": str,
                    "outputs": [str, ...],  # Asset URLs
                    "error": str | None,
                },
                ...
            ],
            "ui_url": str,
        }
    """
    # Validate prompts
    _validate_prompts(prompts)

    if base_params is None:
        base_params = {}

    results = []
    for prompt in prompts:
        params = base_params.copy()
        # Remove workflow_id from params to prevent collision
        params.pop("workflow_id", None)
        params["prompt"] = prompt

        try:
            # Generate single image (wait=False initially)
            job = client.create_job(workflow_id, params)
            results.append({
                "prompt": prompt,
                "job_id": job["id"],
                "status": job["status"],
                "outputs": [],
                "error": job.get("error"),
            })
        except Exception as e:
            results.append({
                "prompt": prompt,
                "job_id": None,
                "status": "failed",
                "outputs": [],
                "error": f"Job creation failed: {str(e)}",
            })

    if not wait:
        return {
            "results": results,
            "ui_url": f"{base_url}/",
        }

    # Poll all jobs
    start_time = time.time()
    max_iterations = timeout_sec // POLL_INTERVAL_SEC + 10
    iterations = 0
    while True:
        iterations += 1
        if iterations > max_iterations:
            # Force timeout to prevent infinite loop
            for result in results:
                if result["status"] not in ("completed", "failed"):
                    result["status"] = "timeout"
                    result["error"] = f"Max iterations reached ({max_iterations})"
            break

        all_done = True
        for result in results:
            # Skip failed jobs (no job_id)
            if result["job_id"] is None:
                continue
            if result["status"] in ("queued", "running") or (
                result["status"] == "completed" and not result["outputs"]
            ):
                job_id = result["job_id"]
                try:
                    job_status = client.get_job(job_id)
                    result["status"] = job_status["status"]
                    result["error"] = job_status.get("error")
                    if job_status["status"] == "completed":
                        outputs = job_status.get("outputs", [])
                        asset_urls = []
                        for output in outputs:
                            if isinstance(output, dict) and "filename" in output:
                                filename = output["filename"]
                                asset_urls.append(f"{base_url}/assets/{filename}")
                            elif isinstance(output, str):
                                if output.startswith("http"):
                                    asset_urls.append(output)
                                else:
                                    asset_urls.append(f"{base_url}/assets/{output}")
                        if asset_urls:
                            result["outputs"] = asset_urls
                except Exception as e:
                    result["status"] = "failed"
                    result["error"] = str(e)

            if result["status"] not in ("completed", "failed") or (
                result["status"] == "completed" and not result["outputs"]
            ):
                all_done = False

        if all_done:
            break

        if time.time() - start_time > timeout_sec:
            # Timeout
            for result in results:
                if result["status"] not in ("completed", "failed"):
                    result["status"] = "timeout"
                    result["error"] = f"Timeout after {timeout_sec}s"
            break

        await asyncio.sleep(POLL_INTERVAL_SEC)  # Non-blocking sleep

    return {
        "results": results,
        "ui_url": f"{base_url}/",
    }
