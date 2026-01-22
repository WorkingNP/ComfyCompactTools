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
