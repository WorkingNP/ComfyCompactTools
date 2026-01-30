"""Tests for template patching."""
from __future__ import annotations

import copy
import pytest
from typing import Any, Dict

# Import will be available after implementation
# from server.workflow_patcher import apply_patch, PatchError


class TestDeepCopy:
    """Tests for ensuring templates are not mutated."""

    def test_original_not_modified(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that applying patch does not modify the original template."""
        from server.workflow_patcher import apply_patch

        original = copy.deepcopy(sample_template)
        params = {"prompt": "new prompt", "steps": 30}

        result = apply_patch(sample_template, sample_manifest, params)

        # Original should be unchanged
        assert sample_template == original
        # Result should be different
        assert result["2"]["inputs"]["text"] == "new prompt"
        assert result["5"]["inputs"]["steps"] == 30

    def test_nested_objects_not_shared(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that nested objects are fully copied, not shared."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test"}
        result = apply_patch(sample_template, sample_manifest, params)

        # Modify the result
        result["2"]["inputs"]["text"] = "modified"

        # Original should be unchanged
        assert sample_template["2"]["inputs"]["text"] == "default prompt"


class TestSimplePatching:
    """Tests for basic patch operations."""

    def test_patch_string_field(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test patching a string field."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "a beautiful sunset"}
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["2"]["inputs"]["text"] == "a beautiful sunset"

    def test_patch_integer_field(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test patching an integer field."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "steps": 50}
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["steps"] == 50

    def test_patch_float_field(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test patching a float/number field."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "cfg": 12.5}
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["cfg"] == 12.5

    def test_patch_multiple_fields(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test patching multiple fields at once."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "a cat",
            "negative_prompt": "ugly",
            "steps": 30,
            "cfg": 8.0,
            "width": 768,
            "height": 768,
        }
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["2"]["inputs"]["text"] == "a cat"
        assert result["3"]["inputs"]["text"] == "ugly"
        assert result["5"]["inputs"]["steps"] == 30
        assert result["5"]["inputs"]["cfg"] == 8.0
        assert result["4"]["inputs"]["width"] == 768
        assert result["4"]["inputs"]["height"] == 768


class TestDefaultValues:
    """Tests for default value handling."""

    def test_missing_param_uses_default(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that missing optional params use default values."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test"}  # steps not provided, default is 20
        result = apply_patch(sample_template, sample_manifest, params)

        # Default value should be applied
        assert result["5"]["inputs"]["steps"] == 20

    def test_explicit_value_overrides_default(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that explicit values override defaults."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "steps": 40}  # override default
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["steps"] == 40


class TestTypeCoercion:
    """Tests for type coercion."""

    def test_string_to_integer_coercion(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that string values are coerced to integers when needed."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "steps": "30"}  # string instead of int
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["steps"] == 30
        assert isinstance(result["5"]["inputs"]["steps"], int)

    def test_string_to_float_coercion(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that string values are coerced to floats when needed."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "cfg": "8.5"}  # string instead of float
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["cfg"] == 8.5
        assert isinstance(result["5"]["inputs"]["cfg"], float)

    def test_integer_to_float_coercion(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that integers are coerced to floats when needed."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "cfg": 8}  # int instead of float
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["cfg"] == 8.0


class TestValidation:
    """Tests for parameter validation."""

    def test_missing_required_param_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that missing required params raise an error."""
        from server.workflow_patcher import apply_patch, PatchError

        params = {}  # missing required 'prompt'
        with pytest.raises(PatchError, match="prompt"):
            apply_patch(sample_template, sample_manifest, params)

    def test_value_below_min_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that values below min raise an error."""
        from server.workflow_patcher import apply_patch, PatchError

        params = {"prompt": "test", "steps": 0}  # min is 1
        with pytest.raises(PatchError, match="steps"):
            apply_patch(sample_template, sample_manifest, params)

    def test_value_above_max_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that values above max raise an error."""
        from server.workflow_patcher import apply_patch, PatchError

        params = {"prompt": "test", "steps": 200}  # max is 150
        with pytest.raises(PatchError, match="steps"):
            apply_patch(sample_template, sample_manifest, params)

    def test_invalid_choice_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that invalid choice values raise an error."""
        from server.workflow_patcher import apply_patch, PatchError

        params = {"prompt": "test", "sampler_name": "invalid_sampler"}
        with pytest.raises(PatchError, match="sampler_name"):
            apply_patch(sample_template, sample_manifest, params)

    def test_valid_choice_accepted(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that valid choice values are accepted."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "sampler_name": "euler_ancestral"}
        result = apply_patch(sample_template, sample_manifest, params)

        assert result["5"]["inputs"]["sampler_name"] == "euler_ancestral"


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_node_id_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that patching non-existent node raises descriptive error."""
        from server.workflow_patcher import apply_patch, PatchError

        # Add a param with invalid node_id
        sample_manifest["params"]["bad_param"] = {
            "type": "string",
            "required": True,
            "patch": {"node_id": "999", "field": "inputs.text"},
        }

        params = {"prompt": "test", "bad_param": "value"}
        with pytest.raises(PatchError, match="999"):
            apply_patch(sample_template, sample_manifest, params)

    def test_invalid_field_path_raises_error(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that patching non-existent field raises descriptive error."""
        from server.workflow_patcher import apply_patch, PatchError

        # Add a param with invalid field path
        sample_manifest["params"]["bad_param"] = {
            "type": "string",
            "required": True,
            "patch": {"node_id": "2", "field": "inputs.nonexistent.field"},
        }

        params = {"prompt": "test", "bad_param": "value"}
        with pytest.raises(PatchError, match="nonexistent"):
            apply_patch(sample_template, sample_manifest, params)

    def test_error_message_includes_param_name(
        self, sample_template: Dict[str, Any], sample_manifest: Dict[str, Any]
    ):
        """Test that error messages include the parameter name."""
        from server.workflow_patcher import apply_patch, PatchError

        params = {}  # missing required 'prompt'
        with pytest.raises(PatchError) as exc_info:
            apply_patch(sample_template, sample_manifest, params)

        assert "prompt" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Manifest-Driven Tests (using actual workflow manifests)
# ---------------------------------------------------------------------------

def _get_nested_value(obj: Dict, node_id: str, field_path: str) -> Any:
    """Get a nested value from template using node_id and field path.

    Args:
        obj: The template dict
        node_id: The node ID (e.g., "2")
        field_path: The field path (e.g., "inputs.text")

    Returns:
        The value at the specified path
    """
    node = obj.get(node_id)
    if node is None:
        raise KeyError(f"Node {node_id} not found")

    parts = field_path.split(".")
    current = node
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise KeyError(f"Cannot traverse path {field_path}")
    return current


def _generate_test_value(param_def: Dict[str, Any]) -> Any:
    """Generate a test value based on parameter definition.

    Args:
        param_def: The parameter definition from manifest

    Returns:
        A valid test value for this parameter type
    """
    param_type = param_def.get("type", "string")

    if param_type == "string":
        if "choices" in param_def:
            return param_def["choices"][0]
        return "test_value_string"
    elif param_type == "integer":
        min_val = param_def.get("min", 1)
        max_val = param_def.get("max", 100)
        # Pick a value in the middle of the range
        return max(min_val, min(max_val, (min_val + max_val) // 2))
    elif param_type == "number":
        min_val = param_def.get("min", 0.0)
        max_val = param_def.get("max", 10.0)
        return (min_val + max_val) / 2
    elif param_type == "boolean":
        return True
    elif param_type == "image":
        return "test_input.png"
    else:
        return "unknown_type_value"


class TestKleinDistilledManifestDriven:
    """Manifest-driven tests for flux2_klein_distilled workflow.

    These tests automatically verify that all parameters defined in the
    manifest correctly patch the template. When new parameters are added
    to the manifest, they are automatically tested.
    """

    def test_all_params_patch_correctly(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that ALL params defined in manifest patch correctly.

        This test iterates over every parameter in the manifest and verifies
        that applying it results in the correct value at the expected location.
        """
        from server.workflow_patcher import apply_patch

        manifest_params = klein_manifest.get("params", {})

        for param_name, param_def in manifest_params.items():
            # Generate a test value for this parameter
            test_value = _generate_test_value(param_def)

            # Build params dict (always include required prompt)
            params = {"prompt": "test prompt"}
            if param_name != "prompt":
                params[param_name] = test_value
            else:
                params["prompt"] = test_value

            # Apply patch
            result = apply_patch(klein_template, klein_manifest, params)

            # Verify the patch was applied
            patch_def = param_def.get("patch", {})
            node_id = patch_def.get("node_id")
            field_path = patch_def.get("field")

            if node_id and field_path:
                actual = _get_nested_value(result, node_id, field_path)
                assert actual == test_value, (
                    f"Parameter '{param_name}' not patched correctly. "
                    f"Expected {test_value!r} at node {node_id} / {field_path}, "
                    f"got {actual!r}"
                )

    def test_prompt_patches_to_clip_text_encode(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that prompt patches to the correct CLIP text encode node."""
        from server.workflow_patcher import apply_patch

        test_prompt = "a beautiful sunset over mountains"
        params = {"prompt": test_prompt}
        result = apply_patch(klein_template, klein_manifest, params)

        # Verify node 2 (CLIP Text Encode) has the prompt
        assert result["2"]["inputs"]["text"] == test_prompt

    def test_dimensions_patch_to_multiple_nodes(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that width/height patch to both latent and scheduler nodes."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "test",
            "width": 768,
            "height": 512,
            "width_scheduler": 768,
            "height_scheduler": 512,
        }
        result = apply_patch(klein_template, klein_manifest, params)

        # Node 7: EmptyFlux2LatentImage
        assert result["7"]["inputs"]["width"] == 768
        assert result["7"]["inputs"]["height"] == 512

        # Node 8: Flux2Scheduler
        assert result["8"]["inputs"]["width"] == 768
        assert result["8"]["inputs"]["height"] == 512

    def test_seed_patches_to_random_noise(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that seed patches to RandomNoise node."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "seed": 12345}
        result = apply_patch(klein_template, klein_manifest, params)

        # Node 6: RandomNoise
        assert result["6"]["inputs"]["noise_seed"] == 12345

    def test_cfg_patches_to_cfg_guider(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that cfg patches to CFGGuider node."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "cfg": 2.5}
        result = apply_patch(klein_template, klein_manifest, params)

        # Node 5: CFGGuider
        assert result["5"]["inputs"]["cfg"] == 2.5

    def test_steps_patches_to_scheduler(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test that steps patches to Flux2Scheduler node."""
        from server.workflow_patcher import apply_patch

        params = {"prompt": "test", "steps": 8}
        result = apply_patch(klein_template, klein_manifest, params)

        # Node 8: Flux2Scheduler
        assert result["8"]["inputs"]["steps"] == 8

    def test_combined_params(
        self, klein_template: Dict[str, Any], klein_manifest: Dict[str, Any]
    ):
        """Test applying multiple params together."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "a cat sitting on a windowsill",
            "negative_prompt": "blurry, low quality",
            "width": 512,
            "height": 768,
            "width_scheduler": 512,
            "height_scheduler": 768,
            "steps": 6,
            "cfg": 1.5,
            "seed": 42,
            "sampler_name": "euler",
        }
        result = apply_patch(klein_template, klein_manifest, params)

        # Verify all patches were applied
        assert result["2"]["inputs"]["text"] == "a cat sitting on a windowsill"
        assert result["3"]["inputs"]["text"] == "blurry, low quality"
        assert result["7"]["inputs"]["width"] == 512
        assert result["7"]["inputs"]["height"] == 768
        assert result["8"]["inputs"]["steps"] == 6
        assert result["5"]["inputs"]["cfg"] == 1.5
        assert result["6"]["inputs"]["noise_seed"] == 42
        assert result["9"]["inputs"]["sampler_name"] == "euler"


class TestSD15ManifestDriven:
    """Manifest-driven tests for sd15_txt2img workflow."""

    def test_all_params_patch_correctly(
        self, sd15_template: Dict[str, Any], sd15_manifest: Dict[str, Any]
    ):
        """Test that ALL params defined in manifest patch correctly."""
        from server.workflow_patcher import apply_patch

        manifest_params = sd15_manifest.get("params", {})

        for param_name, param_def in manifest_params.items():
            test_value = _generate_test_value(param_def)

            params = {"prompt": "test prompt"}
            if param_name != "prompt":
                params[param_name] = test_value
            else:
                params["prompt"] = test_value

            result = apply_patch(sd15_template, sd15_manifest, params)

            patch_def = param_def.get("patch", {})
            node_id = patch_def.get("node_id")
            field_path = patch_def.get("field")

            if node_id and field_path:
                actual = _get_nested_value(result, node_id, field_path)
                assert actual == test_value, (
                    f"Parameter '{param_name}' not patched correctly. "
                    f"Expected {test_value!r}, got {actual!r}"
                )


class TestWan22ManifestDriven:
    """Manifest-driven tests for wan2_2_ti2v_5b workflow."""

    def test_all_params_patch_correctly(
        self, wan22_template: Dict[str, Any], wan22_manifest: Dict[str, Any]
    ):
        """Test that ALL params defined in manifest patch correctly."""
        from server.workflow_patcher import apply_patch

        manifest_params = wan22_manifest.get("params", {})

        for param_name, param_def in manifest_params.items():
            test_value = _generate_test_value(param_def)

            # Required params for this workflow
            params = {
                "prompt": "test prompt",
                "start_image": "test_input.png",
            }
            if param_name == "prompt":
                params["prompt"] = test_value
            elif param_name == "start_image":
                params["start_image"] = test_value
            else:
                params[param_name] = test_value

            result = apply_patch(wan22_template, wan22_manifest, params)

            patch_def = param_def.get("patch", {})
            node_id = patch_def.get("node_id")
            field_path = patch_def.get("field")

            if node_id and field_path:
                actual = _get_nested_value(result, node_id, field_path)
                assert actual == test_value, (
                    f"Parameter '{param_name}' not patched correctly. "
                    f"Expected {test_value!r}, got {actual!r}"
                )

    def test_start_image_patches_to_load_image(
        self, wan22_template: Dict[str, Any], wan22_manifest: Dict[str, Any]
    ):
        """Start image should patch to LoadImage node."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "test",
            "start_image": "input.png",
        }
        result = apply_patch(wan22_template, wan22_manifest, params)

        assert result["56"]["inputs"]["image"] == "input.png"

    def test_dimensions_length_patch_to_latent(
        self, wan22_template: Dict[str, Any], wan22_manifest: Dict[str, Any]
    ):
        """Width/height/length should patch Wan22ImageToVideoLatent."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "test",
            "start_image": "input.png",
            "width": 640,
            "height": 352,
            "length": 24,
        }
        result = apply_patch(wan22_template, wan22_manifest, params)

        assert result["55"]["inputs"]["width"] == 640
        assert result["55"]["inputs"]["height"] == 352
        assert result["55"]["inputs"]["length"] == 24

    def test_fps_patches_create_video(
        self, wan22_template: Dict[str, Any], wan22_manifest: Dict[str, Any]
    ):
        """FPS should patch CreateVideo node."""
        from server.workflow_patcher import apply_patch

        params = {
            "prompt": "test",
            "start_image": "input.png",
            "fps": 12,
        }
        result = apply_patch(wan22_template, wan22_manifest, params)

        assert result["57"]["inputs"]["fps"] == 12
