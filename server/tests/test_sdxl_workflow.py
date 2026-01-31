"""Tests for SDXL workflow."""
from __future__ import annotations

import pytest
from pathlib import Path
import json


@pytest.fixture
def sdxl_manifest():
    """Load SDXL manifest from file."""
    manifest_path = Path(__file__).parent.parent.parent / "workflows" / "sdxl_txt2img" / "manifest.json"
    with open(manifest_path) as f:
        return json.load(f)


@pytest.fixture
def sdxl_template():
    """Load SDXL template from file."""
    template_path = Path(__file__).parent.parent.parent / "workflows" / "sdxl_txt2img" / "template_api.json"
    with open(template_path) as f:
        return json.load(f)


class TestSDXLManifest:
    """Validate SDXL manifest structure."""

    def test_required_fields(self, sdxl_manifest):
        """Test manifest has all required fields."""
        assert sdxl_manifest["id"] == "sdxl_txt2img"
        assert sdxl_manifest["name"]
        assert "params" in sdxl_manifest
        assert "template_file" in sdxl_manifest

    def test_has_checkpoint_param(self, sdxl_manifest):
        """Test checkpoint param is defined."""
        assert "checkpoint" in sdxl_manifest["params"]
        ckpt = sdxl_manifest["params"]["checkpoint"]
        assert ckpt["type"] == "string"
        assert "patch" in ckpt

    def test_has_vae_param(self, sdxl_manifest):
        """Test VAE param is defined."""
        assert "vae" in sdxl_manifest["params"]
        vae = sdxl_manifest["params"]["vae"]
        assert vae["type"] == "string"
        assert "patch" in vae


class TestSDXLPatching:
    """Test SDXL workflow patching."""

    def test_all_params_patch_correctly(self, sdxl_template, sdxl_manifest):
        """Test that all manifest params patch correctly."""
        from server.workflow_patcher import apply_patch

        test_values = {
            "prompt": "a majestic cat",
            "negative_prompt": "blurry",
            "checkpoint": "sd_xl_base_1.0.safetensors",
            "vae": "sdxl_vae.safetensors",
            "width": 1024,
            "height": 1024,
            "steps": 30,
            "cfg": 7.5,
            "seed": 42,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "batch_size": 2
        }

        result = apply_patch(sdxl_template, sdxl_manifest, test_values)

        # Verify key patches
        assert result["2"]["inputs"]["text"] == "a majestic cat"
        assert result["3"]["inputs"]["text"] == "blurry"
        assert result["1"]["inputs"]["ckpt_name"] == "sd_xl_base_1.0.safetensors"
        assert result["8"]["inputs"]["vae_name"] == "sdxl_vae.safetensors"
        assert result["4"]["inputs"]["width"] == 1024
        assert result["4"]["inputs"]["height"] == 1024
        assert result["4"]["inputs"]["batch_size"] == 2
        assert result["5"]["inputs"]["steps"] == 30
        assert result["5"]["inputs"]["cfg"] == 7.5
        assert result["5"]["inputs"]["seed"] == 42
        assert result["5"]["inputs"]["sampler_name"] == "dpmpp_2m"
        assert result["5"]["inputs"]["scheduler"] == "karras"

    def test_sdxl_defaults(self, sdxl_template, sdxl_manifest):
        """Test SDXL-appropriate default values (1024x1024)."""
        from server.workflow_patcher import apply_patch

        result = apply_patch(sdxl_template, sdxl_manifest, {"prompt": "test"})

        # SDXL defaults should be 1024
        assert result["4"]["inputs"]["width"] == 1024
        assert result["4"]["inputs"]["height"] == 1024
        assert result["5"]["inputs"]["steps"] == 25  # Official template default


class TestSDXLRegistry:
    """Test SDXL workflow registration."""

    def test_sdxl_appears_in_workflow_list(self):
        """Test SDXL workflow is discoverable."""
        from server.workflow_registry import WorkflowRegistry
        from pathlib import Path

        workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        ids = [w["id"] for w in workflows]
        assert "sdxl_txt2img" in ids

    def test_sdxl_can_be_loaded(self):
        """Test SDXL workflow can be loaded."""
        from server.workflow_registry import WorkflowRegistry
        from pathlib import Path

        workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        registry = WorkflowRegistry(workflows_dir)

        wf = registry.get_workflow("sdxl_txt2img")
        assert wf["manifest"]["id"] == "sdxl_txt2img"
        assert "template" in wf
