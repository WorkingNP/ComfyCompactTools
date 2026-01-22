from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QMouseEvent


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)
