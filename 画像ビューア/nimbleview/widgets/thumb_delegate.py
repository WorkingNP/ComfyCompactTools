from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle

from ..file_index import FileListModel


@dataclass
class DelegateConfig:
    thumb_size: int = 256
    show_labels: bool = False
    padding: int = 6
    label_height: int = 18


class ThumbDelegate(QStyledItemDelegate):
    def __init__(self, cfg: DelegateConfig, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg

    def set_thumb_size(self, s: int) -> None:
        self.cfg.thumb_size = int(s)

    def set_show_labels(self, v: bool) -> None:
        self.cfg.show_labels = bool(v)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()

        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # background
        if selected:
            painter.fillRect(rect, QColor(60, 90, 140, 140))
        else:
            painter.fillRect(rect, QColor(0, 0, 0, 0))

        pad = self.cfg.padding
        label_h = self.cfg.label_height if self.cfg.show_labels else 0

        thumb_rect = QRect(
            rect.left() + pad,
            rect.top() + pad,
            rect.width() - pad * 2,
            rect.height() - pad * 2 - label_h,
        )

        # thumbnail pixmap comes from DecorationRole (we return QPixmap from the model)
        pm = index.data(Qt.ItemDataRole.DecorationRole)
        if pm is not None:
            try:
                painter.drawPixmap(thumb_rect, pm)
            except Exception:
                pass

        # overlay: favorite star
        fav = bool(index.data(int(FileListModel.FavoriteRole)) or False)
        if fav:
            painter.setPen(QColor(255, 220, 90))
            f = QFont()
            f.setBold(True)
            f.setPointSize(14)
            painter.setFont(f)
            painter.drawText(thumb_rect.adjusted(6, 4, 0, 0), "★")

        # overlay: ext badge (bottom-right)
        ext = str(index.data(int(FileListModel.ExtRole)) or "").upper().lstrip(".")
        if ext:
            badge_text = ext
        else:
            kind = str(index.data(int(FileListModel.KindRole)) or "")
            badge_text = "VID" if kind == "video" else "IMG"

        # badge background
        badge_pad_x = 6
        badge_pad_y = 2
        f2 = QFont()
        f2.setBold(True)
        f2.setPointSize(9)
        painter.setFont(f2)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(badge_text)
        th = fm.height()

        badge_w = tw + badge_pad_x * 2
        badge_h = th + badge_pad_y * 2
        bx = thumb_rect.right() - badge_w - 6
        by = thumb_rect.bottom() - badge_h - 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.drawRoundedRect(bx, by, badge_w, badge_h, 6, 6)

        painter.setPen(QColor(235, 235, 235))
        painter.drawText(QRect(bx, by, badge_w, badge_h), int(Qt.AlignmentFlag.AlignCenter), badge_text)

        # label (optional)
        if self.cfg.show_labels:
            name = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            label_rect = QRect(
                rect.left() + pad,
                rect.bottom() - label_h - pad + 2,
                rect.width() - pad * 2,
                label_h,
            )
            painter.setPen(QColor(220, 220, 220))
            f3 = QFont()
            f3.setPointSize(9)
            painter.setFont(f3)
            elided = painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideMiddle, label_rect.width())
            painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), elided)

        # focus border
        if bool(option.state & QStyle.StateFlag.State_HasFocus):
            pen = QPen(QColor(180, 180, 180, 120))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        pad = self.cfg.padding
        label_h = self.cfg.label_height if self.cfg.show_labels else 0
        s = self.cfg.thumb_size + pad * 2
        return QSize(s, s + label_h)
