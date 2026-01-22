from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QModelIndex, QSize
from PySide6.QtGui import QAction, QKeyEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListView,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QCheckBox,
    QComboBox,
    QSlider,
    QLabel,
    QToolButton,
    QMenu,
    QMessageBox,
)

from ..file_index import FileListModel, MediaFilterProxyModel
from ..settings import AppSettings
from .thumb_delegate import ThumbDelegate, DelegateConfig


class ThumbListView(QListView):
    openRequested = Signal(QModelIndex)
    favoriteToggleRequested = Signal(QModelIndex)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setSpacing(6)
        self.setWordWrap(False)
        self.setMouseTracking(True)
        self.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)

        self.doubleClicked.connect(self.openRequested.emit)

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        key = ev.key()
        mod = ev.modifiers()

        idx = self.currentIndex()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if idx.isValid():
                self.openRequested.emit(idx)
                return
        if key == Qt.Key.Key_F:
            if idx.isValid():
                self.favoriteToggleRequested.emit(idx)
                return

        super().keyPressEvent(ev)


class GridPage(QWidget):
    openFolderRequested = Signal(str)
    openViewerRequested = Signal(QModelIndex)      # proxy index
    favoriteToggleRequested = Signal(QModelIndex)  # proxy index
    filtersChanged = Signal()
    sortChanged = Signal()
    thumbSizeChanged = Signal(int)
    spacingChanged = Signal(int)
    showLabelsChanged = Signal(bool)
    includeSubfoldersChanged = Signal(bool)
    fullscreenRequested = Signal()

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.model: Optional[MediaFilterProxyModel] = None

        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("フォルダパスを入力して Enter（例: C:\\Users\\...）")
        self.path_edit.returnPressed.connect(self._open_path_from_edit)

        self.btn_open = QPushButton("Open", self)
        self.btn_open.clicked.connect(self._open_dialog)

        self.btn_up = QPushButton("Up", self)
        self.btn_up.clicked.connect(self._go_parent)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("検索（ファイル名）")
        self.search.textChanged.connect(lambda _t: self.filtersChanged.emit())

        self.chk_img = QCheckBox("IMG", self)
        self.chk_vid = QCheckBox("VID", self)
        self.chk_fav = QCheckBox("★", self)
        self.chk_img.stateChanged.connect(lambda _v: self.filtersChanged.emit())
        self.chk_vid.stateChanged.connect(lambda _v: self.filtersChanged.emit())
        self.chk_fav.stateChanged.connect(lambda _v: self.filtersChanged.emit())

        self.sort = QComboBox(self)
        self.sort.addItems(["名前", "更新日", "サイズ"])
        self.sort.currentIndexChanged.connect(lambda _i: self.sortChanged.emit())

        self.sort_order = QToolButton(self)
        self.sort_order.setText("↑")
        self.sort_order.setCheckable(True)
        self.sort_order.setChecked(False)  # False=descending by default for date/size, but we handle in main
        self.sort_order.toggled.connect(lambda _v: self.sortChanged.emit())
        self.sort_order.setToolTip("昇順/降順")

        self.slider_size = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_size.setRange(96, 420)
        self.slider_size.setSingleStep(8)
        self.slider_size.valueChanged.connect(self.thumbSizeChanged.emit)
        self.slider_size.setToolTip("サムネサイズ")

        self.slider_spacing = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_spacing.setRange(0, 24)
        self.slider_spacing.setSingleStep(1)
        self.slider_spacing.valueChanged.connect(self.spacingChanged.emit)
        self.slider_spacing.setToolTip("詰め込み密度（余白）")

        # settings menu
        self.btn_menu = QToolButton(self)
        self.btn_menu.setText("⚙")
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.act_labels = QAction("ファイル名を表示", self, checkable=True)
        self.act_subfolders = QAction("サブフォルダも含める", self, checkable=True)
        self.act_fullscreen = QAction("フルスクリーン", self)
        self.act_help = QAction("ショートカット", self)

        menu = QMenu(self.btn_menu)
        menu.addAction(self.act_labels)
        menu.addAction(self.act_subfolders)
        menu.addSeparator()
        menu.addAction(self.act_fullscreen)
        menu.addAction(self.act_help)
        self.btn_menu.setMenu(menu)

        self.act_labels.toggled.connect(self.showLabelsChanged.emit)
        self.act_subfolders.toggled.connect(self.includeSubfoldersChanged.emit)
        self.act_fullscreen.triggered.connect(self.fullscreenRequested.emit)
        self.act_help.triggered.connect(self._show_help)

        top = QWidget(self)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(8, 6, 8, 6)
        top_l.setSpacing(8)

        top_l.addWidget(self.btn_open)
        top_l.addWidget(self.btn_up)
        top_l.addWidget(self.path_edit, 2)
        top_l.addWidget(self.search, 1)
        top_l.addWidget(self.chk_img)
        top_l.addWidget(self.chk_vid)
        top_l.addWidget(self.chk_fav)
        top_l.addWidget(self.sort)
        top_l.addWidget(self.sort_order)
        top_l.addWidget(QLabel("Size", self))
        top_l.addWidget(self.slider_size, 1)
        top_l.addWidget(QLabel("Gap", self))
        top_l.addWidget(self.slider_spacing, 1)
        top_l.addWidget(self.btn_menu)

        self.list = ThumbListView(self)

        cfg = DelegateConfig(
            thumb_size=self.slider_size.value(),
            show_labels=self.act_labels.isChecked(),
            padding=6,
            label_height=18,
        )
        self.delegate = ThumbDelegate(cfg, self.list)
        self.list.setItemDelegate(self.delegate)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(top, 0)
        lay.addWidget(self.list, 1)

        self.setAcceptDrops(True)

        # Restore defaults
        self._restore_from_settings()

        # list signals
        self.list.openRequested.connect(self.openViewerRequested.emit)
        self.list.favoriteToggleRequested.connect(self.favoriteToggleRequested.emit)

    def set_model(self, proxy: MediaFilterProxyModel) -> None:
        self.model = proxy
        self.list.setModel(proxy)

    def current_index(self) -> QModelIndex:
        return self.list.currentIndex()

    def focus_list(self) -> None:
        self.list.setFocus()

    def set_current_folder(self, folder: str) -> None:
        self.path_edit.setText(folder)

    def set_item_count_hint(self, shown: int, total: int) -> None:
        # We keep it subtle: put it into the window title via main window status.
        pass

    def show_labels(self) -> bool:
        return self.act_labels.isChecked()

    def include_subfolders(self) -> bool:
        return self.act_subfolders.isChecked()

    def search_text(self) -> str:
        return self.search.text()

    def show_images(self) -> bool:
        return self.chk_img.isChecked()

    def show_videos(self) -> bool:
        return self.chk_vid.isChecked()

    def favorites_only(self) -> bool:
        return self.chk_fav.isChecked()

    def sort_mode(self) -> str:
        # 'name' | 'mtime' | 'size'
        i = self.sort.currentIndex()
        return "name" if i == 0 else ("mtime" if i == 1 else "size")

    def sort_ascending(self) -> bool:
        return self.sort_order.isChecked()

    def _open_dialog(self) -> None:
        start = self.path_edit.text().strip() or self.settings.value_str("last_folder", "")
        folder = QFileDialog.getExistingDirectory(self, "フォルダを開く", start)
        if folder:
            self.openFolderRequested.emit(folder)

    def _open_path_from_edit(self) -> None:
        p = self.path_edit.text().strip()
        if p:
            self.openFolderRequested.emit(p)

    def _go_parent(self) -> None:
        cur = self.path_edit.text().strip()
        if not cur:
            return
        parent = str(Path(cur).resolve().parent)
        self.openFolderRequested.emit(parent)

    def apply_thumb_size(self, size: int) -> None:
        size = int(size)
        self.delegate.set_thumb_size(size)
        self.list.setIconSize(QSize(size, size))
        pad = self.delegate.cfg.padding
        label_h = self.delegate.cfg.label_height if self.delegate.cfg.show_labels else 0
        self.list.setGridSize(QSize(size + pad * 2, size + pad * 2 + label_h))
        self.list.viewport().update()

    def apply_spacing(self, gap: int) -> None:
        self.list.setSpacing(int(gap))
        self.list.viewport().update()

    def apply_show_labels(self, show: bool) -> None:
        self.delegate.set_show_labels(bool(show))
        self.act_labels.setChecked(bool(show))
        self.apply_thumb_size(self.slider_size.value())

    def _restore_from_settings(self) -> None:
        # defaults that match your complaint: big + dense
        size = self.settings.value_int("thumb_size", 260)
        gap = self.settings.value_int("thumb_gap", 6)
        show_labels = self.settings.value_bool("show_labels", False)
        show_img = self.settings.value_bool("show_images", True)
        show_vid = self.settings.value_bool("show_videos", True)
        fav_only = self.settings.value_bool("favorites_only", False)
        include_sub = self.settings.value_bool("include_subfolders", False)

        self.slider_size.setValue(size)
        self.slider_spacing.setValue(gap)
        self.chk_img.setChecked(show_img)
        self.chk_vid.setChecked(show_vid)
        self.chk_fav.setChecked(fav_only)
        self.act_labels.setChecked(show_labels)
        self.act_subfolders.setChecked(include_sub)

        self.apply_show_labels(show_labels)
        self.apply_thumb_size(size)
        self.apply_spacing(gap)

    def store_to_settings(self) -> None:
        self.settings.set_value("thumb_size", int(self.slider_size.value()))
        self.settings.set_value("thumb_gap", int(self.slider_spacing.value()))
        self.settings.set_value("show_labels", bool(self.act_labels.isChecked()))
        self.settings.set_value("show_images", bool(self.chk_img.isChecked()))
        self.settings.set_value("show_videos", bool(self.chk_vid.isChecked()))
        self.settings.set_value("favorites_only", bool(self.chk_fav.isChecked()))
        self.settings.set_value("include_subfolders", bool(self.act_subfolders.isChecked()))
        self.settings.set_value("last_folder", self.path_edit.text().strip())

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "ショートカット",
            """【グリッド】
Enter/ダブルクリック: 開く
F: ★トグル
Ctrl+O: フォルダを開く
Alt+↑: 親フォルダへ
Ctrl+F: 検索へ
Esc: 検索クリア

【ビューアー】
←/→: 前/次
F: ★トグル
Z: 前後プレビュー表示切替
(画像) 0: Fit / 1: 100%
(動画) Space: 再生/停止 / L: ループ / C: フレーム保存

F11: フルスクリーン
""",
        )

    # Drag & drop: folder or file
    def dragEnterEvent(self, ev: QDragEnterEvent) -> None:
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev: QDropEvent) -> None:
        urls = ev.mimeData().urls()
        if not urls:
            return
        local = urls[0].toLocalFile()
        if not local:
            return
        p = Path(local)
        if p.is_dir():
            self.openFolderRequested.emit(str(p))
            return
        if p.is_file():
            self.openFolderRequested.emit(str(p.parent))
            # selection of the file is handled by main window (best effort)
            return

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        # Top-level shortcuts when the page has focus.
        if ev.key() == Qt.Key.Key_F11:
            self.fullscreenRequested.emit()
            return
        if ev.key() == Qt.Key.Key_F and ev.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.search.setFocus()
            return
        if ev.key() == Qt.Key.Key_O and ev.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._open_dialog()
            return
        if ev.key() == Qt.Key.Key_Up and ev.modifiers() == Qt.KeyboardModifier.AltModifier:
            self._go_parent()
            return
        super().keyPressEvent(ev)
