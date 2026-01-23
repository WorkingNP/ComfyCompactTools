"""
Offline tests using recorded fixtures.

These tests mock HTTP requests and use pre-recorded fixtures to verify
the client sequence works correctly without requiring ComfyUI.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import comfy_flux2_klein_generate as klein
from comfy_utils.image_checks import (
    assert_not_blank_image,
    assert_valid_png,
    is_blank_image,
    is_valid_png_signature,
    ImageValidationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def klein_fixtures_dir(fixtures_dir: Path) -> Path:
    """Path to klein_distilled_fp8 fixtures."""
    return fixtures_dir / "klein_distilled_fp8"


@pytest.fixture
def sample_history(klein_fixtures_dir: Path) -> dict:
    """Load sample history JSON from fixtures."""
    history_path = klein_fixtures_dir / "history_success.json"
    if not history_path.exists():
        pytest.skip(f"Fixture not found: {history_path}")
    with open(history_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_image_path(klein_fixtures_dir: Path) -> Path:
    """Path to sample output PNG."""
    img_path = klein_fixtures_dir / "sample_output.png"
    if not img_path.exists():
        pytest.skip(f"Fixture not found: {img_path}")
    return img_path


@pytest.fixture
def sample_image_bytes(sample_image_path: Path) -> bytes:
    """Raw bytes of sample output PNG."""
    return sample_image_path.read_bytes()


# ---------------------------------------------------------------------------
# Image Validation Tests (Unit Tests)
# ---------------------------------------------------------------------------

@pytest.mark.offline
class TestImageValidation:
    """Unit tests for image validation functions."""

    def test_valid_png_signature_with_real_png(self, sample_image_path: Path):
        """Real PNG should have valid signature."""
        assert is_valid_png_signature(sample_image_path) is True

    def test_valid_png_signature_with_non_png(self, tmp_path: Path):
        """Non-PNG file should fail signature check."""
        fake_file = tmp_path / "fake.png"
        fake_file.write_bytes(b"not a real png file")
        assert is_valid_png_signature(fake_file) is False

    def test_valid_png_signature_with_missing_file(self, tmp_path: Path):
        """Missing file should fail signature check."""
        assert is_valid_png_signature(tmp_path / "nonexistent.png") is False

    def test_assert_valid_png_with_real_png(self, sample_image_path: Path):
        """Real PNG should pass validation."""
        assert_valid_png(sample_image_path)  # Should not raise

    def test_assert_valid_png_with_empty_file(self, tmp_path: Path):
        """Empty file should fail validation."""
        empty_file = tmp_path / "empty.png"
        empty_file.write_bytes(b"")
        with pytest.raises(ImageValidationError, match="empty"):
            assert_valid_png(empty_file)

    def test_assert_valid_png_with_missing_file(self, tmp_path: Path):
        """Missing file should fail validation."""
        with pytest.raises(ImageValidationError, match="does not exist"):
            assert_valid_png(tmp_path / "nonexistent.png")

    def test_not_blank_with_real_image(self, sample_image_path: Path):
        """Real generated image should not be blank."""
        assert_not_blank_image(sample_image_path)  # Should not raise

    def test_is_blank_detects_black_image(self, tmp_path: Path):
        """Solid black image should be detected as blank."""
        from PIL import Image
        black_img = tmp_path / "black.png"
        img = Image.new("RGB", (64, 64), color=(0, 0, 0))
        img.save(black_img)
        assert is_blank_image(black_img) is True

    def test_is_blank_detects_white_image(self, tmp_path: Path):
        """Solid white image should be detected as blank."""
        from PIL import Image
        white_img = tmp_path / "white.png"
        img = Image.new("RGB", (64, 64), color=(255, 255, 255))
        img.save(white_img)
        assert is_blank_image(white_img) is True

    def test_assert_not_blank_raises_for_black(self, tmp_path: Path):
        """assert_not_blank_image should raise for solid black."""
        from PIL import Image
        black_img = tmp_path / "black.png"
        img = Image.new("RGB", (64, 64), color=(0, 0, 0))
        img.save(black_img)
        with pytest.raises(ImageValidationError, match="blank"):
            assert_not_blank_image(black_img)


# ---------------------------------------------------------------------------
# Template Parameter Tests
# ---------------------------------------------------------------------------

@pytest.mark.offline
class TestTemplateParameters:
    """Test that template parameters are correctly applied."""

    def test_set_params_applies_text(self, fixtures_dir: Path):
        """set_params should apply text prompts correctly."""
        template_path = fixtures_dir.parent.parent / "flux2_klein_4b_fp8_prompt_template.json"
        if not template_path.exists():
            pytest.skip(f"Template not found: {template_path}")

        prompt = klein.load_template(str(template_path))
        test_text = "a test prompt with specific content"
        test_negative = "bad quality"

        klein.set_params(
            prompt,
            text=test_text,
            negative=test_negative,
            width=512,
            height=768,
            steps=8,
            cfg=2.5,
            seed=42,
            sampler_name="dpmpp_2m",
            filename_prefix="test-prefix",
            text_encoder="test-encoder.safetensors",
            unet="test-unet.safetensors",
            vae="test-vae.safetensors",
            batch=2,
        )

        # Verify parameters were set
        assert prompt["2"]["inputs"]["text"] == test_text
        assert prompt["3"]["inputs"]["text"] == test_negative
        assert prompt["7"]["inputs"]["width"] == 512
        assert prompt["7"]["inputs"]["height"] == 768
        assert prompt["7"]["inputs"]["batch_size"] == 2
        assert prompt["8"]["inputs"]["steps"] == 8
        assert prompt["5"]["inputs"]["cfg"] == 2.5
        assert prompt["6"]["inputs"]["noise_seed"] == 42
        assert prompt["9"]["inputs"]["sampler_name"] == "dpmpp_2m"
        assert prompt["13"]["inputs"]["filename_prefix"] == "test-prefix"


# ---------------------------------------------------------------------------
# Client Sequence Tests (HTTP Mocked)
# ---------------------------------------------------------------------------

@pytest.mark.offline
class TestClientSequenceMocked:
    """Test the full client sequence with mocked HTTP."""

    def test_queue_prompt_returns_prompt_id(self):
        """queue_prompt should return prompt_id from response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"prompt_id": "test-prompt-id-123"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            prompt_id = klein.queue_prompt(
                "http://localhost:8188",
                {"test": "prompt"},
                "test-client-id"
            )

            assert prompt_id == "test-prompt-id-123"
            mock_post.assert_called_once()

    def test_extract_images_from_history(self, sample_history: dict):
        """extract_images should correctly parse history response."""
        # sample_history is the full history response
        # We need to get the history item (value for the prompt_id key)
        if isinstance(sample_history, dict):
            # If it's the raw history format {prompt_id: {...}}
            if "outputs" not in sample_history:
                # Get first value
                history_item = next(iter(sample_history.values()))
            else:
                history_item = sample_history
        else:
            pytest.skip("Invalid history format")

        images = klein.extract_images(history_item)
        assert len(images) > 0, "Should extract at least one image"
        assert "filename" in images[0]
        assert "subfolder" in images[0]
        assert "type" in images[0]

    def test_full_sequence_with_mock(
        self, sample_history: dict, sample_image_bytes: bytes, tmp_path: Path
    ):
        """Test full sequence: queue -> wait -> extract -> download."""
        prompt_id = "mock-prompt-id-" + uuid.uuid4().hex[:8]

        # Get history item
        if "outputs" not in sample_history:
            history_item = next(iter(sample_history.values()))
        else:
            history_item = sample_history

        # Mock responses
        queue_response = MagicMock()
        queue_response.json.return_value = {"prompt_id": prompt_id}
        queue_response.raise_for_status = MagicMock()

        # History response (returns the full history with prompt_id as key)
        history_response = MagicMock()
        history_response.json.return_value = {prompt_id: history_item}
        history_response.raise_for_status = MagicMock()

        # View response (image download)
        view_response = MagicMock()
        view_response.content = sample_image_bytes
        view_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=queue_response), \
             patch("requests.get") as mock_get:

            # Set up get to return different responses based on URL
            def get_side_effect(url, **kwargs):
                if "/history/" in url:
                    return history_response
                elif "/view" in url:
                    return view_response
                return MagicMock()

            mock_get.side_effect = get_side_effect

            # Execute the sequence
            base_url = "http://localhost:8188"

            # 1. Queue prompt
            returned_prompt_id = klein.queue_prompt(
                base_url, {"test": "prompt"}, "test-client"
            )
            assert returned_prompt_id == prompt_id

            # 2. Wait for history
            hist = klein.wait_history(base_url, prompt_id, timeout_s=5)
            assert hist is not None

            # 3. Extract images
            images = klein.extract_images(hist)
            assert len(images) > 0

            # 4. Download image
            out_path = klein.download_image(base_url, images[0], tmp_path)
            assert out_path.exists()
            assert out_path.stat().st_size > 0

            # 5. Validate image
            assert_valid_png(out_path)
            assert_not_blank_image(out_path)
