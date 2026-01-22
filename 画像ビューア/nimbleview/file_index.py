from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QSortFilterProxyModel

from .constants import classify
from .favorites import FavoritesStore
from .thumbnails import ThumbnailLoader


@dataclass(frozen=True)
class FileItem:
    path: str
    name: str  # without extension
    ext: str   # with dot
    kind: str  # 'image' | 'video'
    mtime: float
    size: int


class FileListModel(QAbstractListModel):
    """Source model: all media files in the current folder (optionally recursive)."""

    # Custom roles
    PathRole = Qt.ItemDataRole.UserRole + 1
    KindRole = Qt.ItemDataRole.UserRole + 2
    NameRole = Qt.ItemDataRole.UserRole + 3
    ExtRole = Qt.ItemDataRole.UserRole + 4
    MTimeRole = Qt.ItemDataRole.UserRole + 5
    SizeRole = Qt.ItemDataRole.UserRole + 6
    FavoriteRole = Qt.ItemDataRole.UserRole + 7

    def __init__(self, thumbs: ThumbnailLoader, favorites: FavoritesStore) -> None:
        super().__init__()
        self._thumbs = thumbs
        self._favorites = favorites
        self._items: list[FileItem] = []
        self._row_by_path: dict[str, int] = {}
        self._thumb_size: int = 256
        self.current_folder: str = ""
        self.include_subfolders: bool = False

        self._thumbs.thumbnailReady.connect(self._on_thumb_ready)

    def set_thumb_size(self, size: int) -> None:
        size = int(size)
        if size <= 0:
            return
        if size == self._thumb_size:
            return
        self._thumb_size = size
        # repaint everything (new cache keys)
        if self.rowCount() > 0:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, 0)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DecorationRole])

    def thumb_size(self) -> int:
        return self._thumb_size

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def roleNames(self) -> dict[int, bytes]:
        roles = super().roleNames()
        roles.update({
            int(self.PathRole): b"path",
            int(self.KindRole): b"kind",
            int(self.NameRole): b"name",
            int(self.ExtRole): b"ext",
            int(self.MTimeRole): b"mtime",
            int(self.SizeRole): b"size",
            int(self.FavoriteRole): b"favorite",
        })
        return roles

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        it = self._items[row]

        if role == Qt.ItemDataRole.DisplayRole:
            return it.name

        if role == Qt.ItemDataRole.ToolTipRole:
            # full filename, includes extension
            return Path(it.path).name

        if role == Qt.ItemDataRole.DecorationRole:
            size = self._thumb_size
            pm = self._thumbs.cache.get(it.path, size)
            if pm is None:
                self._thumbs.request(it.path, it.kind, size)
                pm = self._thumbs.placeholder_pixmap(it.kind, size)
            return pm  # we'll use a custom delegate; returning QPixmap is fine

        if role == int(self.PathRole):
            return it.path
        if role == int(self.KindRole):
            return it.kind
        if role == int(self.NameRole):
            return it.name
        if role == int(self.ExtRole):
            return it.ext
        if role == int(self.MTimeRole):
            return it.mtime
        if role == int(self.SizeRole):
            return it.size
        if role == int(self.FavoriteRole):
            return self._favorites.is_favorite(it.path)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def item_at(self, row: int) -> Optional[FileItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def row_for_path(self, path: str) -> Optional[int]:
        return self._row_by_path.get(os.path.abspath(path))

    def notify_favorite_changed(self, path: str) -> None:
        row = self.row_for_path(path)
        if row is None:
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [int(self.FavoriteRole)])

    def load_folder(self, folder: str, include_subfolders: bool = False) -> int:
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return 0

        self.beginResetModel()
        self._items = []
        self._row_by_path = {}
        self.current_folder = folder
        self.include_subfolders = include_subfolders

        paths = list(_iter_media_files(folder, recursive=include_subfolders))
        items: list[FileItem] = []
        for p in paths:
            kind = classify(p)
            if kind is None:
                continue
            try:
                st = os.stat(p)
                name = Path(p).stem
                ext = Path(p).suffix.lower()
                items.append(FileItem(
                    path=p,
                    name=name,
                    ext=ext,
                    kind=kind,
                    mtime=float(st.st_mtime),
                    size=int(st.st_size),
                ))
            except OSError:
                continue

        self._items = items
        for i, it in enumerate(self._items):
            self._row_by_path[os.path.abspath(it.path)] = i

        self.endResetModel()
        return len(self._items)

    def _on_thumb_ready(self, path: str, size: int) -> None:
        # only repaint rows that match; ignore other folders
        row = self._row_by_path.get(os.path.abspath(path))
        if row is None:
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DecorationRole])


class MediaFilterProxyModel(QSortFilterProxyModel):
    """Filtering + sorting.

    Filters:
    - search (name contains)
    - kind toggles (images/videos)
    - favorites only
    """

    def __init__(self) -> None:
        super().__init__()
        self.search_text: str = ""
        self.show_images: bool = True
        self.show_videos: bool = True
        self.favorites_only: bool = False

        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_search_text(self, text: str) -> None:
        self.search_text = text.strip()
        self.invalidateFilter()

    def set_show_images(self, v: bool) -> None:
        self.show_images = bool(v)
        self.invalidateFilter()

    def set_show_videos(self, v: bool) -> None:
        self.show_videos = bool(v)
        self.invalidateFilter()

    def set_favorites_only(self, v: bool) -> None:
        self.favorites_only = bool(v)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        idx = self.sourceModel().index(source_row, 0, source_parent)
        kind = idx.data(int(FileListModel.KindRole))
        if kind == "image" and not self.show_images:
            return False
        if kind == "video" and not self.show_videos:
            return False

        if self.favorites_only:
            fav = bool(idx.data(int(FileListModel.FavoriteRole)))
            if not fav:
                return False

        if self.search_text:
            name = str(idx.data(int(FileListModel.NameRole)) or "")
            ext = str(idx.data(int(FileListModel.ExtRole)) or "")
            hay = f"{name}{ext}".lower()
            if self.search_text.lower() not in hay:
                return False

        return True


def _iter_media_files(folder: str, recursive: bool) -> Iterable[str]:
    if not recursive:
        with os.scandir(folder) as it:
            for e in it:
                if not e.is_file():
                    continue
                yield e.path
        return

    for root, _dirs, files in os.walk(folder):
        for fn in files:
            yield os.path.join(root, fn)
