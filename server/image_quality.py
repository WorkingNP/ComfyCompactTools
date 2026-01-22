"""Image quality checks for detecting problematic outputs."""
from __future__ import annotations

import io
from typing import Optional

from PIL import Image


class ImageQualityError(Exception):
    """Raised when image fails quality checks."""

    pass


def check_image_quality(
    image_data: bytes,
    black_threshold: float = 0.01,
    white_threshold: float = 0.99,
    skip_checks: bool = False,
) -> None:
    """Check if an image passes quality checks.

    Detects:
    - Pure black images (failed generation)
    - Pure white images (failed generation)
    - Single-color images (likely failed)

    Args:
        image_data: Raw image bytes (PNG, JPEG, etc.)
        black_threshold: Brightness below this is "black" (0-1)
        white_threshold: Brightness above this is "white" (0-1)
        skip_checks: If True, skip all checks

    Raises:
        ImageQualityError: If image fails quality checks
    """
    if skip_checks:
        return

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
    color_set = set()
    sample_size = min(num_pixels, 10000)  # Sample for large images
    step = max(1, num_pixels // sample_size)

    for i in range(0, num_pixels, step):
        r, g, b = pixels[i]
        brightness = (r + g + b) / (3 * 255)  # Normalize to 0-1
        total_brightness += brightness
        color_set.add((r, g, b))

    sampled_count = (num_pixels + step - 1) // step
    avg_brightness = total_brightness / sampled_count

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


def get_image_info(image_data: bytes) -> dict:
    """Get basic information about an image.

    Args:
        image_data: Raw image bytes

    Returns:
        Dict with width, height, mode, format info
    """
    img = Image.open(io.BytesIO(image_data))
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
    }
