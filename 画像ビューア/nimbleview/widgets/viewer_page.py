from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QSizePolicy,
    QToolButton,
)

from ..file_index import FileListModel, MediaFilterProxyModel
from ..favorites import FavoritesStore
from ..thumbnails import ThumbnailLoader
from .clickable_label import ClickableLabel
from .image_canvas import ImageCanvas
from .video_player import VideoPlayer


class ViewerPage(QWidget):
    backRequested = Signal()
    currentPathChanged = Signal(str)

    def __init__(self, thumbs: ThumbnailLoader, favorites: FavoritesStore, parent=None) -> None:
        super().__init__(parent)
        self.thumbs = thumbs
        self.favorites = favorites
        self.model: Optional[MediaFilterProxyModel] = None
        self.current_row: int = -1
        self._current_path: str = ""
        self._previews_visible = True
        self._prev: Optional[Tuple[str, str]] = None  # (path, kind)
        self._next: Optional[Tuple[str, str]] = None

        self.btn_back = QPushButton("← Grid", self)
        self.btn_back.clicked.connect(self.backRequested.emit)

        self.lbl_title = QLabel("", self)
        self.lbl_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.btn_fav = QToolButton(self)
        self.btn_fav.setText("☆")
        self.btn_fav.clicked.connect(self.toggle_favorite)

        top = QWidget(self)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(8, 6, 8, 6)
        top_l.setSpacing(10)
        top_l.addWidget(self.btn_back)
        top_l.addWidget(self.lbl_title, 1)
        top_l.addWidget(self.btn_fav)

        # previews
        self.prev_preview = ClickableLabel(self)
        self.next_preview = ClickableLabel(self)
        for lab in (self.prev_preview, self.next_preview):
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setFixedWidth(220)
            lab.setStyleSheet("background: #0f0f0f;")
            lab.setScaledContents(False)

        self.prev_preview.clicked.connect(self.prev)
        self.next_preview.clicked.connect(self.next)

        self.stack = QStackedWidget(self)
        self.image = ImageCanvas(self)
        self.video = VideoPlayer(self)
        self.stack.addWidget(self.image)
        self.stack.addWidget(self.video)

        self.video.frameSaved.connect(self._on_frame_saved)

        mid = QWidget(self)
        mid_l = QHBoxLayout(mid)
        mid_l.setContentsMargins(0, 0, 0, 0)
        mid_l.setSpacing(0)
        mid_l.addWidget(self.prev_preview, 0)
        mid_l.addWidget(self.stack, 1)
        mid_l.addWidget(self.next_preview, 0)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(top, 0)
        lay.addWidget(mid, 1)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.thumbs.thumbnailReady.connect(self._on_thumb_ready)

    def set_model(self, proxy: MediaFilterProxyModel) -> None:
        self.model = proxy

    def open_index(self, proxy_index: QModelIndex) -> None:
        if not proxy_index.isValid():
            return
        self.open_row(proxy_index.row())

    def open_row(self, row: int) -> None:
        if self.model is None:
            return
        if row < 0 or row >= self.model.rowCount():
            return

        self.current_row = row
        idx = self.model.index(row, 0)
        path = str(idx.data(int(FileListModel.PathRole)) or "")
        kind = str(idx.data(int(FileListModel.KindRole)) or "")
        self._current_path = path
        self.currentPathChanged.emit(path)

        title = Path(path).name if path else ""
        self.lbl_title.setText(title)
        self._update_fav_button()

        if kind == "video":
            self.stack.setCurrentWidget(self.video)
            self.video.set_loop(True)
            self.video.set_video(path)
        else:
            self.video.stop()
            self.stack.setCurrentWidget(self.image)
            self.image.set_image(path)

        self._update_previews()

    def current_path(self) -> str:
        return self._current_path

    def _update_fav_button(self) -> None:
        if not self._current_path:
            self.btn_fav.setText("☆")
            return
        is_f = self.favorites.is_favorite(self._current_path)
        self.btn_fav.setText("★" if is_f else "☆")

    def toggle_favorite(self) -> None:
        if not self._current_path:
            return
        self.favorites.toggle(self._current_path)
        self._update_fav_button()
        self.currentPathChanged.emit(self._current_path)

    def prev(self) -> None:
        if self.model is None:
            return
        if self.current_row <= 0:
            return
        self.open_row(self.current_row - 1)

    def next(self) -> None:
        if self.model is None:
            return
        if self.current_row < 0:
            return
        if self.current_row + 1 >= self.model.rowCount():
            return
        self.open_row(self.current_row + 1)

    def _update_previews(self) -> None:
        self._prev = None
        self._next = None

        if self.model is None:
            return

        if not self._previews_visible:
            self.prev_preview.hide()
            self.next_preview.hide()
            return

        self.prev_preview.show()
        self.next_preview.show()

        # prev
        if self.current_row - 1 >= 0:
            i = self.model.index(self.current_row - 1, 0)
            p = str(i.data(int(FileListModel.PathRole)) or "")
            k = str(i.data(int(FileListModel.KindRole)) or "image")
            if p:
                self._prev = (p, k)
        # next
        if self.current_row + 1 < self.model.rowCount():
            i = self.model.index(self.current_row + 1, 0)
            p = str(i.data(int(FileListModel.PathRole)) or "")
            k = str(i.data(int(FileListModel.KindRole)) or "image")
            if p:
                self._next = (p, k)

        if self._prev is None:
            self.prev_preview.setPixmap(QPixmap())
            self.prev_preview.setText("")
            self.prev_preview.setToolTip("")
        else:
            self._set_preview_pixmap(self.prev_preview, self._prev[0], self._prev[1])

        if self._next is None:
            self.next_preview.setPixmap(QPixmap())
            self.next_preview.setText("")
            self.next_preview.setToolTip("")
        else:
            self._set_preview_pixmap(self.next_preview, self._next[0], self._next[1])

    def _set_preview_pixmap(self, label: QLabel, path: str, kind: str) -> None:
        size = 240  # preview thumb size
        pm = self.thumbs.cache.get(path, size)
        if pm is None:
            self.thumbs.request(path, kind, size)
            pm = self.thumbs.placeholder_pixmap(kind, size)

        # Scale to fit label
        target_w = max(1, label.width())
        target_h = max(1, label.height())
        scaled = pm.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        label.setPixmap(scaled)
        label.setText("")
        label.setToolTip(path)

    def _on_thumb_ready(self, path: str, size: int) -> None:
        if not self._previews_visible:
            return
        if self._prev and path == self._prev[0] and size == 240:
            self._set_preview_pixmap(self.prev_preview, self._prev[0], self._prev[1])
        if self._next and path == self._next[0] and size == 240:
            self._set_preview_pixmap(self.next_preview, self._next[0], self._next[1])

    def _on_frame_saved(self, out_path: str) -> None:
        # title hint (status bar is nicer; main window also shows it)
        try:
            self.lbl_title.setText(f"{Path(self._current_path).name}   (Saved: {Path(out_path).name})")
        except Exception:
            pass

    def toggle_previews(self) -> None:
        self._previews_visible = not self._previews_visible
        self._update_previews()

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        key = ev.key()

        if key == Qt.Key.Key_Escape:
            self.backRequested.emit()
            return

        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.prev()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.next()
            return

        if key == Qt.Key.Key_F:
            self.toggle_favorite()
            return

        if key == Qt.Key.Key_Z:
            self.toggle_previews()
            return

        # image controls
        if self.stack.currentWidget() == self.image:
            if key == Qt.Key.Key_0:
                self.image.fit()
                return
            if key == Qt.Key.Key_1:
                self.image.zoom_100()
                return

        # video controls
        if self.stack.currentWidget() == self.video:
            if key == Qt.Key.Key_Space:
                self.video.toggle_play()
                return
            if key == Qt.Key.Key_L:
                self.video.set_loop(not self.video.loop_enabled)
                return
            if key == Qt.Key.Key_C:
                # Quick capture next to the file
                if self._current_path:
                    base = Path(self._current_path)
                    out = base.parent / (base.stem + "_frame.png")
                    n = 1
                    while out.exists():
                        out = base.parent / f"{base.stem}_frame_{n:03d}.png"
                        n += 1
                    self.video.capture_frame(str(out))
                return

        super().keyPressEvent(ev)
