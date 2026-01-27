"""
MCP tools for Cockpit image generation.

These tools are designed to be called by LLMs via MCP protocol.
All tools accept a CockpitApiClient for dependency injection (testability).
"""

import time
from typing import Any, Dict, List, Optional
from .cockpit_api_client import CockpitApiClient


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


def images_generate(
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
    if params is None:
        params = {}

    # Create jobs
    jobs = []
    for i in range(count):
        job_params = params.copy()
        # If seed not specified or -1, let server generate random seeds
        # If seed is specified, increment for each additional job
        if count > 1 and "seed" in job_params and job_params["seed"] >= 0:
            job_params["seed"] = job_params["seed"] + i

        job = client.create_job(workflow_id, job_params)
        jobs.append({
            "job_id": job["id"],
            "status": job["status"],
            "outputs": [],
            "error": job.get("error"),
        })

    # If wait=True, poll until completion
    if wait:
        start_time = time.time()
        while True:
            all_done = True
            for job_info in jobs:
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

            time.sleep(2)  # Poll every 2 seconds

    return {
        "jobs": jobs,
        "ui_url": f"{base_url}/",
    }


def images_generate_many(
    client: CockpitApiClient,
    prompts: List[str],
    workflow_id: str = "flux2_klein_distilled",
    base_params: Optional[Dict[str, Any]] = None,
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
    if base_params is None:
        base_params = {}

    results = []
    for prompt in prompts:
        params = base_params.copy()
        params["prompt"] = prompt

        # Generate single image (wait=False initially)
        job = client.create_job(workflow_id, params)
        results.append({
            "prompt": prompt,
            "job_id": job["id"],
            "status": job["status"],
            "outputs": [],
            "error": job.get("error"),
        })

    # Poll all jobs
    start_time = time.time()
    while True:
        all_done = True
        for result in results:
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

        time.sleep(2)

    return {
        "results": results,
        "ui_url": f"{base_url}/",
    }
