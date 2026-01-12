from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Tuple


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def new_asset_filename(*, prefix: str = "asset", ext: str = ".png") -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}_{uuid.uuid4().hex[:10]}{ext}"


def write_bytes(path: str, data: bytes) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data)
