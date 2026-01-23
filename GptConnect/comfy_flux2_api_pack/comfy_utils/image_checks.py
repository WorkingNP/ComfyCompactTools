"""
Image validation utilities for ComfyUI API pack.

Provides functions to verify that generated images are valid PNGs
and not blank/single-color images.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image, ImageStat

# PNG signature: first 8 bytes
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Default thresholds for blank image detection
DEFAULT_STDDEV_THRESHOLD = 5.0  # If max stddev across channels is below this, likely blank
DEFAULT_MEAN_LOW = 10  # If mean is below this, likely black
DEFAULT_MEAN_HIGH = 245  # If mean is above this, likely white


class ImageValidationError(Exception):
    """Raised when image validation fails."""
    pass


def is_valid_png_signature(path: Union[str, Path]) -> bool:
    """Check if file starts with valid PNG signature."""
    path = Path(path)
    if not path.exists():
        return False
    with open(path, "rb") as f:
        header = f.read(8)
    return header == PNG_SIGNATURE


def get_image_stats(path: Union[str, Path]) -> dict:
    """
    Get image statistics for blank detection.

    Returns:
        dict with keys:
            - mean: list of mean values per channel
            - stddev: list of stddev values per channel
            - max_stddev: maximum stddev across channels
            - min_mean: minimum mean across channels
            - max_mean: maximum mean across channels
    """
    with Image.open(path) as img:
        # Convert to RGB if necessary (handles RGBA, L, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        stat = ImageStat.Stat(img)
        mean = stat.mean
        stddev = stat.stddev

        return {
            "mean": mean,
            "stddev": stddev,
            "max_stddev": max(stddev),
            "min_mean": min(mean),
            "max_mean": max(mean),
        }


def is_blank_image(
    path: Union[str, Path],
    stddev_threshold: float = DEFAULT_STDDEV_THRESHOLD,
    mean_low: float = DEFAULT_MEAN_LOW,
    mean_high: float = DEFAULT_MEAN_HIGH,
) -> bool:
    """
    Check if image appears to be blank (single color).

    Detection criteria:
    1. Max stddev across channels < threshold (low variation = uniform color)
    2. AND (mean < mean_low OR mean > mean_high) as supplementary check

    Args:
        path: Path to image file
        stddev_threshold: Max stddev threshold for blank detection
        mean_low: Mean below this suggests black image
        mean_high: Mean above this suggests white image

    Returns:
        True if image appears to be blank/single-color
    """
    stats = get_image_stats(path)

    # Primary check: low variation indicates uniform color
    if stats["max_stddev"] < stddev_threshold:
        # If stddev is very low, it's likely a single color
        # Additional check: is it extremely dark or bright?
        if stats["min_mean"] < mean_low or stats["max_mean"] > mean_high:
            return True
        # Even if not extreme, very low stddev is suspicious
        if stats["max_stddev"] < 1.0:
            return True

    return False


def assert_valid_png(path: Union[str, Path]) -> None:
    """
    Assert that file exists and has valid PNG signature.

    Raises:
        ImageValidationError: If file is missing or not a valid PNG
    """
    path = Path(path)

    if not path.exists():
        raise ImageValidationError(f"File does not exist: {path}")

    if path.stat().st_size == 0:
        raise ImageValidationError(f"File is empty: {path}")

    if not is_valid_png_signature(path):
        raise ImageValidationError(f"File does not have valid PNG signature: {path}")


def assert_not_blank_image(
    path: Union[str, Path],
    stddev_threshold: float = DEFAULT_STDDEV_THRESHOLD,
    mean_low: float = DEFAULT_MEAN_LOW,
    mean_high: float = DEFAULT_MEAN_HIGH,
) -> None:
    """
    Assert that image is not blank (single color like black/white).

    This function first validates the PNG, then checks for blank images.

    Args:
        path: Path to image file
        stddev_threshold: Max stddev threshold for blank detection
        mean_low: Mean below this suggests black image
        mean_high: Mean above this suggests white image

    Raises:
        ImageValidationError: If image is invalid or appears blank
    """
    path = Path(path)

    # First, validate it's a proper PNG
    assert_valid_png(path)

    # Then check if it's blank
    if is_blank_image(path, stddev_threshold, mean_low, mean_high):
        stats = get_image_stats(path)
        raise ImageValidationError(
            f"Image appears to be blank/single-color: {path}\n"
            f"  mean={stats['mean']}, stddev={stats['stddev']}"
        )
