"""Tests for workflow registry."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict

# Import will be available after implementation
# from server.workflow_registry import WorkflowRegistry, WorkflowNotFoundError


class TestWorkflowDiscovery:
    """Tests for discovering workflows in directory."""

    def test_list_empty_directory(self, workflows_dir: Path):
        """Test listing workflows from empty directory."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        assert workflows == []

    def test_list_single_workflow(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test listing a single workflow."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        assert len(workflows) == 1
        assert workflows[0]["id"] == "test_workflow"
        assert workflows[0]["name"] == "Test Workflow"

    def test_list_multiple_workflows(
        self,
        workflows_dir: Path,
        sample_template: Dict[str, Any],
        sample_manifest: Dict[str, Any],
    ):
        """Test listing multiple workflows."""
        from server.workflow_registry import WorkflowRegistry

        # Create two workflows
        for wf_id in ["workflow_a", "workflow_b"]:
            wf_path = workflows_dir / wf_id
            wf_path.mkdir()

            manifest = {**sample_manifest, "id": wf_id, "name": f"Workflow {wf_id[-1].upper()}"}
            with open(wf_path / "template_api.json", "w", encoding="utf-8") as f:
                json.dump(sample_template, f)
            with open(wf_path / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f)

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        assert len(workflows) == 2
        ids = [w["id"] for w in workflows]
        assert "workflow_a" in ids
        assert "workflow_b" in ids

    def test_ignore_non_directories(
        self,
        workflows_dir: Path,
        setup_test_workflow: Path,
    ):
        """Test that non-directory files are ignored."""
        from server.workflow_registry import WorkflowRegistry

        # Create a random file in workflows dir
        (workflows_dir / "random_file.txt").write_text("ignore me")

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        # Should only find the actual workflow
        assert len(workflows) == 1

    def test_ignore_incomplete_workflows(
        self,
        workflows_dir: Path,
        sample_template: Dict[str, Any],
    ):
        """Test that incomplete workflows (missing manifest or template) are ignored."""
        from server.workflow_registry import WorkflowRegistry

        # Create workflow with only template (no manifest)
        no_manifest = workflows_dir / "no_manifest"
        no_manifest.mkdir()
        with open(no_manifest / "template_api.json", "w", encoding="utf-8") as f:
            json.dump(sample_template, f)

        # Create workflow with only manifest (no template)
        no_template = workflows_dir / "no_template"
        no_template.mkdir()
        with open(no_template / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({"id": "no_template", "name": "No Template"}, f)

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        # Should find neither incomplete workflow
        assert len(workflows) == 0


class TestWorkflowRetrieval:
    """Tests for retrieving individual workflows."""

    def test_get_existing_workflow(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test getting an existing workflow."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)
        workflow = registry.get_workflow("test_workflow")

        assert workflow is not None
        assert "manifest" in workflow
        assert "template" in workflow
        assert workflow["manifest"]["id"] == "test_workflow"

    def test_get_nonexistent_workflow(self, workflows_dir: Path):
        """Test getting a workflow that doesn't exist."""
        from server.workflow_registry import WorkflowRegistry, WorkflowNotFoundError

        registry = WorkflowRegistry(workflows_dir)

        with pytest.raises(WorkflowNotFoundError, match="nonexistent"):
            registry.get_workflow("nonexistent")

    def test_workflow_contains_template(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test that retrieved workflow contains template data."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)
        workflow = registry.get_workflow("test_workflow")

        assert "template" in workflow
        assert "1" in workflow["template"]  # Node ID from sample template
        assert workflow["template"]["1"]["class_type"] == "CheckpointLoaderSimple"

    def test_workflow_contains_manifest(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test that retrieved workflow contains manifest data."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)
        workflow = registry.get_workflow("test_workflow")

        assert "manifest" in workflow
        assert "params" in workflow["manifest"]
        assert "prompt" in workflow["manifest"]["params"]


class TestWorkflowCaching:
    """Tests for workflow caching behavior."""

    def test_workflow_is_cached(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test that workflows are cached after first load."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)

        workflow1 = registry.get_workflow("test_workflow")
        workflow2 = registry.get_workflow("test_workflow")

        # Should be the same object (cached)
        assert workflow1 is workflow2

    def test_reload_clears_cache(self, setup_test_workflow: Path, workflows_dir: Path):
        """Test that reload clears the cache."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)

        workflow1 = registry.get_workflow("test_workflow")
        registry.reload()
        workflow2 = registry.get_workflow("test_workflow")

        # Should be different objects after reload
        assert workflow1 is not workflow2

    def test_list_after_reload_reflects_changes(
        self,
        workflows_dir: Path,
        sample_template: Dict[str, Any],
        sample_manifest: Dict[str, Any],
    ):
        """Test that list reflects filesystem changes after reload."""
        from server.workflow_registry import WorkflowRegistry

        registry = WorkflowRegistry(workflows_dir)

        # Initially empty
        assert len(registry.list_workflows()) == 0

        # Add a workflow
        wf_path = workflows_dir / "new_workflow"
        wf_path.mkdir()
        manifest = {**sample_manifest, "id": "new_workflow"}
        with open(wf_path / "template_api.json", "w", encoding="utf-8") as f:
            json.dump(sample_template, f)
        with open(wf_path / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Still empty (cached)
        assert len(registry.list_workflows()) == 0

        # After reload, should find new workflow
        registry.reload()
        assert len(registry.list_workflows()) == 1


class TestValidation:
    """Tests for workflow validation during loading."""

    def test_invalid_manifest_is_skipped(
        self,
        workflows_dir: Path,
        sample_template: Dict[str, Any],
    ):
        """Test that workflows with invalid manifests are skipped."""
        from server.workflow_registry import WorkflowRegistry

        wf_path = workflows_dir / "invalid_workflow"
        wf_path.mkdir()

        # Valid template
        with open(wf_path / "template_api.json", "w", encoding="utf-8") as f:
            json.dump(sample_template, f)

        # Invalid manifest (missing required fields)
        with open(wf_path / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({"invalid": "manifest"}, f)

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        # Should not include invalid workflow
        assert len(workflows) == 0

    def test_invalid_json_is_skipped(
        self,
        workflows_dir: Path,
        sample_manifest: Dict[str, Any],
    ):
        """Test that workflows with invalid JSON are skipped."""
        from server.workflow_registry import WorkflowRegistry

        wf_path = workflows_dir / "bad_json"
        wf_path.mkdir()

        # Invalid JSON in template
        with open(wf_path / "template_api.json", "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Valid manifest
        with open(wf_path / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(sample_manifest, f)

        registry = WorkflowRegistry(workflows_dir)
        workflows = registry.list_workflows()

        # Should not include workflow with bad JSON
        assert len(workflows) == 0
