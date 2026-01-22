from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSettings, QCoreApplication
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QListView

from .favorites import FavoritesStore
from .file_index import FileListModel, MediaFilterProxyModel
from .settings import AppSettings
from .thumbnails import ThumbnailLoader, ThumbnailCache
from .widgets.grid_page import GridPage
from .widgets.viewer_page import ViewerPage


class MainWindow(QMainWindow):
    def __init__(self, start_path: Optional[str] = None) -> None:
        super().__init__()

        self.setWindowTitle("NimbleView")
        self.resize(1400, 900)

        self.settings = AppSettings(QSettings())

        self.favorites = FavoritesStore.load()
        self.thumbs = ThumbnailLoader(cache=ThumbnailCache(max_items=700))

        self.model = FileListModel(thumbs=self.thumbs, favorites=self.favorites)
        self.proxy = MediaFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.grid = GridPage(settings=self.settings, parent=self)
        self.grid.set_model(self.proxy)

        self.viewer = ViewerPage(thumbs=self.thumbs, favorites=self.favorites, parent=self)
        self.viewer.set_model(self.proxy)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.grid)
        self.stack.addWidget(self.viewer)
        self.setCentralWidget(self.stack)

        self.status = self.statusBar()
        self.status.showMessage("Ready", 2000)

        # Global actions
        act_fs = QAction("Fullscreen", self)
        act_fs.setShortcut(QKeySequence(Qt.Key.Key_F11))
        act_fs.triggered.connect(self.toggle_fullscreen)
        self.addAction(act_fs)

        act_open = QAction("Open Folder", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(lambda: self.grid._open_dialog())
        self.addAction(act_open)

        # Signals: grid
        self.grid.openFolderRequested.connect(self.open_folder)
        self.grid.openViewerRequested.connect(self.open_viewer)
        self.grid.favoriteToggleRequested.connect(self.toggle_favorite_from_index)
        self.grid.filtersChanged.connect(self.apply_filters)
        self.grid.sortChanged.connect(self.apply_sort)

        self.grid.thumbSizeChanged.connect(self.on_thumb_size_changed)
        self.grid.spacingChanged.connect(self.on_spacing_changed)
        self.grid.showLabelsChanged.connect(self.on_show_labels_changed)
        self.grid.includeSubfoldersChanged.connect(self.on_include_subfolders_changed)
        self.grid.fullscreenRequested.connect(self.toggle_fullscreen)

        # Signals: viewer
        self.viewer.backRequested.connect(self.back_to_grid)
        self.viewer.currentPathChanged.connect(self.on_current_path_changed)

        # Restore last folder
        if start_path:
            self._open_start_path(start_path)
        else:
            last = self.settings.value_str("last_folder", "")
            if last and os.path.isdir(last):
                self.open_folder(last)

        # Apply UI preferences to model/view
        self.grid.apply_thumb_size(self.grid.slider_size.value())
        self.model.set_thumb_size(self.grid.slider_size.value())
        self.grid.apply_spacing(self.grid.slider_spacing.value())

        self.apply_filters()
        self.apply_sort()

    def closeEvent(self, ev) -> None:
        # persist UI state
        try:
            self.grid.store_to_settings()
        except Exception:
            pass
        super().closeEvent(ev)

    def _open_start_path(self, start_path: str) -> None:
        p = Path(start_path)
        if p.is_dir():
            self.open_folder(str(p))
        elif p.is_file():
            self.open_folder(str(p.parent), select_file=str(p))
        else:
            # maybe a raw string path
            if os.path.isdir(start_path):
                self.open_folder(start_path)

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def open_folder(self, folder: str, select_file: Optional[str] = None) -> None:
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Open Folder", f"フォルダが見つかりません: {folder}")
            return

        include_sub = self.grid.include_subfolders()
        total = self.model.load_folder(folder, include_subfolders=include_sub)
        self.grid.set_current_folder(folder)
        self.settings.set_value("last_folder", folder)

        self.apply_filters()
        self.apply_sort()

        # select file if requested
        if select_file:
            self.select_path(select_file)

        self.status.showMessage(f"Loaded: {total} items  (subfolders={'ON' if include_sub else 'OFF'})", 4000)
        self.setWindowTitle(f"NimbleView — {folder}")

    def select_path(self, path: str) -> None:
        # Best-effort selection in the current proxy (after filtering/sort).
        row = self.model.row_for_path(path)
        if row is None:
            return
        src = self.model.index(row, 0)
        px = self.proxy.mapFromSource(src)
        if not px.isValid():
            return
        self.grid.list.setCurrentIndex(px)
        self.grid.list.scrollTo(px, QListView.ScrollHint.PositionAtCenter)

    def apply_filters(self) -> None:
        self.proxy.set_search_text(self.grid.search_text())
        self.proxy.set_show_images(self.grid.show_images())
        self.proxy.set_show_videos(self.grid.show_videos())
        self.proxy.set_favorites_only(self.grid.favorites_only())

        shown = self.proxy.rowCount()
        total = self.model.rowCount()
        self.status.showMessage(f"Items: {shown} / {total}", 2000)

    def apply_sort(self) -> None:
        mode = self.grid.sort_mode()
        asc = self.grid.sort_ascending()

        # cosmetic arrow
        self.grid.sort_order.setText("↑" if asc else "↓")

        if mode == "name":
            self.proxy.setSortRole(int(FileListModel.NameRole))
            default_asc = True
        elif mode == "mtime":
            self.proxy.setSortRole(int(FileListModel.MTimeRole))
            default_asc = False
        else:
            self.proxy.setSortRole(int(FileListModel.SizeRole))
            default_asc = False

        order = Qt.SortOrder.AscendingOrder if asc else Qt.SortOrder.DescendingOrder
        self.proxy.sort(0, order)

        # If user never touched sort order, you might want defaults per mode,
        # but we keep your explicit toggle as the single source of truth.

    def on_thumb_size_changed(self, size: int) -> None:
        self.grid.apply_thumb_size(size)
        self.model.set_thumb_size(size)
        self.settings.set_value("thumb_size", int(size))

    def on_spacing_changed(self, gap: int) -> None:
        self.grid.apply_spacing(gap)
        self.settings.set_value("thumb_gap", int(gap))

    def on_show_labels_changed(self, show: bool) -> None:
        self.grid.apply_show_labels(show)
        self.settings.set_value("show_labels", bool(show))

    def on_include_subfolders_changed(self, include_sub: bool) -> None:
        self.settings.set_value("include_subfolders", bool(include_sub))
        # reload current folder
        if self.model.current_folder:
            self.open_folder(self.model.current_folder)

    def toggle_favorite_from_index(self, proxy_index) -> None:
        if not proxy_index.isValid():
            return
        path = str(proxy_index.data(int(FileListModel.PathRole)) or "")
        if not path:
            return
        newv = self.favorites.toggle(path)
        self.model.notify_favorite_changed(path)
        # If "favorites only" is active, we must refilter.
        if self.grid.favorites_only():
            self.proxy.invalidateFilter()
        self.status.showMessage(("★ " if newv else "☆ ") + Path(path).name, 2000)

    def open_viewer(self, proxy_index) -> None:
        if not proxy_index.isValid():
            return
        self.viewer.open_index(proxy_index)
        self.stack.setCurrentWidget(self.viewer)
        self.viewer.setFocus()

    def back_to_grid(self) -> None:
        # stop video playback
        try:
            self.viewer.video.stop()
        except Exception:
            pass

        path = self.viewer.current_path()
        self.stack.setCurrentWidget(self.grid)
        self.grid.focus_list()
        if path:
            self.select_path(path)

    def on_current_path_changed(self, path: str) -> None:
        # Update favorite role in list
        if path:
            self.model.notify_favorite_changed(path)
        # Also reflect filter updates when favorites-only is ON
        if self.grid.favorites_only():
            self.proxy.invalidateFilter()
        self.status.showMessage(path, 2000)


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    # Make QSettings nice on Windows
    QCoreApplication.setOrganizationName("NimbleView")
    QCoreApplication.setApplicationName("NimbleView")
    QCoreApplication.setApplicationVersion("0.1.0")

    app = QApplication([sys.argv[0]] + argv)
    app.setQuitOnLastWindowClosed(True)

    start_path = argv[0] if argv else None
    win = MainWindow(start_path=start_path)
    win.show()
    return app.exec()
