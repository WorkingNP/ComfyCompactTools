"""Tests for image quality checking (black/white detection)."""
from __future__ import annotations

import io
import pytest
from PIL import Image

# Import will be available after implementation
# from server.image_quality import check_image_quality, ImageQualityError


def create_test_image(color: tuple, size: tuple = (100, 100)) -> bytes:
    """Create a test image with a solid color."""
    img = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_gradient_image(size: tuple = (100, 100)) -> bytes:
    """Create a test image with a gradient (not solid)."""
    img = Image.new("RGB", size)
    for x in range(size[0]):
        for y in range(size[1]):
            r = int(255 * x / size[0])
            g = int(255 * y / size[1])
            b = 128
            img.putpixel((x, y), (r, g, b))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_noisy_image(size: tuple = (100, 100)) -> bytes:
    """Create a test image with random noise."""
    import random

    img = Image.new("RGB", size)
    for x in range(size[0]):
        for y in range(size[1]):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            img.putpixel((x, y), (r, g, b))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestBlackImageDetection:
    """Tests for detecting pure black images."""

    def test_detect_pure_black(self):
        """Test that pure black images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        black_image = create_test_image((0, 0, 0))
        with pytest.raises(ImageQualityError, match="black"):
            check_image_quality(black_image)

    def test_detect_near_black(self):
        """Test that near-black images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        near_black = create_test_image((5, 5, 5))
        # May be detected as "black" or "single color" - both are valid
        with pytest.raises(ImageQualityError, match="(black|single color)"):
            check_image_quality(near_black)

    def test_dark_but_not_black_passes(self):
        """Test that dark (but not black) varied images pass."""
        from server.image_quality import check_image_quality

        # Use a dark gradient instead of solid color to avoid single-color detection
        dark_image = create_gradient_image(size=(100, 100))
        # Make it darker by creating a dimmer gradient
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(dark_image))
        # Darken the image
        pixels = list(img.getdata())
        new_pixels = [(max(0, r - 200), max(0, g - 200), max(0, b - 200)) for r, g, b in pixels]
        img.putdata(new_pixels)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        dark_gradient = buffer.getvalue()
        # Should not raise because it has variety
        check_image_quality(dark_gradient)


class TestWhiteImageDetection:
    """Tests for detecting pure white images."""

    def test_detect_pure_white(self):
        """Test that pure white images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        white_image = create_test_image((255, 255, 255))
        with pytest.raises(ImageQualityError, match="white"):
            check_image_quality(white_image)

    def test_detect_near_white(self):
        """Test that near-white images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        near_white = create_test_image((252, 252, 252))
        # May be detected as "white" or "single color" - both are valid
        with pytest.raises(ImageQualityError, match="(white|single color)"):
            check_image_quality(near_white)

    def test_light_but_not_white_passes(self):
        """Test that light (but not white) varied images pass."""
        from server.image_quality import check_image_quality

        # Use a light gradient instead of solid color to avoid single-color detection
        import io
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        for x in range(100):
            for y in range(100):
                # Light colors with variation
                r = 200 + (x * 55 // 100)
                g = 200 + (y * 55 // 100)
                b = 220
                img.putpixel((x, y), (r, g, b))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        light_gradient = buffer.getvalue()
        # Should not raise because it has variety
        check_image_quality(light_gradient)


class TestSingleColorDetection:
    """Tests for detecting single-color images."""

    def test_detect_solid_red(self):
        """Test that solid red images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        red_image = create_test_image((255, 0, 0))
        with pytest.raises(ImageQualityError, match="single color"):
            check_image_quality(red_image)

    def test_detect_solid_blue(self):
        """Test that solid blue images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        blue_image = create_test_image((0, 0, 255))
        with pytest.raises(ImageQualityError, match="single color"):
            check_image_quality(blue_image)

    def test_detect_solid_gray(self):
        """Test that solid gray images are detected."""
        from server.image_quality import check_image_quality, ImageQualityError

        gray_image = create_test_image((128, 128, 128))
        with pytest.raises(ImageQualityError, match="single color"):
            check_image_quality(gray_image)


class TestValidImages:
    """Tests for valid (non-problematic) images."""

    def test_gradient_image_passes(self):
        """Test that gradient images pass quality check."""
        from server.image_quality import check_image_quality

        gradient = create_gradient_image()
        # Should not raise
        check_image_quality(gradient)

    def test_noisy_image_passes(self):
        """Test that noisy/colorful images pass quality check."""
        from server.image_quality import check_image_quality

        noisy = create_noisy_image()
        # Should not raise
        check_image_quality(noisy)


class TestConfigurableThresholds:
    """Tests for configurable detection thresholds."""

    def test_custom_black_threshold(self):
        """Test that black threshold can be customized."""
        from server.image_quality import check_image_quality

        # Dark image that would normally pass
        dark_image = create_test_image((20, 20, 20))

        # With strict threshold, it should fail
        with pytest.raises(Exception):
            check_image_quality(dark_image, black_threshold=0.1)

    def test_custom_white_threshold(self):
        """Test that white threshold can be customized."""
        from server.image_quality import check_image_quality

        # Light image that would normally pass
        light_image = create_test_image((240, 240, 240))

        # With strict threshold, it should fail
        with pytest.raises(Exception):
            check_image_quality(light_image, white_threshold=0.9)

    def test_skip_checks_option(self):
        """Test that checks can be skipped entirely."""
        from server.image_quality import check_image_quality

        black_image = create_test_image((0, 0, 0))
        # Should not raise when skip_checks=True
        check_image_quality(black_image, skip_checks=True)


class TestSpecialFormats:
    """Tests for special image formats."""

    def test_grayscale_image(self):
        """Test handling of grayscale images."""
        from server.image_quality import check_image_quality

        img = Image.new("L", (100, 100), 128)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        grayscale = buffer.getvalue()

        # Solid grayscale should be detected
        with pytest.raises(Exception):
            check_image_quality(grayscale)

    def test_rgba_image(self):
        """Test handling of images with alpha channel."""
        from server.image_quality import check_image_quality, ImageQualityError

        img = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        rgba_black = buffer.getvalue()

        with pytest.raises(ImageQualityError, match="black"):
            check_image_quality(rgba_black)

    def test_valid_rgba_image(self):
        """Test that valid RGBA images pass."""
        from server.image_quality import check_image_quality

        img = Image.new("RGBA", (100, 100))
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), (x * 2, y * 2, 128, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        valid_rgba = buffer.getvalue()

        # Should not raise
        check_image_quality(valid_rgba)


class TestStddevCheck:
    """Tests for standard deviation (low variance) detection."""

    def test_low_variance_detected(self):
        """Test that low variance images are detected with stddev_min."""
        from server.image_quality import check_image_quality, ImageQualityError

        # Create an image with very similar colors (low variance)
        img = Image.new("RGB", (100, 100))
        for x in range(100):
            for y in range(100):
                # Very slight variation around gray
                r = 128 + (x % 2)
                g = 128 + (y % 2)
                b = 128
                img.putpixel((x, y), (r, g, b))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        low_variance = buffer.getvalue()

        # With a high stddev_min threshold, should fail
        with pytest.raises(ImageQualityError, match="low variance"):
            check_image_quality(low_variance, stddev_min=0.1)

    def test_high_variance_passes(self):
        """Test that high variance images pass stddev check."""
        from server.image_quality import check_image_quality

        gradient = create_gradient_image()
        # Should pass even with stddev_min set
        check_image_quality(gradient, stddev_min=0.01)

    def test_stddev_disabled_by_default(self):
        """Test that stddev check is disabled when stddev_min=0."""
        from server.image_quality import check_image_quality

        # Low variance image should pass when stddev_min=0 (default)
        img = Image.new("RGB", (100, 100))
        for x in range(100):
            for y in range(100):
                r = 128 + (x % 2)
                g = 128 + (y % 2)
                b = 128
                img.putpixel((x, y), (r, g, b))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        low_variance = buffer.getvalue()

        # Should pass with default stddev_min=0
        check_image_quality(low_variance)


class TestMinBytesCheck:
    """Tests for minimum file size check."""

    def test_small_file_detected(self):
        """Test that small files are detected with min_bytes."""
        from server.image_quality import check_image_quality, ImageQualityError

        # Create a tiny valid image
        img = Image.new("RGB", (10, 10), (128, 64, 192))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        tiny_image = buffer.getvalue()

        # With a high min_bytes threshold, should fail
        with pytest.raises(ImageQualityError, match="file too small"):
            check_image_quality(tiny_image, min_bytes=100000)

    def test_large_file_passes(self):
        """Test that large files pass min_bytes check."""
        from server.image_quality import check_image_quality

        large_image = create_noisy_image(size=(200, 200))
        # Noisy images don't compress well, so this should exceed 1000 bytes
        check_image_quality(large_image, min_bytes=1000)

    def test_min_bytes_disabled_by_default(self):
        """Test that min_bytes check is disabled when min_bytes=0."""
        from server.image_quality import check_image_quality

        # Tiny image should pass when min_bytes=0 (default)
        img = Image.new("RGB", (10, 10), (128, 64, 192))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        tiny_image = buffer.getvalue()

        # Should pass with default min_bytes=0 (but may fail single-color check)
        # Use gradient to avoid single-color
        tiny_gradient = create_gradient_image(size=(10, 10))
        check_image_quality(tiny_gradient)


class TestManifestQualityParams:
    """Tests for get_quality_params_from_manifest helper."""

    def test_extract_params_from_manifest(self):
        """Test extracting quality params from manifest."""
        from server.image_quality import get_quality_params_from_manifest

        manifest = {
            "id": "test",
            "quality_checks": {
                "black_threshold": 0.02,
                "white_threshold": 0.95,
                "stddev_min": 0.05,
                "min_bytes": 5000,
                "skip_checks": False,
            },
        }

        params = get_quality_params_from_manifest(manifest)
        assert params["black_threshold"] == 0.02
        assert params["white_threshold"] == 0.95
        assert params["stddev_min"] == 0.05
        assert params["min_bytes"] == 5000
        assert params["skip_checks"] is False

    def test_defaults_when_no_quality_checks(self):
        """Test default values when quality_checks not present."""
        from server.image_quality import get_quality_params_from_manifest

        manifest = {"id": "test"}
        params = get_quality_params_from_manifest(manifest)

        assert params["black_threshold"] == 0.01
        assert params["white_threshold"] == 0.99
        assert params["stddev_min"] == 0.0
        assert params["min_bytes"] == 0
        assert params["skip_checks"] is False

    def test_partial_quality_checks(self):
        """Test partial quality_checks section uses defaults for missing."""
        from server.image_quality import get_quality_params_from_manifest

        manifest = {
            "id": "test",
            "quality_checks": {
                "black_threshold": 0.05,
                # Other fields missing
            },
        }

        params = get_quality_params_from_manifest(manifest)
        assert params["black_threshold"] == 0.05
        assert params["white_threshold"] == 0.99  # default
        assert params["stddev_min"] == 0.0  # default


class TestGetImageInfo:
    """Tests for get_image_info helper."""

    def test_get_image_info_includes_size(self):
        """Test that get_image_info returns file size."""
        from server.image_quality import get_image_info

        image_data = create_gradient_image()
        info = get_image_info(image_data)

        assert "width" in info
        assert "height" in info
        assert "size_bytes" in info
        assert info["size_bytes"] == len(image_data)
        assert info["width"] == 100
        assert info["height"] == 100
