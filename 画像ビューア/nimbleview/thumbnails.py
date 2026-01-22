from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, QSize, Qt
from PySide6.QtGui import (
    QImage,
    QImageReader,
    QPainter,
    QPixmap,
    QFont,
    QColor,
)

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # optional


@dataclass(frozen=True)
class ThumbKey:
    path: str
    size: int


class ThumbnailCache:
    """Very simple LRU cache (by item count).

    QPixmap is a GUI-thread object, so this cache should be used on the GUI thread.
    """

    def __init__(self, max_items: int = 600) -> None:
        self.max_items = max_items
        self._lru: "OrderedDict[ThumbKey, QPixmap]" = OrderedDict()

    def get(self, path: str, size: int) -> Optional[QPixmap]:
        key = ThumbKey(os.path.abspath(path), int(size))
        pix = self._lru.get(key)
        if pix is None:
            return None
        # bump
        self._lru.move_to_end(key, last=True)
        return pix

    def put(self, path: str, size: int, pixmap: QPixmap) -> None:
        key = ThumbKey(os.path.abspath(path), int(size))
        self._lru[key] = pixmap
        self._lru.move_to_end(key, last=True)
        while len(self._lru) > self.max_items:
            self._lru.popitem(last=False)

    def clear(self) -> None:
        self._lru.clear()


class _WorkerSignals(QObject):
    result = Signal(str, int, QImage)  # path, size, image
    failed = Signal(str, int, str)     # path, size, error


class ThumbnailWorker(QRunnable):
    """Loads/creates a *QImage* thumbnail in a worker thread."""

    def __init__(self, path: str, kind: str, size: int) -> None:
        super().__init__()
        self.path = path
        self.kind = kind
        self.size = int(size)
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            img = self._make_thumb_image()
            self.signals.result.emit(self.path, self.size, img)
        except Exception as e:
            self.signals.failed.emit(self.path, self.size, str(e))

    def _make_thumb_image(self) -> QImage:
        size = self.size
        # A square canvas; we letterbox into it.
        canvas = QImage(size, size, QImage.Format.Format_ARGB32)
        canvas.fill(QColor(24, 24, 24))

        if self.kind == "image":
            reader = QImageReader(self.path)
            try:
                reader.setAutoTransform(True)
            except Exception:
                pass

            orig = reader.size()
            if orig.isValid() and orig.width() > 0 and orig.height() > 0:
                scale = min(size / orig.width(), size / orig.height())
                sw = max(1, int(orig.width() * scale))
                sh = max(1, int(orig.height() * scale))
                try:
                    reader.setScaledSize(QSize(sw, sh))
                except Exception:
                    pass

            img = reader.read()
            if img.isNull():
                return self._draw_placeholder(canvas, text="IMG")

            # center
            p = QPainter(canvas)
            x = (size - img.width()) // 2
            y = (size - img.height()) // 2
            p.drawImage(x, y, img)
            p.end()
            return canvas

        if self.kind == "video":
            if cv2 is None:
                return self._draw_placeholder(canvas, text="VID")

            cap = cv2.VideoCapture(self.path)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return self._draw_placeholder(canvas, text="VID")

            # BGR -> RGB
            frame = frame[:, :, ::-1]
            h, w, _ = frame.shape
            # Create QImage wrapping the numpy buffer; then copy to detach.
            qimg = QImage(frame.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()

            # scale to fit
            qimg = qimg.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            p = QPainter(canvas)
            x = (size - qimg.width()) // 2
            y = (size - qimg.height()) // 2
            p.drawImage(x, y, qimg)
            p.end()
            return canvas

        return self._draw_placeholder(canvas, text="FILE")

    def _draw_placeholder(self, canvas: QImage, text: str) -> QImage:
        p = QPainter(canvas)
        p.setPen(QColor(220, 220, 220))
        f = QFont()
        f.setBold(True)
        f.setPointSize(max(10, int(self.size * 0.10)))
        p.setFont(f)
        p.drawText(canvas.rect(), int(Qt.AlignmentFlag.AlignCenter), text)
        p.end()
        return canvas


class ThumbnailLoader(QObject):
    """GUI-thread thumbnail manager.

    - Keeps an LRU cache of QPixmaps.
    - Schedules worker threads that generate QImages.
    - Converts to QPixmap on the GUI thread.
    """

    thumbnailReady = Signal(str, int)  # path, size

    def __init__(self, cache: ThumbnailCache | None = None) -> None:
        super().__init__()
        self.cache = cache or ThumbnailCache()
        self.pool = QThreadPool.globalInstance()
        self._inflight: set[ThumbKey] = set()
        self._placeholder_cache: dict[tuple[str, int], QPixmap] = {}

    def request(self, path: str, kind: str, size: int) -> None:
        key = ThumbKey(os.path.abspath(path), int(size))
        if self.cache.get(path, size) is not None:
            return
        if key in self._inflight:
            return

        self._inflight.add(key)
        worker = ThumbnailWorker(path=path, kind=kind, size=size)
        worker.signals.result.connect(self._on_result)
        worker.signals.failed.connect(self._on_failed)
        self.pool.start(worker)

    def _on_result(self, path: str, size: int, img: QImage) -> None:
        key = ThumbKey(os.path.abspath(path), int(size))
        self._inflight.discard(key)
        if not img.isNull():
            pix = QPixmap.fromImage(img)
            self.cache.put(path, size, pix)
            self.thumbnailReady.emit(path, size)
        else:
            # Still notify to repaint placeholder -> maybe later.
            self.thumbnailReady.emit(path, size)

    def _on_failed(self, path: str, size: int, error: str) -> None:
        key = ThumbKey(os.path.abspath(path), int(size))
        self._inflight.discard(key)
        # fail soft: keep placeholder
        self.thumbnailReady.emit(path, size)

    def placeholder_pixmap(self, kind: str, size: int) -> QPixmap:
        k = (kind, int(size))
        pix = self._placeholder_cache.get(k)
        if pix is not None:
            return pix

        s = int(size)
        pm = QPixmap(s, s)
        pm.fill(QColor(24, 24, 24))
        p = QPainter(pm)
        p.setPen(QColor(220, 220, 220))
        f = QFont()
        f.setBold(True)
        f.setPointSize(max(10, int(s * 0.10)))
        p.setFont(f)
        label = "IMG" if kind == "image" else ("VID" if kind == "video" else "FILE")
        p.drawText(pm.rect(), int(Qt.AlignmentFlag.AlignCenter), label)
        p.end()

        self._placeholder_cache[k] = pm
        return pm
