#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相机预览对话框（非阻塞）

取帧在后台线程中进行，GUI 线程只显示最新一帧，取代 flamekit 的 cv2.imshow 循环：
后者在 GUI 线程里阻塞最长 60 秒。相机 SDK 单次取帧的超时为 1 秒，
若在 GUI 线程轮询，相机停止出帧时主窗口每次都会卡住 1 秒。

注意：预览线程运行期间不能有其他代码访问相机；拍摄、标定、释放相机前必须先 stop()/close()。
"""

import threading
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout


class CameraPreviewDialog(QDialog):
    """相机实时预览窗口（非模态）"""

    # 后台取帧线程 -> GUI 线程（跨线程自动为队列连接）
    _frame_available = Signal()
    _capture_error = Signal(str)

    # stop() 等待取帧线程退出的上限：须大于 SDK 单次取帧超时（1 s）
    STOP_JOIN_TIMEOUT_S = 2.0

    def __init__(self, flame_kit, parent=None, fps: int = 30, timeout_s: float = 60.0):
        super().__init__(parent)
        self.flame_kit = flame_kit
        self.timeout_ms = int(max(0.0, timeout_s) * 1000)
        self.frame_interval_s = 1.0 / max(1, int(fps))
        self.frame_count = 0

        self._stop_event = threading.Event()
        self._worker = None
        self._frame_lock = threading.Lock()
        self._latest_frame = None

        self.setWindowTitle("相机预览")
        self.setModal(False)
        self.resize(800, 640)

        layout = QVBoxLayout(self)
        self.image_label = QLabel("正在打开相机...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("background-color: #202020; color: #cccccc;")
        layout.addWidget(self.image_label, 1)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.close_button = QPushButton("关闭预览")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self._frame_available.connect(self._show_latest_frame)
        self._capture_error.connect(self._on_capture_error)

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)

    # ------------------------------------------------------------------ 生命周期
    def start(self) -> bool:
        """初始化相机并启动后台取帧；相机不可用时返回 False"""
        if self.is_running():
            return True
        try:
            if not self.flame_kit.initialize():
                self.image_label.setText("相机未就绪，无法预览")
                return False
        except Exception as e:
            self.image_label.setText(f"相机初始化失败: {e}")
            return False

        self._stop_event.clear()
        self._worker = threading.Thread(target=self._acquire_loop, name="camera-preview", daemon=True)
        self._worker.start()
        if self.timeout_ms > 0:
            self.timeout_timer.start(self.timeout_ms)
        return True

    def is_running(self) -> bool:
        """后台取帧线程是否仍在运行"""
        return self._worker is not None and self._worker.is_alive()

    def stop(self) -> bool:
        """停止预览并等待取帧线程退出；返回 False 表示线程未能在时限内退出"""
        self.timeout_timer.stop()
        self._stop_event.set()
        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(self.STOP_JOIN_TIMEOUT_S)
            if worker.is_alive():
                return False
        self._worker = None
        return True

    def closeEvent(self, event):
        # QDialog.closeEvent 内部会调用 reject()，两处都停止预览（幂等）
        self.stop()
        super().closeEvent(event)

    def reject(self):
        # Esc 键 / 关闭按钮：停止预览后交给 QDialog 隐藏窗口。
        # 注意不能在这里调用 close()：QDialog.closeEvent 会再次调用 reject()，
        # 嵌套的 close() 被 Qt 忽略后外层关闭事件也会被取消，窗口无法关闭。
        self.stop()
        super().reject()

    # ------------------------------------------------------------------ 后台取帧
    def _acquire_loop(self):
        """后台线程：循环取帧，只保留最新一帧，交给 GUI 线程显示"""
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                frame = self.flame_kit.camera.capture_single_frame()
            except Exception as e:
                if not self._emit_safely(self._capture_error, str(e)):
                    return
                self._stop_event.wait(0.5)  # 避免相机故障时空转
                continue

            if frame is not None and not self._stop_event.is_set():
                with self._frame_lock:
                    display_pending = self._latest_frame is not None
                    self._latest_frame = frame
                # GUI 尚未取走上一帧时不再发信号，避免事件队列堆积
                if not display_pending and not self._emit_safely(self._frame_available):
                    return

            remaining = self.frame_interval_s - (time.monotonic() - started)
            if remaining > 0:
                self._stop_event.wait(remaining)

    @staticmethod
    def _emit_safely(signal, *args) -> bool:
        """对话框已销毁时发信号会抛 RuntimeError，此时结束取帧线程"""
        try:
            signal.emit(*args)
            return True
        except RuntimeError:
            return False

    # ------------------------------------------------------------------ GUI 线程
    def _on_timeout(self):
        self._stop_event.set()
        self.info_label.setText("预览已自动结束（超时）")

    def _on_capture_error(self, message: str):
        self.info_label.setText(f"预览错误: {message}")

    def _show_latest_frame(self):
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
        if frame is None or self._stop_event.is_set():
            return
        self.frame_count += 1
        self._display_frame(frame)

    def _display_frame(self, frame):
        try:
            if frame.ndim == 2:
                h, w = frame.shape
                q_image = QImage(frame.data, w, h, w, QImage.Format_Grayscale8)
            else:
                import cv2
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                q_image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image.copy())
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.info_label.setText(f"{w}×{h}  已显示 {self.frame_count} 帧")
        except Exception as e:
            self.info_label.setText(f"显示图像错误: {e}")
