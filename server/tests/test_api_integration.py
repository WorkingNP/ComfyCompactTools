"""Integration tests for API endpoints (mock HTTP, no ComfyUI required)."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # We need to import after setting up mocks
    from server.main import app
    return TestClient(app)


class TestWorkflowsAPI:
    """Tests for /api/workflows endpoints."""

    def test_list_workflows_returns_list(self, test_client):
        """Test GET /api/workflows returns a list."""
        response = test_client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_workflows_contains_expected_fields(self, test_client):
        """Test that workflow list items have required fields."""
        response = test_client.get("/api/workflows")
        assert response.status_code == 200
        workflows = response.json()

        if workflows:  # Only test if there are workflows
            wf = workflows[0]
            assert "id" in wf
            assert "name" in wf

    def test_get_nonexistent_workflow_returns_404(self, test_client):
        """Test GET /api/workflows/{id} returns 404 for unknown ID."""
        response = test_client.get("/api/workflows/this_workflow_does_not_exist_xyz")
        assert response.status_code == 404

    def test_reload_workflows(self, test_client):
        """Test POST /api/workflows/reload works."""
        response = test_client.post("/api/workflows/reload")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "count" in data


class TestJobsAPIValidation:
    """Tests for /api/jobs validation."""

    def test_create_job_empty_prompt_fails(self, test_client):
        """Test that empty prompt returns 400."""
        response = test_client.post("/api/jobs", json={"prompt": ""})
        assert response.status_code == 422  # Pydantic validation error

    def test_create_job_missing_prompt_fails(self, test_client):
        """Test that missing prompt returns 422."""
        response = test_client.post("/api/jobs", json={})
        assert response.status_code == 422

    def test_create_job_invalid_workflow_id_fails(self, test_client):
        """Test that invalid workflow_id returns 404."""
        response = test_client.post(
            "/api/jobs",
            json={
                "prompt": "test prompt",
                "workflow_id": "nonexistent_workflow_xyz",
            },
        )
        assert response.status_code == 404


class TestManifestDefaults:
    """Tests for manifest default values."""

    def test_flux2_klein_has_different_defaults_than_legacy(self, test_client):
        """Test that flux2_klein_distilled manifest defaults differ from legacy defaults.

        Legacy defaults: steps=20, cfg=4.0, width=832
        flux2_klein_distilled should have: steps=4, cfg=1.0, width=1024
        """
        response = test_client.get("/api/workflows/flux2_klein_distilled")
        if response.status_code == 404:
            pytest.skip("flux2_klein_distilled workflow not available")

        manifest = response.json()
        params = manifest["params"]

        # Verify manifest has different defaults than legacy
        assert params["steps"]["default"] == 4, "steps should default to 4 for distilled model"
        assert params["cfg"]["default"] == 1.0, "cfg should default to 1.0 for distilled model"
        assert params["width"]["default"] == 1024, "width should default to 1024"

    def test_sd15_txt2img_manifest_defaults(self, test_client):
        """Test SD 1.5 manifest defaults are properly configured."""
        response = test_client.get("/api/workflows/sd15_txt2img")
        if response.status_code == 404:
            pytest.skip("sd15_txt2img workflow not available")

        manifest = response.json()
        params = manifest["params"]

        assert params["steps"]["default"] == 20
        assert params["cfg"]["default"] == 7.0
        assert params["width"]["default"] == 512


class TestHealthAndConfig:
    """Tests for health and config endpoints."""

    def test_health_endpoint(self, test_client):
        """Test GET /api/health returns ok."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_config_endpoint(self, test_client):
        """Test GET /api/config returns expected structure."""
        response = test_client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "comfy_url" in data
        assert "defaults" in data
        assert "choices" in data
