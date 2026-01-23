import os
import sys
from pathlib import Path

# Add parent directory to sys.path for imports
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

import pytest
import requests


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "offline: mark test as offline (no ComfyUI required)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end (requires ComfyUI)"
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("COMFY_BASE_URL", "http://127.0.0.1:8188").rstrip("/")


def _is_comfyui_up(base_url: str) -> bool:
    """Check if ComfyUI is running."""
    try:
        r = requests.get(f"{base_url}/object_info", timeout=5)
        r.raise_for_status()
        return True
    except Exception:
        return False


def _assert_comfyui_up(base_url: str) -> None:
    try:
        r = requests.get(f"{base_url}/object_info", timeout=5)
        r.raise_for_status()
    except Exception as e:
        raise AssertionError(
            "ComfyUI が起動していない、または API に接続できません。\n"
            f"  - 想定URL: {base_url}\n"
            "  - 対処: ComfyUI を起動してから再実行してください。\n"
            "  - ヒント: COMFY_BASE_URL 環境変数でURLを変更できます。\n"
        ) from e


@pytest.fixture(scope="session")
def comfyui_available(base_url: str) -> bool:
    """Returns True if ComfyUI is available, False otherwise."""
    return _is_comfyui_up(base_url)


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip E2E tests if ComfyUI is not running.
    Tests marked with @pytest.mark.offline will always run.
    Tests marked with @pytest.mark.e2e require ComfyUI.
    """
    base_url = os.environ.get("COMFY_BASE_URL", "http://127.0.0.1:8188").rstrip("/")
    comfyui_up = _is_comfyui_up(base_url)

    skip_e2e = pytest.mark.skip(
        reason="ComfyUI が起動していないため E2E テストをスキップします。"
    )

    for item in items:
        # Skip E2E tests if ComfyUI is not running
        if "e2e" in item.keywords and not comfyui_up:
            item.add_marker(skip_e2e)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to the fixtures directory."""
    return repo_root() / "tests" / "fixtures"
