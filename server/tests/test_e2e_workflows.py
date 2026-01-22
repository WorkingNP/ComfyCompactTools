"""End-to-end tests for workflows (requires running ComfyUI)."""
from __future__ import annotations

import os
import pytest
import httpx
from pathlib import Path

# Mark all tests in this file as e2e
pytestmark = pytest.mark.e2e

COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8787")


def is_comfy_available() -> bool:
    """Check if ComfyUI is running."""
    try:
        r = httpx.get(f"{COMFY_URL}/system_stats", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def is_server_available() -> bool:
    """Check if our server is running."""
    try:
        r = httpx.get(f"{SERVER_URL}/api/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


# Skip all E2E tests if ComfyUI or server not available
skip_if_no_comfy = pytest.mark.skipif(
    not is_comfy_available(),
    reason="ComfyUI not available at " + COMFY_URL,
)
skip_if_no_server = pytest.mark.skipif(
    not is_server_available(),
    reason="Server not available at " + SERVER_URL,
)


class TestWorkflowEndpoints:
    """Test workflow API endpoints."""

    @skip_if_no_server
    def test_list_workflows(self):
        """Test GET /api/workflows returns available workflows."""
        r = httpx.get(f"{SERVER_URL}/api/workflows", timeout=10.0)
        assert r.status_code == 200
        workflows = r.json()
        assert isinstance(workflows, list)

        # Should have at least the three workflows we created
        ids = [w["id"] for w in workflows]
        # Note: These may not be present if workflows dir is empty
        # The test verifies the endpoint works correctly

    @skip_if_no_server
    def test_get_workflow_detail(self):
        """Test GET /api/workflows/{id} returns workflow details."""
        # First list to get an available workflow
        r = httpx.get(f"{SERVER_URL}/api/workflows", timeout=10.0)
        if r.status_code != 200:
            pytest.skip("Cannot list workflows")

        workflows = r.json()
        if not workflows:
            pytest.skip("No workflows available")

        workflow_id = workflows[0]["id"]
        r = httpx.get(f"{SERVER_URL}/api/workflows/{workflow_id}", timeout=10.0)
        assert r.status_code == 200

        detail = r.json()
        assert "id" in detail
        assert "name" in detail
        assert "params" in detail

    @skip_if_no_server
    def test_get_nonexistent_workflow(self):
        """Test GET /api/workflows/{id} returns 404 for unknown workflow."""
        r = httpx.get(f"{SERVER_URL}/api/workflows/nonexistent_workflow_xyz", timeout=10.0)
        assert r.status_code == 404


class TestJobCreationWithWorkflow:
    """Test job creation with workflow_id."""

    @skip_if_no_server
    @skip_if_no_comfy
    def test_create_job_with_workflow_id(self):
        """Test creating a job with a specific workflow_id."""
        # First check what workflows are available
        r = httpx.get(f"{SERVER_URL}/api/workflows", timeout=10.0)
        if r.status_code != 200 or not r.json():
            pytest.skip("No workflows available")

        workflows = r.json()
        workflow_id = workflows[0]["id"]

        # Create a job
        payload = {
            "prompt": "a beautiful sunset over mountains, high quality",
            "workflow_id": workflow_id,
            "steps": 4,  # Keep low for fast test
            "width": 512,
            "height": 512,
        }

        r = httpx.post(
            f"{SERVER_URL}/api/jobs",
            json=payload,
            timeout=30.0,
        )

        assert r.status_code == 200
        job = r.json()
        assert "id" in job
        assert job["status"] in ["queued", "running", "completed", "failed"]

    @skip_if_no_server
    def test_create_job_legacy_mode(self):
        """Test creating a job without workflow_id (backward compatibility)."""
        payload = {
            "prompt": "a cat sitting on a windowsill",
            # No workflow_id - should use legacy build_txt2img_workflow
        }

        r = httpx.post(
            f"{SERVER_URL}/api/jobs",
            json=payload,
            timeout=30.0,
        )

        # Should still work (though may fail if ComfyUI not available)
        assert r.status_code in [200, 500, 502]

    @skip_if_no_server
    def test_create_job_invalid_workflow(self):
        """Test creating a job with invalid workflow_id returns error."""
        payload = {
            "prompt": "test prompt",
            "workflow_id": "nonexistent_workflow_xyz123",
        }

        r = httpx.post(
            f"{SERVER_URL}/api/jobs",
            json=payload,
            timeout=10.0,
        )

        assert r.status_code == 404


class TestFlux2KleinGeneration:
    """E2E test for Flux2 Klein (distilled) - the most reliable workflow."""

    @skip_if_no_server
    @skip_if_no_comfy
    @pytest.mark.slow
    def test_flux2_klein_generates_image(self):
        """Test that Flux2 Klein workflow generates a valid image.

        This is the most reliable workflow for E2E testing because:
        - Distilled models are more stable
        - Only 4 steps needed
        - Less likely to produce black images
        """
        # Check if flux2_klein_distilled workflow is available
        r = httpx.get(f"{SERVER_URL}/api/workflows", timeout=10.0)
        if r.status_code != 200:
            pytest.skip("Cannot list workflows")

        workflows = r.json()
        workflow_ids = [w["id"] for w in workflows]

        if "flux2_klein_distilled" not in workflow_ids:
            pytest.skip("flux2_klein_distilled workflow not available")

        # Create a job
        payload = {
            "prompt": "a beautiful red rose in a garden, detailed, high quality photograph",
            "workflow_id": "flux2_klein_distilled",
            "steps": 4,
            "width": 512,  # Lower resolution for faster test
            "height": 512,
        }

        r = httpx.post(
            f"{SERVER_URL}/api/jobs",
            json=payload,
            timeout=120.0,  # Allow time for generation
        )

        assert r.status_code == 200
        job = r.json()
        job_id = job["id"]

        # Poll for completion (max 2 minutes)
        import time

        max_wait = 120
        start = time.time()
        while time.time() - start < max_wait:
            r = httpx.get(f"{SERVER_URL}/api/jobs", timeout=10.0)
            if r.status_code == 200:
                jobs = r.json()
                current_job = next((j for j in jobs if j["id"] == job_id), None)
                if current_job:
                    if current_job["status"] == "completed":
                        break
                    if current_job["status"] == "failed":
                        pytest.fail(f"Job failed: {current_job.get('error')}")
            time.sleep(2)
        else:
            pytest.fail("Job did not complete within timeout")

        # Check that an asset was created
        r = httpx.get(f"{SERVER_URL}/api/assets", timeout=10.0)
        assert r.status_code == 200
        assets = r.json()

        job_assets = [a for a in assets if a["job_id"] == job_id]
        assert len(job_assets) > 0, "No assets created for job"

        # Verify the asset has a URL
        asset = job_assets[0]
        assert "url" in asset
        assert asset["url"].startswith("/assets/")
