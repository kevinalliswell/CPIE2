#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相机预览对话框（非阻塞）

用 QTimer 轮询相机单帧并显示在 QLabel 上，取代 flamekit 的 cv2.imshow 循环：
后者在 GUI 线程里阻塞最长 60 秒，期间主窗口、副屏和实验日志都无法刷新。
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout


class CameraPreviewDialog(QDialog):
    """相机实时预览窗口（非模态）"""

    def __init__(self, flame_kit, parent=None, fps: int = 30, timeout_s: float = 60.0):
        super().__init__(parent)
        self.flame_kit = flame_kit
        self.timeout_ms = int(max(0.0, timeout_s) * 1000)
        self.frame_count = 0

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

        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.setInterval(max(10, int(1000 / max(1, fps))))

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)

    # ------------------------------------------------------------------ 生命周期
    def start(self) -> bool:
        """初始化相机并开始预览；相机不可用时返回 False"""
        try:
            if not self.flame_kit.initialize():
                self.image_label.setText("相机未就绪，无法预览")
                return False
        except Exception as e:
            self.image_label.setText(f"相机初始化失败: {e}")
            return False
        self.frame_timer.start()
        if self.timeout_ms > 0:
            self.timeout_timer.start(self.timeout_ms)
        return True

    def stop(self):
        """停止预览定时器"""
        self.frame_timer.stop()
        self.timeout_timer.stop()

    def closeEvent(self, event):
        # QDialog.closeEvent 内部会调用 reject()，两处都停止定时器（幂等）
        self.stop()
        super().closeEvent(event)

    def reject(self):
        # Esc 键 / 关闭按钮：停止定时器后交给 QDialog 隐藏窗口。
        # 注意不能在这里调用 close()：QDialog.closeEvent 会再次调用 reject()，
        # 嵌套的 close() 被 Qt 忽略后外层关闭事件也会被取消，窗口无法关闭。
        self.stop()
        super().reject()

    # ------------------------------------------------------------------ 内部
    def _on_timeout(self):
        self.info_label.setText("预览已自动结束（超时）")
        self.frame_timer.stop()

    def _update_frame(self):
        try:
            frame = self.flame_kit.camera.capture_single_frame()
        except Exception as e:
            self.info_label.setText(f"预览错误: {e}")
            return
        if frame is None:
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
