"""Workflow Registry: Discover, load, and manage workflow definitions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ManifestError(Exception):
    """Raised when a manifest is invalid or cannot be loaded."""

    pass


class WorkflowNotFoundError(Exception):
    """Raised when a requested workflow is not found."""

    pass


# Valid parameter types
VALID_PARAM_TYPES = {"string", "integer", "number", "boolean", "image"}


def load_manifest(path: Path) -> Dict[str, Any]:
    """Load a manifest from a JSON file.

    Args:
        path: Path to the manifest.json file

    Returns:
        Parsed manifest dictionary

    Raises:
        ManifestError: If file not found or invalid JSON
    """
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in manifest {path}: {e}")


def validate_manifest(manifest: Dict[str, Any]) -> None:
    """Validate a manifest structure.

    Args:
        manifest: The manifest dictionary to validate

    Raises:
        ManifestError: If validation fails
    """
    # Required top-level fields
    required_fields = ["id", "name", "template_file", "params"]
    for field in required_fields:
        if field not in manifest:
            raise ManifestError(f"Manifest missing required field: {field}")

    # Validate params
    params = manifest.get("params", {})
    if not isinstance(params, dict):
        raise ManifestError("Manifest 'params' must be an object")

    for param_name, param_def in params.items():
        _validate_param_definition(param_name, param_def)


def _validate_param_definition(name: str, param_def: Dict[str, Any]) -> None:
    """Validate a single parameter definition.

    Args:
        name: Parameter name (for error messages)
        param_def: Parameter definition dict

    Raises:
        ManifestError: If validation fails
    """
    # Type is required
    if "type" not in param_def:
        raise ManifestError(f"Parameter '{name}' missing required field: type")

    param_type = param_def["type"]
    if param_type not in VALID_PARAM_TYPES:
        raise ManifestError(
            f"Parameter '{name}' has invalid type '{param_type}'. "
            f"Valid types: {', '.join(sorted(VALID_PARAM_TYPES))}"
        )

    # Patch is required
    if "patch" not in param_def:
        raise ManifestError(f"Parameter '{name}' missing required field: patch")

    patch = param_def["patch"]
    if not isinstance(patch, dict):
        raise ManifestError(f"Parameter '{name}' patch must be an object")

    if "node_id" not in patch:
        raise ManifestError(f"Parameter '{name}' patch missing required field: node_id")

    if "field" not in patch:
        raise ManifestError(f"Parameter '{name}' patch missing required field: field")


def load_template(path: Path) -> Dict[str, Any]:
    """Load a template from a JSON file.

    Args:
        path: Path to the template_api.json file

    Returns:
        Parsed template dictionary

    Raises:
        ManifestError: If file not found or invalid JSON
    """
    if not path.exists():
        raise ManifestError(f"Template not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in template {path}: {e}")


class WorkflowRegistry:
    """Registry for managing workflow definitions.

    Discovers workflows in a directory, loads and caches them.
    """

    def __init__(self, workflows_dir: Path):
        """Initialize the registry.

        Args:
            workflows_dir: Directory containing workflow subdirectories
        """
        self._workflows_dir = Path(workflows_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._workflow_list: Optional[List[Dict[str, Any]]] = None

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows.

        Returns:
            List of workflow info dicts with id, name, description
        """
        if self._workflow_list is not None:
            return self._workflow_list

        workflows = []

        if not self._workflows_dir.exists():
            self._workflow_list = []
            return []

        for entry in self._workflows_dir.iterdir():
            if not entry.is_dir():
                continue

            manifest_path = entry / "manifest.json"
            template_path = entry / "template_api.json"

            # Skip incomplete workflows
            if not manifest_path.exists() or not template_path.exists():
                continue

            try:
                manifest = load_manifest(manifest_path)
                validate_manifest(manifest)

                # Also validate template is loadable
                load_template(template_path)

                workflows.append(
                    {
                        "id": manifest.get("id", entry.name),
                        "name": manifest.get("name", entry.name),
                        "description": manifest.get("description", ""),
                        "version": manifest.get("version", ""),
                    }
                )
            except (ManifestError, json.JSONDecodeError):
                # Skip invalid workflows
                continue

        self._workflow_list = workflows
        return workflows

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by ID.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Dict with 'manifest' and 'template' keys

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        # Check cache first
        if workflow_id in self._cache:
            return self._cache[workflow_id]

        # Find workflow directory
        wf_dir = self._workflows_dir / workflow_id
        if not wf_dir.is_dir():
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")

        manifest_path = wf_dir / "manifest.json"
        if not manifest_path.exists():
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' missing manifest.json")

        # Load and validate manifest
        manifest = load_manifest(manifest_path)
        validate_manifest(manifest)

        # Load template
        template_file = manifest.get("template_file", "template_api.json")
        template_path = wf_dir / template_file
        template = load_template(template_path)

        workflow = {
            "manifest": manifest,
            "template": template,
        }

        # Cache it
        self._cache[workflow_id] = workflow
        return workflow

    def reload(self) -> None:
        """Clear the cache and force re-discovery of workflows."""
        self._cache.clear()
        self._workflow_list = None
