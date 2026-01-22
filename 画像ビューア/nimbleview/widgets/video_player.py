from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QStyle,
    QSizePolicy,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


def _format_ms(ms: int) -> str:
    if ms < 0:
        ms = 0
    s = ms // 1000
    m = s // 60
    s = s % 60
    h = m // 60
    m = m % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class VideoPlayer(QWidget):
    frameSaved = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.video = QVideoWidget(self)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)

        # capture frames via the widget's video sink
        self._last_frame: Optional[QImage] = None
        try:
            sink = self.video.videoSink()
            sink.videoFrameChanged.connect(self._on_frame)
        except Exception:
            sink = None

        self.loop_enabled = True
        self._dragging = False
        self._current_path: str = ""

        self.btn_play = QPushButton(self)
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_loop = QPushButton("Loop: ON", self)
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(True)
        self.btn_loop.clicked.connect(self._toggle_loop_button)

        self.btn_capture = QPushButton("Capture", self)
        self.btn_capture.clicked.connect(self.capture_frame_dialog)

        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.slider.sliderMoved.connect(self._on_slider_moved)

        self.time = QLabel("00:00 / 00:00", self)
        self.time.setMinimumWidth(110)
        self.time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        bar = QWidget(self)
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(8, 6, 8, 6)
        bar_l.setSpacing(8)
        bar_l.addWidget(self.btn_play)
        bar_l.addWidget(self.slider, 1)
        bar_l.addWidget(self.time)
        bar_l.addWidget(self.btn_loop)
        bar_l.addWidget(self.btn_capture)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.video, 1)
        lay.addWidget(bar, 0)

        self.player.durationChanged.connect(self._on_duration)
        self.player.positionChanged.connect(self._on_position)
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.playbackStateChanged.connect(self._on_state)

    def set_video(self, path: str) -> None:
        self.stop()
        self._last_frame = None
        self._current_path = path
        if not path or not os.path.exists(path):
            return
        url = QUrl.fromLocalFile(path)
        self.player.setSource(url)
        self.player.play()

    def toggle_play(self) -> None:
        st = self.player.playbackState()
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self) -> None:
        try:
            self.player.stop()
        except Exception:
            pass

    def set_loop(self, enabled: bool) -> None:
        self.loop_enabled = bool(enabled)
        self.btn_loop.setChecked(self.loop_enabled)
        self.btn_loop.setText("Loop: ON" if self.loop_enabled else "Loop: OFF")

    def _toggle_loop_button(self) -> None:
        self.set_loop(self.btn_loop.isChecked())

    def _on_duration(self, dur: int) -> None:
        self.slider.setRange(0, max(0, int(dur)))
        self._update_time_label()

    def _on_position(self, pos: int) -> None:
        if not self._dragging:
            self.slider.setValue(int(pos))
        self._update_time_label()

    def _on_state(self, _state) -> None:
        st = self.player.playbackState()
        icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaPause if st == QMediaPlayer.PlaybackState.PlayingState
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.btn_play.setIcon(icon)

    def _on_status(self, status) -> None:
        # loop at end
        try:
            end = QMediaPlayer.MediaStatus.EndOfMedia
        except Exception:
            end = None
        if end is not None and status == end and self.loop_enabled:
            self.player.setPosition(0)
            self.player.play()

    def _on_slider_pressed(self) -> None:
        self._dragging = True

    def _on_slider_released(self) -> None:
        self._dragging = False
        self.player.setPosition(self.slider.value())

    def _on_slider_moved(self, _v: int) -> None:
        self._update_time_label(preview_pos=self.slider.value())

    def _update_time_label(self, preview_pos: Optional[int] = None) -> None:
        dur = int(self.player.duration() or 0)
        pos = int(preview_pos if preview_pos is not None else (self.player.position() or 0))
        self.time.setText(f"{_format_ms(pos)} / {_format_ms(dur)}")

    def _on_frame(self, frame) -> None:
        try:
            if frame is None or not frame.isValid():
                return
        except Exception:
            pass

        img = None
        try:
            img = frame.toImage()
        except Exception:
            # fallback: some Qt builds may not expose toImage; ignore
            img = None

        if isinstance(img, QImage) and not img.isNull():
            self._last_frame = img

    def capture_frame(self, out_path: str) -> bool:
        if self._last_frame is None or self._last_frame.isNull():
            QMessageBox.information(self, "Capture", "まだフレームが取得できていません（再生してから試してください）")
            return False

        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ok = self._last_frame.save(str(p))
        if ok:
            self.frameSaved.emit(str(p))
        return bool(ok)

    def capture_frame_dialog(self) -> None:
        if not self._current_path:
            return
        base = Path(self._current_path)
        default_name = base.with_suffix("").name + "_frame.png"
        default_dir = base.parent
        out, _ = QFileDialog.getSaveFileName(self, "フレームを保存", str(default_dir / default_name), "PNG (*.png)")
        if not out:
            return
        self.capture_frame(out)
