"""Model scanner utility for enumerating checkpoint and VAE files."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def scan_models(directory: str, extensions: List[str] = None) -> List[str]:
    """
    Scan directory for model files and return sorted list of filenames.

    Args:
        directory: Path to directory containing models
        extensions: List of file extensions (default: [".safetensors", ".ckpt", ".pt"])

    Returns:
        Sorted list of model filenames (not full paths)
        Returns empty list if directory doesn't exist or is empty
    """
    if extensions is None:
        extensions = [".safetensors", ".ckpt", ".pt"]

    path = Path(directory)

    if not path.exists():
        logger.warning(f"Model directory does not exist: {directory}")
        return []

    if not path.is_dir():
        logger.error(f"Model path is not a directory: {directory}")
        return []

    try:
        models = []
        for ext in extensions:
            models.extend(path.glob(f"*{ext}"))

        # Return filenames only (ComfyUI expects filenames, not paths)
        filenames = [f.name for f in models]
        logger.info(f"Found {len(filenames)} models in {directory}")
        return sorted(filenames)
    except PermissionError as e:
        logger.error(f"Permission denied accessing {directory}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error scanning {directory}: {e}")
        return []


def scan_checkpoints(checkpoints_dir: str) -> List[str]:
    """Convenience wrapper for checkpoint scanning."""
    return scan_models(checkpoints_dir)


def scan_vaes(vae_dir: str) -> List[str]:
    """Convenience wrapper for VAE scanning."""
    return scan_models(vae_dir)
