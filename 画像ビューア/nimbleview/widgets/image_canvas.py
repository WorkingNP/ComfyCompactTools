from __future__ import annotations

import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImageReader, QWheelEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem


class ImageCanvas(QGraphicsView):
    """Zoomable/pannable image viewer (no chrome)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self._item = QGraphicsPixmapItem()
        self.scene().addItem(self._item)

        self.setRenderHints(self.renderHints() | QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(Qt.GlobalColor.black)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._fit_mode = True
        self._has_pixmap = False

    def has_image(self) -> bool:
        return self._has_pixmap

    def set_image(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            self._item.setPixmap(QPixmap())
            self._has_pixmap = False
            return False

        reader = QImageReader(path)
        try:
            reader.setAutoTransform(True)
        except Exception:
            pass

        img = reader.read()
        if img.isNull():
            self._item.setPixmap(QPixmap())
            self._has_pixmap = False
            return False

        pm = QPixmap.fromImage(img)
        self._item.setPixmap(pm)
        self._has_pixmap = True
        self._fit_mode = True
        self._reset_view()
        return True

    def _reset_view(self) -> None:
        self.setTransform(self.transform().identity())
        self.scene().setSceneRect(self._item.boundingRect())
        if self._has_pixmap:
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)

    def fit(self) -> None:
        if not self._has_pixmap:
            return
        self._fit_mode = True
        self._reset_view()

    def zoom_100(self) -> None:
        if not self._has_pixmap:
            return
        self._fit_mode = False
        self.setTransform(self.transform().identity())

    def wheelEvent(self, ev: QWheelEvent) -> None:
        if not self._has_pixmap:
            return super().wheelEvent(ev)
        # zoom
        delta = ev.angleDelta().y()
        if delta == 0:
            return
        self._fit_mode = False
        factor = 1.25 if delta > 0 else 0.8
        self.scale(factor, factor)

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        if self._fit_mode and self._has_pixmap:
            self._reset_view()

    def mouseDoubleClickEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._has_pixmap:
            # toggle fit / 100
            if self._fit_mode:
                self.zoom_100()
            else:
                self.fit()
        super().mouseDoubleClickEvent(ev)
