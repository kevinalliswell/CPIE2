#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制面板组件
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel, QCheckBox
from PySide6.QtCore import Signal
from models.experiment_states import ExplosionExperimentState


class ControlPanelWidget(QGroupBox):
    """实验控制面板组件"""
    
    # 信号定义
    connect_clicked = Signal()
    new_experiment_clicked = Signal()
    start_clicked = Signal()
    stop_clicked = Signal()
    
    def __init__(self, config, parent=None):
        """
        初始化控制面板
        
        Args:
            config: 配置字典
            parent: 父组件
        """
        super().__init__("实验控制", parent)
        self.config = config
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
        
        # 第2行第1列：启动实验按钮
        self.btn_start = QPushButton("启动实验")
        self.btn_start.setObjectName("successButton")
        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_start.setEnabled(False)
        layout.addWidget(self.btn_start, 1, 0)
        
        # 第2行第2列：停止/完成按钮（智能按钮，根据状态动态显示）
        self.btn_stop = QPushButton("停止实验")
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop, 1, 1)
        
        # 相机选项（隐藏）
        self.chk_camera = QCheckBox("启用相机")
        self.chk_camera.setChecked(self.config['camera']['enabled'])
        # layout.addWidget(self.chk_camera) 隐藏此按钮
        
        # 第4行：状态标签（跨2列）
        self.lbl_status = QLabel("状态: 未连接")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.lbl_status, 3, 0, 1, 2)
        
        # 第5行：检测标准标签（跨2列）
        lbl_standard = QLabel("检测标准: GB/T AQ/T 1045-2010《煤尘爆炸性鉴定规范》")
        lbl_standard.setStyleSheet("font-size: 9pt; color: #666666; padding: 5px 0px;")
        lbl_standard.setWordWrap(True)
        layout.addWidget(lbl_standard, 4, 0, 1, 2)
    
    def update_button_states(self, state: ExplosionExperimentState, is_running: bool):
        """
        更新按钮状态
        
        Args:
            state: 实验状态枚举
            is_running: 是否正在运行
        """
        # 连接按钮
        self.btn_connect.setEnabled(state == ExplosionExperimentState.IDLE)
        
        # 新建实验
        self.btn_new_experiment.setEnabled(state.can_create_experiment())
        
        # 启动实验
        self.btn_start.setEnabled(state.can_start())
        
        # 停止/完成按钮
        can_stop = state.can_stop()
        can_finalize = state.can_finalize()
        self.btn_stop.setEnabled(can_stop or can_finalize)
        
        # 根据状态动态更新按钮文本和样式
        if state == ExplosionExperimentState.SEQUENCE_RUNNING:
            self.btn_stop.setText("停止实验")
            self.btn_stop.setObjectName("dangerButton")
        elif state == ExplosionExperimentState.WAITING_ANALYSIS:
            if is_running:
                self.btn_stop.setText("停止实验")
                self.btn_stop.setObjectName("dangerButton")
            else:
                self.btn_stop.setText("完成实验")
                self.btn_stop.setObjectName("warningButton")
        elif state == ExplosionExperimentState.SESSION_CREATED:
            self.btn_stop.setText("完成实验")
            self.btn_stop.setObjectName("warningButton")
        else:
            self.btn_stop.setText("停止实验")
            self.btn_stop.setObjectName("dangerButton")
        
        # 应用样式（需要重新设置样式表才能生效）
        self.btn_stop.style().unpolish(self.btn_stop)
        self.btn_stop.style().polish(self.btn_stop)
    
    def update_status_display(self, text: str, color: str):
        """
        更新状态显示
        
        Args:
            text: 状态文本
            color: 颜色代码
        """
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(
            f"font-weight: bold; font-size: 12pt; color: {color};"
        )
    
    def set_connect_button_text(self, text: str):
        """设置连接按钮文本"""
        self.btn_connect.setText(text)
    
    def set_connect_button_enabled(self, enabled: bool):
        """设置连接按钮是否可用"""
        self.btn_connect.setEnabled(enabled)

