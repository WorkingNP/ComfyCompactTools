"""Tests for UI serving (static files)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for the FastAPI app."""
    from server.main import app
    return TestClient(app)


class TestUIServing:
    """Test static UI file serving."""

    def test_root_serves_html(self, client):
        """GET / should return index.html."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # Check for essential HTML elements
        html = response.text
        assert "<!doctype html>" in html.lower() or "<!DOCTYPE html>" in html
        assert "<html" in html

    def test_app_js_accessible(self, client):
        """Static JS file should be accessible."""
        response = client.get("/app.js")
        assert response.status_code == 200
        # Should contain JavaScript
        assert "function" in response.text or "const" in response.text

    def test_styles_css_accessible(self, client):
        """Static CSS file should be accessible."""
        response = client.get("/styles.css")
        assert response.status_code == 200
        # Basic CSS check
        css = response.text
        # CSS files should have some common patterns
        assert "{" in css and "}" in css


class TestAPIForUI:
    """Test that APIs needed by UI are working correctly."""

    def test_health_provides_ui_info(self, client):
        """Health endpoint should provide info for UI."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "comfy_url" in data
        assert "error_code" in data  # Can be None if OK
        assert "error_message" in data  # Can be None if OK

    def test_workflows_list_for_ui(self, client):
        """Workflows endpoint should return data for UI."""
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least one workflow
        assert len(data) > 0
        # Each workflow should have essential fields
        for wf in data:
            assert "id" in wf
            assert "name" in wf

    def test_workflow_detail_for_form_generation(self, client):
        """Workflow detail should provide params_schema for form generation."""
        # First get available workflows
        response = client.get("/api/workflows")
        assert response.status_code == 200
        workflows = response.json()
        assert len(workflows) > 0

        # Get detail for first workflow
        workflow_id = workflows[0]["id"]
        response = client.get(f"/api/workflows/{workflow_id}")
        assert response.status_code == 200

        detail = response.json()
        assert "id" in detail
        assert "name" in detail
        assert "params" in detail

        # params should be a dict where each param has metadata for form generation
        params = detail["params"]
        assert isinstance(params, dict)

        # Check that params have type information for form generation
        for param_name, param_def in params.items():
            assert isinstance(param_def, dict), f"param {param_name} should be a dict"
            # Should have type information
            assert "type" in param_def, f"param {param_name} missing 'type'"
            # Optional params should have default, required params don't need it
            is_required = param_def.get("required", False)
            if not is_required:
                assert "default" in param_def, f"optional param {param_name} missing 'default'"
