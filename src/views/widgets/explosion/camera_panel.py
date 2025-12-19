#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相机控制面板组件
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Signal


class CameraPanelWidget(QGroupBox):
    """相机控制面板组件"""
    
    # 信号定义
    init_camera_clicked = Signal()
    preview_clicked = Signal()
    capture_clicked = Signal()
    calibrate_clicked = Signal()
    analyze_clicked = Signal()
    
    def __init__(self, parent=None):
        """
        初始化相机面板
        
        Args:
            parent: 父组件
        """
        super().__init__("相机控制", parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        
        # 第1行第1列：初始化相机按钮
        btn_init_camera = QPushButton("初始化相机")
        btn_init_camera.setObjectName("primaryButton")
        btn_init_camera.clicked.connect(self.init_camera_clicked.emit)
        layout.addWidget(btn_init_camera, 0, 0)
        
        # 第1行第2列：预览按钮
        self.btn_preview = QPushButton("开始预览")
        self.btn_preview.setObjectName("standardButton")
        self.btn_preview.clicked.connect(self.preview_clicked.emit)
        self.btn_preview.setEnabled(False)
        layout.addWidget(self.btn_preview, 0, 1)
        
        # 第2行第1列：手动拍摄按钮
        self.btn_capture = QPushButton("手动拍摄")
        self.btn_capture.setObjectName("standardButton")
        self.btn_capture.clicked.connect(self.capture_clicked.emit)
        self.btn_capture.setEnabled(False)
        layout.addWidget(self.btn_capture, 1, 0)

        # 第2行第2列：参数标定
        self.btn_calibrate = QPushButton("参数标定")
        self.btn_calibrate.setObjectName("standardButton")
        self.btn_calibrate.clicked.connect(self.calibrate_clicked.emit)
        self.btn_calibrate.setEnabled(False)
        layout.addWidget(self.btn_calibrate, 1, 1)

        # 分析火焰按钮（暂时隐藏）
        self.btn_analyze = QPushButton("分析火焰")
        self.btn_analyze.setObjectName("warningButton")
        self.btn_analyze.clicked.connect(self.analyze_clicked.emit)
        self.btn_analyze.setEnabled(False)
        # layout.addWidget(self.btn_analyze) 暂时隐藏此按钮

        # 第3行：相机状态（跨2列）
        self.lbl_camera_status = QLabel("相机状态: 未初始化")
        layout.addWidget(self.lbl_camera_status, 2, 0, 1, 2)
    
    def update_camera_status(self, enabled: bool):
        """
        更新相机状态
        
        Args:
            enabled: 相机是否已就绪
        """
        status_text = "相机状态: " + ("已就绪" if enabled else "未找到相机")
        color = "#4caf50" if enabled else "#f44336"
        self.lbl_camera_status.setText(status_text)
        self.lbl_camera_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # 更新按钮状态
        self.btn_preview.setEnabled(enabled)
        self.btn_capture.setEnabled(enabled)
        self.btn_analyze.setEnabled(enabled)
        self.btn_calibrate.setEnabled(enabled)

