"""Integration tests for API endpoints (mock HTTP, no ComfyUI required)."""
from __future__ import annotations

import pytest
import uuid
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # We need to import after setting up mocks
    from server.main import app
    return TestClient(app)


@pytest.fixture
def fake_comfy_client():
    """Create a FakeComfyClient for testing."""
    from server.fake_comfy_client import FakeComfyClient
    return FakeComfyClient()


@pytest.fixture
def test_client_with_fake_comfy(fake_comfy_client):
    """Create a test client with FakeComfyClient injected."""
    from server import main
    from server.main import app

    # Save original client
    original_comfy = main.comfy

    # Inject fake client
    main.set_comfy_client(fake_comfy_client)

    client = TestClient(app)
    yield client

    # Restore original client
    main.set_comfy_client(original_comfy)


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

    def test_wan22_workflow_present(self, test_client):
        """wan2_2_ti2v_5b should be discoverable in workflows list."""
        response = test_client.get("/api/workflows")
        assert response.status_code == 200
        workflows = response.json()
        ids = [w["id"] for w in workflows]
        assert "wan2_2_ti2v_5b" in ids

    def test_wan22_workflow_detail_has_start_image(self, test_client):
        """wan2_2_ti2v_5b should expose image param for start_image."""
        response = test_client.get("/api/workflows/wan2_2_ti2v_5b")
        assert response.status_code == 200
        detail = response.json()
        params = detail.get("params", {})
        assert "start_image" in params
        assert params["start_image"]["type"] == "image"

    def test_flux2_klein_defaults_match_official(self, test_client):
        """flux2_klein_distilled defaults should match official template values."""
        response = test_client.get("/api/workflows/flux2_klein_distilled")
        if response.status_code == 404:
            pytest.skip("flux2_klein_distilled workflow not available")

        manifest = response.json()
        params = manifest["params"]

        expected_prompt = "masterpiece, best quality, high detail"
        expected_negative = (
            "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
            "missing fingers, deformed, disfigured, blurry, watermark, text, jpeg artifacts"
        )

        assert params["prompt"]["default"] == expected_prompt
        assert params["negative_prompt"]["default"] == expected_negative
        assert params["steps"]["default"] == 4
        assert params["cfg"]["default"] == 1.0
        assert params["width"]["default"] == 1024
        assert params["height"]["default"] == 1024

    def test_sdxl_manifest_defaults_match_official(self, test_client):
        """sdxl_txt2img defaults should match official template values."""
        response = test_client.get("/api/workflows/sdxl_txt2img")
        if response.status_code == 404:
            pytest.skip("sdxl_txt2img workflow not available")

        manifest = response.json()
        params = manifest["params"]

        assert params["prompt"]["default"] == "masterpiece, best quality, high detail"
        assert params["negative_prompt"]["default"] == (
            "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
            "missing fingers, deformed, disfigured, blurry, watermark, text, jpeg artifacts"
        )
        assert params["steps"]["default"] == 25
        assert params["cfg"]["default"] == 8.0
        assert params["sampler_name"]["default"] == "euler"
        assert params["scheduler"]["default"] == "normal"
        assert params["width"]["default"] == 1024
        assert params["height"]["default"] == 1024

    def test_wan22_defaults_match_recommended(self, test_client):
        """wan2_2_ti2v_5b defaults should match recommended settings."""
        response = test_client.get("/api/workflows/wan2_2_ti2v_5b")
        assert response.status_code == 200
        detail = response.json()
        params = detail.get("params", {})

        expected_prompt = "masterpiece, best quality, high detail"
        expected_negative = (
            "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
            "missing fingers, deformed, disfigured, blurry, watermark, text, jpeg artifacts"
        )

        assert params["width"]["default"] == 1280
        assert params["height"]["default"] == 704
        assert params["length"]["default"] == 121
        assert params["fps"]["default"] == 24
        assert params["steps"]["default"] == 20
        assert params["cfg"]["default"] == 5.0
        assert params["sampler_name"]["default"] == "uni_pc"
        assert params["scheduler"]["default"] == "simple"
        assert params["prompt"]["default"] == expected_prompt
        assert params["negative_prompt"]["default"] == expected_negative


class TestJobsAPIValidation:
    """Tests for /api/jobs validation."""

    def test_create_job_empty_prompt_fails(self, test_client):
        """Test that empty prompt returns 422."""
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
        assert params["cfg"]["default"] == 8.0
        assert params["width"]["default"] == 512
        assert params["prompt"]["default"] == "masterpiece, best quality, high detail"
        assert params["negative_prompt"]["default"] == (
            "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
            "missing fingers, deformed, disfigured, blurry, watermark, text, jpeg artifacts"
        )


class TestHealthAndConfig:
    """Tests for health and config endpoints."""

    def test_health_endpoint_structure(self, test_client):
        """Test GET /api/health returns expected structure."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        # Health endpoint should have these fields
        assert "ok" in data
        assert "comfy_url" in data
        assert "error_code" in data
        assert "error_message" in data

    def test_health_endpoint_when_comfy_unreachable(self, test_client):
        """Test GET /api/health returns error when ComfyUI is unreachable."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        # When ComfyUI is not running, should report unreachable
        if not data["ok"]:
            assert data["error_code"] in ["COMFY_UNREACHABLE", "COMFY_ERROR"]
            assert data["error_message"] is not None

    def test_config_endpoint(self, test_client):
        """Test GET /api/config returns expected structure."""
        response = test_client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "comfy_url" in data
        assert "defaults" in data
        assert "choices" in data


class TestUploads:
    """Tests for upload endpoints."""

    def test_upload_image_saves_file(self, test_client, tmp_path):
        """POST /api/uploads/image should save the file in comfy input dir."""
        from server import main

        # Point Comfy input dir to temp for test isolation
        main.settings.comfy_input_dir = str(tmp_path)

        file_bytes = b"test-image-bytes"
        files = {"file": ("input.png", file_bytes, "image/png")}
        response = test_client.post("/api/uploads/image", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data

        saved_path = tmp_path / data["filename"]
        assert saved_path.exists()
        assert saved_path.read_bytes() == file_bytes


class TestGetJobById:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    def test_get_nonexistent_job_returns_404(self, test_client):
        """Test GET /api/jobs/{id} returns 404 for unknown job."""
        response = test_client.get("/api/jobs/nonexistent-job-id-12345")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_job_returns_expected_fields(self, test_client_with_fake_comfy, fake_comfy_client):
        """Test GET /api/jobs/{id} returns job with expected fields."""
        # First create a job
        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "test prompt for job retrieval"}
        )
        assert response.status_code == 200
        created_job = response.json()
        job_id = created_job["id"]

        # Now retrieve it
        response = test_client_with_fake_comfy.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()

        # Check expected fields
        assert job["id"] == job_id
        assert "status" in job
        assert "prompt" in job
        assert "params" in job
        assert "created_at" in job

    def test_get_job_includes_outputs(self, test_client_with_fake_comfy):
        """Completed jobs should include output asset references."""
        from server import main

        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "job with assets"},
        )
        assert response.status_code == 200
        job_id = response.json()["id"]

        asset_id = str(uuid.uuid4())
        main.db.create_asset(
            asset_id=asset_id,
            job_id=job_id,
            engine="comfy",
            filename="test_output.png",
            recipe={"engine": "comfy"},
            meta={},
        )

        response = test_client_with_fake_comfy.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["filename"] == "test_output.png"


class TestCreateJobWithMock:
    """Tests for POST /api/jobs with FakeComfyClient (no real ComfyUI needed)."""

    def test_create_job_success_returns_job_id(self, test_client_with_fake_comfy, fake_comfy_client):
        """Test POST /api/jobs returns job_id on success."""
        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "a beautiful sunset over mountains"}
        )
        assert response.status_code == 200
        data = response.json()

        # Job should have an ID
        assert "id" in data
        assert data["id"] is not None
        assert len(data["id"]) > 0

        # Job should be queued or have prompt_id from ComfyUI
        assert data["status"] in ["queued", "running", "completed", "failed"]

    def test_create_job_with_workflow_id(self, test_client_with_fake_comfy, fake_comfy_client):
        """Test POST /api/jobs with explicit workflow_id."""
        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={
                "prompt": "a cat sitting on a couch",
                "workflow_id": "flux2_klein_distilled"
            }
        )
        # May be 200 (success) or 404 (workflow not found in test env)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["params"].get("workflow_id") == "flux2_klein_distilled"

    def test_create_job_tracks_in_fake_client(self, test_client_with_fake_comfy, fake_comfy_client):
        """Test that FakeComfyClient tracks submitted prompts."""
        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "test tracking prompt"}
        )
        assert response.status_code == 200

        # FakeComfyClient should have recorded the submission
        assert len(fake_comfy_client.submitted_prompts) >= 1

    def test_create_job_when_comfy_unreachable(self, test_client_with_fake_comfy, fake_comfy_client):
        """Test POST /api/jobs when ComfyUI is unreachable."""
        fake_comfy_client.set_unreachable()

        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "this should fail"}
        )
        assert response.status_code == 200  # Job is created but marked as failed

        data = response.json()
        assert data["status"] in ["queued", "failed"]

        # Background task should mark it as failed shortly after
        if data["status"] != "failed":
            import time
            job_id = data["id"]
            for _ in range(10):
                time.sleep(0.1)
                r = test_client_with_fake_comfy.get(f"/api/jobs/{job_id}")
                if r.status_code != 200:
                    continue
                updated = r.json()
                if updated["status"] == "failed":
                    data = updated
                    break

        assert data["status"] == "failed"
        assert data["error"] is not None


class TestJobParamsNormalization:
    """Tests for new params dict handling and legacy compatibility."""

    def test_create_job_with_params_dict_preserves_extra(self, test_client_with_fake_comfy):
        """Should accept params dict and preserve extra fields in job params."""
        payload = {
            "workflow_id": "flux2_klein_distilled",
            "params": {
                "prompt": "a cat",
                "width": 512,
                "extra_param": 123,
            },
        }
        response = test_client_with_fake_comfy.post("/api/jobs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["params"]["workflow_id"] == "flux2_klein_distilled"
        assert data["params"]["width"] == 512
        assert data["params"]["extra_param"] == 123

    def test_create_job_with_legacy_fields_populates_params(self, test_client_with_fake_comfy):
        """Legacy top-level fields should be normalized into params."""
        response = test_client_with_fake_comfy.post(
            "/api/jobs",
            json={"prompt": "legacy prompt", "width": 640, "height": 480},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["params"]["workflow_id"] == "flux2_klein_distilled"
        assert data["params"]["width"] == 640
        assert data["params"]["height"] == 480


class TestJobsListAndAssets:
    """Tests for listing jobs and assets."""

    def test_list_jobs_returns_list(self, test_client):
        """Test GET /api/jobs returns a list."""
        response = test_client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_assets_returns_list(self, test_client):
        """Test GET /api/assets returns a list."""
        response = test_client.get("/api/assets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
