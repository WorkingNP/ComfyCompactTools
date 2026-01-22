from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings


@dataclass
class AppSettings:
    """Thin wrapper around QSettings.

    Keeps UI preferences sticky across restarts.
    """

    q: QSettings

    def value_str(self, key: str, default: str = "") -> str:
        v = self.q.value(key, default)
        return str(v) if v is not None else default

    def value_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.q.value(key, default))
        except Exception:
            return default

    def value_bool(self, key: str, default: bool = False) -> bool:
        v = self.q.value(key, default)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in {"1", "true", "yes", "on"}
        try:
            return bool(int(v))
        except Exception:
            return bool(default)

    def set_value(self, key: str, value) -> None:
        self.q.setValue(key, value)
