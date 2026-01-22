from __future__ import annotations

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff",
}

VIDEO_EXTS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".m4v", ".mpg", ".mpeg",
}

def classify(path: str) -> str | None:
    """Return 'image' / 'video' / None"""
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None
