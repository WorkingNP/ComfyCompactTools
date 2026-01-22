import os
import sys
from pathlib import Path

# Add parent directory to sys.path for imports
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

import pytest
import requests


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("COMFY_BASE_URL", "http://127.0.0.1:8188").rstrip("/")


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


@pytest.fixture(scope="session", autouse=True)
def ensure_comfyui_running(base_url: str) -> None:
    _assert_comfyui_up(base_url)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
