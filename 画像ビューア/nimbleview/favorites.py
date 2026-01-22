from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QStandardPaths

FAV_SCHEMA_VERSION = 1


def _app_data_dir() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class FavoritesStore:
    """A tiny, robust favorites DB.

    - Stores absolute file paths.
    - Writes JSON under AppData (doesn't touch your media folders).
    - Atomic write to avoid corruption.
    """

    _favorites: set[str]
    _path: Path

    @classmethod
    def load(cls) -> "FavoritesStore":
        path = _app_data_dir() / "favorites.json"
        favs: set[str] = set()
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("version") == FAV_SCHEMA_VERSION:
                    raw = data.get("favorites", [])
                    if isinstance(raw, list):
                        favs = {str(x) for x in raw if isinstance(x, str)}
        except Exception:
            # If something is broken, we fail soft: start empty.
            favs = set()
        return cls(_favorites=favs, _path=path)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        payload = {
            "version": FAV_SCHEMA_VERSION,
            "favorites": sorted(self._favorites),
        }
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def is_favorite(self, path: str) -> bool:
        return os.path.abspath(path) in self._favorites

    def set_favorite(self, path: str, value: bool) -> bool:
        ap = os.path.abspath(path)
        changed = False
        if value:
            if ap not in self._favorites:
                self._favorites.add(ap)
                changed = True
        else:
            if ap in self._favorites:
                self._favorites.remove(ap)
                changed = True
        if changed:
            self.save()
        return value

    def toggle(self, path: str) -> bool:
        ap = os.path.abspath(path)
        new_value = ap not in self._favorites
        self.set_favorite(ap, new_value)
        return new_value

    def bulk_set(self, paths: Iterable[str], value: bool) -> None:
        changed = False
        for p in paths:
            ap = os.path.abspath(p)
            if value:
                if ap not in self._favorites:
                    self._favorites.add(ap)
                    changed = True
            else:
                if ap in self._favorites:
                    self._favorites.remove(ap)
                    changed = True
        if changed:
            self.save()

    def all(self) -> set[str]:
        return set(self._favorites)
