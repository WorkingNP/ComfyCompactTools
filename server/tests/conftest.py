"""Pytest fixtures for server tests."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict


@pytest.fixture
def sample_template() -> Dict[str, Any]:
    """A minimal valid template for testing."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "default.safetensors"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "default prompt", "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "negative", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "test", "images": ["6", 0]},
        },
    }


@pytest.fixture
def sample_manifest() -> Dict[str, Any]:
    """A minimal valid manifest for testing."""
    return {
        "id": "test_workflow",
        "name": "Test Workflow",
        "template_file": "template_api.json",
        "params": {
            "prompt": {
                "type": "string",
                "required": True,
                "patch": {"node_id": "2", "field": "inputs.text"},
            },
            "negative_prompt": {
                "type": "string",
                "required": False,
                "default": "",
                "patch": {"node_id": "3", "field": "inputs.text"},
            },
            "seed": {
                "type": "integer",
                "required": False,
                "default": -1,
                "min": -1,
                "max": 2147483647,
                "patch": {"node_id": "5", "field": "inputs.seed"},
            },
            "steps": {
                "type": "integer",
                "required": False,
                "default": 20,
                "min": 1,
                "max": 150,
                "patch": {"node_id": "5", "field": "inputs.steps"},
            },
            "cfg": {
                "type": "number",
                "required": False,
                "default": 7.0,
                "min": 1.0,
                "max": 30.0,
                "patch": {"node_id": "5", "field": "inputs.cfg"},
            },
            "width": {
                "type": "integer",
                "required": False,
                "default": 512,
                "min": 64,
                "max": 2048,
                "patch": {"node_id": "4", "field": "inputs.width"},
            },
            "height": {
                "type": "integer",
                "required": False,
                "default": 512,
                "min": 64,
                "max": 2048,
                "patch": {"node_id": "4", "field": "inputs.height"},
            },
            "sampler_name": {
                "type": "string",
                "required": False,
                "default": "euler",
                "choices": ["euler", "euler_ancestral", "heun", "dpm_2"],
                "patch": {"node_id": "5", "field": "inputs.sampler_name"},
            },
        },
    }


@pytest.fixture
def workflows_dir(tmp_path: Path) -> Path:
    """Create a temporary workflows directory for testing."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    return wf_dir


@pytest.fixture
def setup_test_workflow(
    workflows_dir: Path, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
) -> Path:
    """Set up a complete test workflow in the workflows directory."""
    wf_path = workflows_dir / "test_workflow"
    wf_path.mkdir()

    # Write template
    template_path = wf_path / "template_api.json"
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(sample_template, f, indent=2)

    # Write manifest
    manifest_path = wf_path / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sample_manifest, f, indent=2)

    return wf_path


@pytest.fixture
def comfy_available() -> bool:
    """Check if ComfyUI is available for E2E tests."""
    try:
        import httpx

        r = httpx.get("http://127.0.0.1:8188/system_stats", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


# Marker for E2E tests
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as end-to-end (requires ComfyUI)")


# ---------------------------------------------------------------------------
# Real workflow fixtures (for manifest-driven testing)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def klein_manifest() -> Dict[str, Any]:
    """Load the actual flux2_klein_distilled manifest."""
    manifest_path = _repo_root() / "workflows" / "flux2_klein_distilled" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def klein_template() -> Dict[str, Any]:
    """Load the actual flux2_klein_distilled template."""
    template_path = _repo_root() / "workflows" / "flux2_klein_distilled" / "template_api.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sd15_manifest() -> Dict[str, Any]:
    """Load the actual sd15_txt2img manifest."""
    manifest_path = _repo_root() / "workflows" / "sd15_txt2img" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sd15_template() -> Dict[str, Any]:
    """Load the actual sd15_txt2img template."""
    template_path = _repo_root() / "workflows" / "sd15_txt2img" / "template_api.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def wan22_manifest() -> Dict[str, Any]:
    """Load the actual wan2_2_ti2v_5b manifest."""
    manifest_path = _repo_root() / "workflows" / "wan2_2_ti2v_5b" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def wan22_template() -> Dict[str, Any]:
    """Load the actual wan2_2_ti2v_5b template."""
    template_path = _repo_root() / "workflows" / "wan2_2_ti2v_5b" / "template_api.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)
