"""Workflow Patcher: Apply parameters to template via deep copy + patch."""
from __future__ import annotations

import copy
import random
from typing import Any, Dict, Optional


class PatchError(Exception):
    """Raised when patching fails."""

    pass


def apply_patch(
    template: Dict[str, Any],
    manifest: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply parameters to a template via deep copy and patching.

    This function is pure - it does not modify the original template.

    Args:
        template: The ComfyUI API template (will not be modified)
        manifest: The workflow manifest with param definitions
        params: User-provided parameter values

    Returns:
        A new dict with patches applied

    Raises:
        PatchError: If patching fails (missing required param, invalid value, etc.)
    """
    # Deep copy to ensure original is never modified
    result = copy.deepcopy(template)

    param_defs = manifest.get("params", {})

    # First, validate all params and apply defaults
    validated_params = _validate_and_prepare_params(param_defs, params)

    # Then apply each patch
    for param_name, value in validated_params.items():
        param_def = param_defs.get(param_name)
        if param_def is None:
            continue  # Skip unknown params

        patch = param_def.get("patch")
        if patch is None:
            continue

        node_id = patch.get("node_id")
        field_path = patch.get("field")

        _apply_single_patch(result, node_id, field_path, value, param_name)

    return result


def _validate_and_prepare_params(
    param_defs: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate params and fill in defaults.

    Args:
        param_defs: Parameter definitions from manifest
        params: User-provided params

    Returns:
        Dict of validated/coerced params with defaults filled in

    Raises:
        PatchError: If validation fails
    """
    result = {}

    for param_name, param_def in param_defs.items():
        value = params.get(param_name)
        is_required = param_def.get("required", False)
        default = param_def.get("default")
        param_type = param_def.get("type", "string")

        # Handle missing values
        if value is None:
            if is_required:
                raise PatchError(f"Missing required parameter: {param_name}")
            if default is not None:
                value = default
            else:
                continue  # Skip params with no value and no default

        # Special case: seed of -1 means random
        if param_name == "seed" and value == -1:
            value = random.randint(0, 2**31 - 1)

        # Type coercion
        value = _coerce_type(param_name, value, param_type)

        # Range validation
        _validate_range(param_name, value, param_def)

        # Choice validation
        _validate_choices(param_name, value, param_def)

        result[param_name] = value

    return result


def _coerce_type(param_name: str, value: Any, param_type: str) -> Any:
    """Coerce a value to the expected type.

    Args:
        param_name: For error messages
        value: The value to coerce
        param_type: Expected type (string, integer, number, boolean, image)

    Returns:
        Coerced value

    Raises:
        PatchError: If coercion fails
    """
    try:
        if param_type == "integer":
            return int(value)
        elif param_type == "number":
            return float(value)
        elif param_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif param_type == "string":
            return str(value)
        elif param_type == "image":
            # Image type is just a filename string
            return str(value)
        else:
            return value
    except (ValueError, TypeError) as e:
        raise PatchError(f"Parameter '{param_name}' type coercion failed: {e}")


def _validate_range(param_name: str, value: Any, param_def: Dict[str, Any]) -> None:
    """Validate that value is within min/max range.

    Args:
        param_name: For error messages
        value: The value to validate
        param_def: Parameter definition

    Raises:
        PatchError: If value is out of range
    """
    min_val = param_def.get("min")
    max_val = param_def.get("max")

    if min_val is not None and value < min_val:
        raise PatchError(
            f"Parameter '{param_name}' value {value} is below minimum {min_val}"
        )

    if max_val is not None and value > max_val:
        raise PatchError(
            f"Parameter '{param_name}' value {value} is above maximum {max_val}"
        )


def _validate_choices(param_name: str, value: Any, param_def: Dict[str, Any]) -> None:
    """Validate that value is one of the allowed choices.

    Args:
        param_name: For error messages
        value: The value to validate
        param_def: Parameter definition

    Raises:
        PatchError: If value is not in choices
    """
    choices = param_def.get("choices")
    if choices is not None and value not in choices:
        raise PatchError(
            f"Parameter '{param_name}' value '{value}' not in allowed choices: {choices}"
        )


def _apply_single_patch(
    template: Dict[str, Any],
    node_id: str,
    field_path: str,
    value: Any,
    param_name: str,
) -> None:
    """Apply a single patch to the template (in-place).

    Args:
        template: Template to modify
        node_id: Node ID to patch
        field_path: Dot-notation path (e.g., "inputs.text")
        value: Value to set
        param_name: For error messages

    Raises:
        PatchError: If node_id or field_path not found
    """
    # Find the node
    if node_id not in template:
        raise PatchError(
            f"Cannot patch parameter '{param_name}': node_id '{node_id}' not found in template"
        )

    node = template[node_id]

    # Navigate the field path
    parts = field_path.split(".")
    target = node

    for i, part in enumerate(parts[:-1]):
        if not isinstance(target, dict):
            path_so_far = ".".join(parts[: i + 1])
            raise PatchError(
                f"Cannot patch parameter '{param_name}': path '{path_so_far}' "
                f"is not an object in node '{node_id}'"
            )

        if part not in target:
            raise PatchError(
                f"Cannot patch parameter '{param_name}': field '{part}' "
                f"not found in node '{node_id}'"
            )

        target = target[part]

    # Set the final field
    final_field = parts[-1]
    if not isinstance(target, dict):
        raise PatchError(
            f"Cannot patch parameter '{param_name}': parent of '{final_field}' "
            f"is not an object in node '{node_id}'"
        )

    # We allow setting fields that don't exist (for flexibility)
    # But warn if the field doesn't exist in the original
    target[final_field] = value
