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
