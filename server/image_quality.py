"""Image quality checks for detecting problematic outputs."""
from __future__ import annotations

import io
import math
from typing import Optional

from PIL import Image


class ImageQualityError(Exception):
    """Raised when image fails quality checks."""

    pass


def check_image_quality(
    image_data: bytes,
    black_threshold: float = 0.01,
    white_threshold: float = 0.99,
    stddev_min: float = 0.0,
    min_bytes: int = 0,
    skip_checks: bool = False,
) -> None:
    """Check if an image passes quality checks.

    Detects:
    - Pure black images (failed generation)
    - Pure white images (failed generation)
    - Single-color images (likely failed)
    - Low variance images (stddev below threshold)
    - Too small files (below min_bytes)

    Args:
        image_data: Raw image bytes (PNG, JPEG, etc.)
        black_threshold: Brightness below this is "black" (0-1)
        white_threshold: Brightness above this is "white" (0-1)
        stddev_min: Minimum standard deviation of brightness (0-1 scale). 0 = disabled.
        min_bytes: Minimum file size in bytes. 0 = disabled.
        skip_checks: If True, skip all checks

    Raises:
        ImageQualityError: If image fails quality checks
    """
    if skip_checks:
        return

    # Check minimum file size first
    if min_bytes > 0 and len(image_data) < min_bytes:
        raise ImageQualityError(
            f"Image file too small: {len(image_data)} bytes (minimum: {min_bytes})"
        )

    # Load image
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary
    if img.mode == "RGBA":
        # Create white background and composite
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background
    elif img.mode == "L":
        # Grayscale - convert to RGB
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Get pixel data
    pixels = list(img.getdata())
    num_pixels = len(pixels)

    if num_pixels == 0:
        raise ImageQualityError("Image has no pixels")

    # Calculate statistics
    total_brightness = 0
    brightness_values = []
    color_set = set()
    sample_size = min(num_pixels, 10000)  # Sample for large images
    step = max(1, num_pixels // sample_size)

    for i in range(0, num_pixels, step):
        r, g, b = pixels[i]
        brightness = (r + g + b) / (3 * 255)  # Normalize to 0-1
        total_brightness += brightness
        brightness_values.append(brightness)
        color_set.add((r, g, b))

    sampled_count = len(brightness_values)
    avg_brightness = total_brightness / sampled_count

    # Calculate standard deviation of brightness
    if sampled_count > 1:
        variance = sum((b - avg_brightness) ** 2 for b in brightness_values) / sampled_count
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    # Check for single color FIRST (more specific error)
    # But only if it's not black or white (those have their own checks)
    is_black_ish = avg_brightness < black_threshold
    is_white_ish = avg_brightness > white_threshold

    # Check for pure black
    if is_black_ish:
        raise ImageQualityError(
            f"Image appears to be black (brightness: {avg_brightness:.4f})"
        )

    # Check for pure white
    if is_white_ish:
        raise ImageQualityError(
            f"Image appears to be white (brightness: {avg_brightness:.4f})"
        )

    # Check for single color (non-black, non-white)
    # Allow some tolerance for compression artifacts
    if len(color_set) <= 3:
        # Get the dominant color
        if len(color_set) == 1:
            dominant = list(color_set)[0]
            raise ImageQualityError(
                f"Image is a single color: RGB({dominant[0]}, {dominant[1]}, {dominant[2]})"
            )
        else:
            # Check if colors are very similar (likely single color with noise)
            colors = list(color_set)
            all_similar = True
            for c in colors[1:]:
                diff = sum(abs(a - b) for a, b in zip(colors[0], c))
                if diff > 15:  # Allow small differences
                    all_similar = False
                    break

            if all_similar:
                dominant = colors[0]
                raise ImageQualityError(
                    f"Image is a single color: RGB({dominant[0]}, {dominant[1]}, {dominant[2]})"
                )

    # Check for low variance (after single-color check to provide more specific error)
    if stddev_min > 0 and stddev < stddev_min:
        raise ImageQualityError(
            f"Image has low variance (stddev: {stddev:.4f}, minimum: {stddev_min:.4f})"
        )


def get_image_info(image_data: bytes) -> dict:
    """Get basic information about an image.

    Args:
        image_data: Raw image bytes

    Returns:
        Dict with width, height, mode, format, size info
    """
    img = Image.open(io.BytesIO(image_data))
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
        "size_bytes": len(image_data),
    }


def get_quality_params_from_manifest(manifest: dict) -> dict:
    """Extract quality check parameters from a workflow manifest.

    Args:
        manifest: Workflow manifest dict

    Returns:
        Dict with quality check parameters (can be passed to check_image_quality)
    """
    quality_checks = manifest.get("quality_checks", {})
    return {
        "black_threshold": quality_checks.get("black_threshold", 0.01),
        "white_threshold": quality_checks.get("white_threshold", 0.99),
        "stddev_min": quality_checks.get("stddev_min", 0.0),
        "min_bytes": quality_checks.get("min_bytes", 0),
        "skip_checks": quality_checks.get("skip_checks", False),
    }
