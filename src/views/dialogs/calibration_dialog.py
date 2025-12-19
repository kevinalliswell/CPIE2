#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数标定对话框
用于计算像素到毫米的转换参数
"""

import cv2
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap


class CalibrationDialog(QDialog):
    """参数标定对话框"""
    
    calibration_completed = Signal(float)  # 标定完成信号，传递 mm_per_pixel 值
    
    def __init__(self, flame_kit, parent=None):
        super().__init__(parent)
        self.flame_kit = flame_kit
        self.points = []  # 存储用户点击的两个点
        self.current_image = None  # 当前显示的图像
        self.display_image = None  # 用于显示的图像（带标记）
        self.preview_timer = None
        
        self.setWindowTitle("参数标定 - FlameKit")
        self.resize(900, 700)
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 说明文字
        instruction_group = QGroupBox("标定说明")
        instruction_layout = QVBoxLayout()
        instruction_text = QLabel(
            "1. 在相机视野中放置已知长度的参考物（如标尺）\n"
            "2. 点击【捕获图像】按钮获取标定图像\n"
            "3. 在图像上点击参考物的起点和终点\n"
            "4. 输入参考物的实际长度（毫米）\n"
            "5. 点击【完成标定】保存参数"
        )
        instruction_text.setWordWrap(True)
        instruction_layout.addWidget(instruction_text)
        instruction_group.setLayout(instruction_layout)
        layout.addWidget(instruction_group)
        
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #000000; }")
        self.image_label.mousePressEvent = self._on_image_click
        layout.addWidget(self.image_label)
        
        # 信息显示
        self.info_label = QLabel("请先点击【捕获图像】按钮")
        self.info_label.setStyleSheet("QLabel { color: #0066cc; font-weight: bold; }")
        layout.addWidget(self.info_label)
        
        # 输入区域
        input_group = QGroupBox("参数输入")
        input_layout = QHBoxLayout()
        
        input_layout.addWidget(QLabel("参考物实际长度:"))
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("输入实际长度（毫米）")
        self.length_input.setEnabled(False)
        input_layout.addWidget(self.length_input)
        input_layout.addWidget(QLabel("mm"))
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览相机")
        self.preview_btn.clicked.connect(self._toggle_preview)
        button_layout.addWidget(self.preview_btn)
        
        self.capture_btn = QPushButton("捕获图像")
        self.capture_btn.clicked.connect(self._capture_image)
        button_layout.addWidget(self.capture_btn)
        
        self.reset_btn = QPushButton("重新标定")
        self.reset_btn.clicked.connect(self._reset_calibration)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)
        
        self.complete_btn = QPushButton("完成标定")
        self.complete_btn.clicked.connect(self._complete_calibration)
        self.complete_btn.setEnabled(False)
        button_layout.addWidget(self.complete_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def _toggle_preview(self):
        """切换预览状态"""
        if self.preview_timer and self.preview_timer.isActive():
            # 停止预览
            self.preview_timer.stop()
            self.preview_btn.setText("预览相机")
            self.capture_btn.setEnabled(True)
            self.info_label.setText("预览已停止")
        else:
            # 开始预览
            if not self.flame_kit.initialize():
                QMessageBox.critical(self, "错误", "相机初始化失败！")
                return
                
            self.preview_timer = QTimer(self)
            self.preview_timer.timeout.connect(self._update_preview)
            self.preview_timer.start(33)  # 约30fps
            self.preview_btn.setText("停止预览")
            self.capture_btn.setEnabled(False)
            self.info_label.setText("预览中...")
            
    def _update_preview(self):
        """更新预览图像"""
        try:
            frame = self.flame_kit.camera.capture_single_frame()
            if frame is not None:
                self._display_frame(frame)
        except Exception as e:
            self.info_label.setText(f"预览错误: {e}")
            
    def _capture_image(self):
        """捕获标定图像"""
        try:
            # 初始化相机
            if not self.flame_kit.initialize():
                QMessageBox.critical(self, "错误", "相机初始化失败！")
                return
                
            # 捕获一帧
            self.info_label.setText("正在捕获图像...")
            frame = self.flame_kit.camera.capture_single_frame()
            
            if frame is None:
                QMessageBox.critical(self, "错误", "无法捕获图像！")
                return
                
            self.current_image = frame.copy()
            self.display_image = frame.copy()
            self._display_frame(self.display_image)
            
            self.info_label.setText("图像已捕获，请在图像上点击参考物的起点和终点")
            self.capture_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"捕获图像失败:\n{e}")
            
    def _on_image_click(self, event):
        """处理图像点击事件"""
        if self.current_image is None:
            return
            
        if len(self.points) >= 2:
            return
            
        # 获取点击位置（需要转换坐标）
        label_width = self.image_label.width()
        label_height = self.image_label.height()
        
        # 获取显示的图像尺寸
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return
            
        pixmap_width = pixmap.width()
        pixmap_height = pixmap.height()
        
        # 计算图像在label中的位置（居中显示）
        x_offset = (label_width - pixmap_width) // 2
        y_offset = (label_height - pixmap_height) // 2
        
        # 获取相对于pixmap的坐标
        click_x = event.pos().x() - x_offset
        click_y = event.pos().y() - y_offset
        
        # 检查点击是否在图像范围内
        if click_x < 0 or click_x >= pixmap_width or click_y < 0 or click_y >= pixmap_height:
            return
            
        # 计算缩放比例
        scale_x = self.current_image.shape[1] / pixmap_width
        scale_y = self.current_image.shape[0] / pixmap_height
        
        # 转换到原始图像坐标
        orig_x = int(click_x * scale_x)
        orig_y = int(click_y * scale_y)
        
        # 添加点
        self.points.append((orig_x, orig_y))
        
        # 在图像上绘制标记
        self.display_image = self.current_image.copy()
        for i, pt in enumerate(self.points):
            cv2.circle(self.display_image, pt, 5, (0, 255, 0), -1)
            cv2.putText(self.display_image, f"P{i+1}", (pt[0]+10, pt[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        if len(self.points) == 2:
            # 绘制连线
            cv2.line(self.display_image, self.points[0], self.points[1], (0, 255, 0), 2)
            
            # 计算像素距离
            pixel_distance = np.sqrt(
                (self.points[1][0] - self.points[0][0]) ** 2 +
                (self.points[1][1] - self.points[0][1]) ** 2
            )
            
            # 显示像素距离
            mid_x = (self.points[0][0] + self.points[1][0]) // 2
            mid_y = (self.points[0][1] + self.points[1][1]) // 2
            text = f"{pixel_distance:.1f} px"
            cv2.putText(self.display_image, text, (mid_x - 50, mid_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            self.info_label.setText(f"已选择两个点，像素距离: {pixel_distance:.2f} px，请输入实际长度")
            self.length_input.setEnabled(True)
            self.complete_btn.setEnabled(True)
        else:
            self.info_label.setText(f"已选择点 {len(self.points)}/2，请继续点击")
            
        self._display_frame(self.display_image)
        
    def _display_frame(self, frame):
        """显示图像到label"""
        try:
            # 转换为RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # 创建QImage
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 缩放到label大小（保持宽高比）
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"显示图像错误: {e}")
            
    def _reset_calibration(self):
        """重置标定"""
        self.points = []
        if self.current_image is not None:
            self.display_image = self.current_image.copy()
            self._display_frame(self.display_image)
            
        self.info_label.setText("已重置，请重新在图像上点击两个点")
        self.length_input.clear()
        self.length_input.setEnabled(False)
        self.complete_btn.setEnabled(False)
        
    def _complete_calibration(self):
        """完成标定"""
        if len(self.points) < 2:
            QMessageBox.warning(self, "警告", "请先在图像上选择两个点！")
            return
            
        # 获取实际长度
        try:
            actual_length_mm = float(self.length_input.text())
        except ValueError:
            QMessageBox.warning(self, "警告", "请输入有效的长度数值！")
            return
            
        if actual_length_mm <= 0:
            QMessageBox.warning(self, "警告", "长度必须大于0！")
            return
            
        # 计算像素距离
        pixel_distance = np.sqrt(
            (self.points[1][0] - self.points[0][0]) ** 2 +
            (self.points[1][1] - self.points[0][1]) ** 2
        )
        
        if pixel_distance == 0:
            QMessageBox.warning(self, "警告", "两点距离为0，请重新选择！")
            return
            
        # 计算标定参数
        mm_per_pixel = actual_length_mm / pixel_distance
        
        # 显示结果
        result_msg = (
            f"标定完成！\n\n"
            f"像素距离: {pixel_distance:.2f} px\n"
            f"实际长度: {actual_length_mm:.4f} mm\n"
            f"标定参数: {mm_per_pixel:.6f} mm/pixel"
        )
        
        QMessageBox.information(self, "标定成功", result_msg)
        
        # 发送信号
        self.calibration_completed.emit(mm_per_pixel)
        
        # 关闭对话框
        self.accept()
        
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止预览
        if self.preview_timer and self.preview_timer.isActive():
            self.preview_timer.stop()
        event.accept()
        
    def reject(self):
        """取消按钮"""
        # 停止预览
        if self.preview_timer and self.preview_timer.isActive():
            self.preview_timer.stop()
        super().reject()
