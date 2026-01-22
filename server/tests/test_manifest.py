"""Tests for manifest loading and validation."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict

# Import will be available after implementation
# from server.workflow_registry import load_manifest, validate_manifest, ManifestError


class TestManifestLoading:
    """Tests for loading manifest files."""

    def test_load_valid_manifest(self, tmp_path: Path, sample_manifest: Dict[str, Any]):
        """Test loading a valid manifest from file."""
        from server.workflow_registry import load_manifest

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(sample_manifest, f)

        loaded = load_manifest(manifest_path)
        assert loaded["id"] == "test_workflow"
        assert loaded["name"] == "Test Workflow"
        assert "params" in loaded

    def test_load_nonexistent_manifest(self, tmp_path: Path):
        """Test loading a manifest that doesn't exist."""
        from server.workflow_registry import load_manifest, ManifestError

        with pytest.raises(ManifestError, match="not found"):
            load_manifest(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path: Path):
        """Test loading a manifest with invalid JSON."""
        from server.workflow_registry import load_manifest, ManifestError

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        with pytest.raises(ManifestError, match="Invalid JSON"):
            load_manifest(manifest_path)


class TestManifestValidation:
    """Tests for manifest validation."""

    def test_validate_valid_manifest(self, sample_manifest: Dict[str, Any]):
        """Test validating a complete valid manifest."""
        from server.workflow_registry import validate_manifest

        # Should not raise
        validate_manifest(sample_manifest)

    def test_reject_missing_id(self, sample_manifest: Dict[str, Any]):
        """Test that manifest without id is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        del sample_manifest["id"]
        with pytest.raises(ManifestError, match="id"):
            validate_manifest(sample_manifest)

    def test_reject_missing_name(self, sample_manifest: Dict[str, Any]):
        """Test that manifest without name is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        del sample_manifest["name"]
        with pytest.raises(ManifestError, match="name"):
            validate_manifest(sample_manifest)

    def test_reject_missing_params(self, sample_manifest: Dict[str, Any]):
        """Test that manifest without params is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        del sample_manifest["params"]
        with pytest.raises(ManifestError, match="params"):
            validate_manifest(sample_manifest)

    def test_reject_missing_template_file(self, sample_manifest: Dict[str, Any]):
        """Test that manifest without template_file is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        del sample_manifest["template_file"]
        with pytest.raises(ManifestError, match="template_file"):
            validate_manifest(sample_manifest)

    def test_reject_invalid_param_type(self, sample_manifest: Dict[str, Any]):
        """Test that invalid param type is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        sample_manifest["params"]["bad_param"] = {
            "type": "invalid_type",
            "patch": {"node_id": "1", "field": "inputs.x"},
        }
        with pytest.raises(ManifestError, match="type"):
            validate_manifest(sample_manifest)

    def test_reject_missing_patch(self, sample_manifest: Dict[str, Any]):
        """Test that param without patch is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        sample_manifest["params"]["no_patch"] = {
            "type": "string",
            "required": True,
        }
        with pytest.raises(ManifestError, match="patch"):
            validate_manifest(sample_manifest)

    def test_reject_invalid_patch_missing_node_id(self, sample_manifest: Dict[str, Any]):
        """Test that patch without node_id is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        sample_manifest["params"]["bad_patch"] = {
            "type": "string",
            "patch": {"field": "inputs.x"},  # missing node_id
        }
        with pytest.raises(ManifestError, match="node_id"):
            validate_manifest(sample_manifest)

    def test_reject_invalid_patch_missing_field(self, sample_manifest: Dict[str, Any]):
        """Test that patch without field is rejected."""
        from server.workflow_registry import validate_manifest, ManifestError

        sample_manifest["params"]["bad_patch"] = {
            "type": "string",
            "patch": {"node_id": "1"},  # missing field
        }
        with pytest.raises(ManifestError, match="field"):
            validate_manifest(sample_manifest)

    def test_accept_all_valid_types(self, sample_manifest: Dict[str, Any]):
        """Test that all valid param types are accepted."""
        from server.workflow_registry import validate_manifest

        for ptype in ["string", "integer", "number", "boolean", "image"]:
            sample_manifest["params"][f"test_{ptype}"] = {
                "type": ptype,
                "patch": {"node_id": "1", "field": f"inputs.{ptype}"},
            }

        # Should not raise
        validate_manifest(sample_manifest)
