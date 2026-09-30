#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制面板组件（着火点实验）
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Signal
from models.experiment_states import IgnitionExperimentState


class ControlPanelWidget(QGroupBox):
    """实验控制面板组件"""
    
    # 信号定义
    connect_clicked = Signal()
    new_experiment_clicked = Signal()
    start_stop_clicked = Signal()
    finalize_clicked = Signal()
    
    def __init__(self, parent=None):
        """
        初始化控制面板
        
        Args:
            parent: 父组件
        """
        super().__init__("实验控制", parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        
        # 第1行第1列：连接按钮
        self.btn_connect = QPushButton("连接设备")
        self.btn_connect.setObjectName("primaryButton")
        self.btn_connect.clicked.connect(self.connect_clicked.emit)
        layout.addWidget(self.btn_connect, 0, 0)
        
        # 第1行第2列：新建实验按钮
        self.btn_new_experiment = QPushButton("新建实验")
        self.btn_new_experiment.setObjectName("primaryButton")
        self.btn_new_experiment.clicked.connect(self.new_experiment_clicked.emit)
        self.btn_new_experiment.setEnabled(False)
        layout.addWidget(self.btn_new_experiment, 0, 1)
        
        # 第2行第1列：启动/停止实验（智能按钮）
        self.btn_start = QPushButton("启动实验")
        self.btn_start.setObjectName("successButton")
        self.btn_start.clicked.connect(self.start_stop_clicked.emit)
        self.btn_start.setEnabled(False)
        layout.addWidget(self.btn_start, 1, 0)
        
        # 第2行第2列：完成实验（独立按钮）
        self.btn_finalize = QPushButton("完成实验")
        self.btn_finalize.setObjectName("warningButton")
        self.btn_finalize.clicked.connect(self.finalize_clicked.emit)
        self.btn_finalize.setEnabled(False)
        layout.addWidget(self.btn_finalize, 1, 1)
        
        # 第3行：状态标签（跨2列）
        self.lbl_status = QLabel("状态: 未连接")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.lbl_status, 2, 0, 1, 2)
        
        # 第4行：检测标准标签（跨2列）
        lbl_standard = QLabel("检测标准: GB/T 18511-2017《煤的着火温度测定方法》")
        lbl_standard.setStyleSheet("font-size: 9pt; color: #666666; padding: 5px 0px;")
        lbl_standard.setWordWrap(True)
        layout.addWidget(lbl_standard, 4, 0, 1, 2)
    
    def update_button_states(self, state: IgnitionExperimentState):
        """
        更新按钮状态
        
        Args:
            state: 实验状态枚举
        """
        # 连接按钮
        self.btn_connect.setEnabled(state == IgnitionExperimentState.IDLE)
        
        # 新建实验按钮
        self.btn_new_experiment.setEnabled(state.can_create_experiment())
        
        # 启动/停止按钮（智能按钮）
        if state == IgnitionExperimentState.PREPARED:
            self.btn_start.setEnabled(True)
            self.btn_start.setText("启动实验")
            self.btn_start.setObjectName("successButton")
        elif state == IgnitionExperimentState.RUNNING:
            self.btn_start.setEnabled(True)
            self.btn_start.setText("停止实验")
            self.btn_start.setObjectName("dangerButton")
        else:
            self.btn_start.setEnabled(False)
            self.btn_start.setText("启动实验")
            self.btn_start.setObjectName("successButton")
        
        # 完成实验按钮
        self.btn_finalize.setEnabled(state.can_finalize())
        self.btn_finalize.setText("结束异常实验" if state == IgnitionExperimentState.ERROR else "完成实验")
        
        # 应用样式（需要重新设置样式表才能生效）
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)
        self.btn_finalize.style().unpolish(self.btn_finalize)
        self.btn_finalize.style().polish(self.btn_finalize)
    
    def update_status_display(self, text: str, style: str):
        """
        更新状态显示
        
        Args:
            text: 状态文本
            style: 样式字符串
        """
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(style)
    
    def set_connect_button_text(self, text: str):
        """设置连接按钮文本"""
        self.btn_connect.setText(text)
    
    def set_connect_button_enabled(self, enabled: bool):
        """设置连接按钮是否可用"""
        self.btn_connect.setEnabled(enabled)
