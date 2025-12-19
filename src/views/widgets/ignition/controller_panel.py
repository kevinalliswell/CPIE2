#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温控仪表面板组件（着火点实验）
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal


class ControllerPanelWidget(QGroupBox):
    """温控仪表面板组件"""
    
    # 信号定义
    mode_switch_clicked = Signal()
    controller_run_clicked = Signal()
    controller_stop_clicked = Signal()
    
    def __init__(self, parent=None):
        """
        初始化温控仪表面板
        
        Args:
            parent: 父组件
        """
        super().__init__("温控仪表", parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        
        # 当前模式标签
        mode_label = QLabel("当前模式:")
        mode_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(mode_label, 0, 0)
        
        self.lbl_current_mode = QLabel("未设置")
        self.lbl_current_mode.setStyleSheet("font-size: 11pt; color: #999999;")
        layout.addWidget(self.lbl_current_mode, 0, 1, 1, 2)
        
        # 参数列表：PV, SV, MV
        params = [
            ("PV (测量值)", "lbl_pv", "°C", 18),
            ("SV (给定值)", "lbl_sv", "°C", 14),
            ("MV (输出值)", "lbl_mv", "%", 14)
        ]
        
        for i, (label_text, attr_name, unit, font_size) in enumerate(params):
            row = (i // 3) + 1  # 从第二行开始
            col = i % 3
            
            # 参数布局
            param_layout = QVBoxLayout()
            
            # 参数标签
            param_label = QLabel(label_text)
            param_label.setStyleSheet("font-weight: bold;")
            param_layout.addWidget(param_label)
            
            # 参数值（单位直接显示在后面）
            value_label = QLabel(f"-- {unit}")
            # 根据参数类型设置颜色
            if attr_name == "lbl_pv":
                color = "#ff4444"  # 亮红色
            elif attr_name == "lbl_sv":
                color = "#44ff44"  # 亮绿色
            else:
                color = "#4a9eff"  # 默认蓝色
            value_label.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold; color: {color};")
            param_layout.addWidget(value_label)
            
            # 保存标签引用
            setattr(self, attr_name, value_label)
            
            layout.addLayout(param_layout, row, col)
        
        # 模式切换按钮
        mode_btn_layout = QHBoxLayout()
        self.btn_mode_switch = QPushButton("模式切换")
        self.btn_mode_switch.setObjectName("standardButton")
        self.btn_mode_switch.clicked.connect(self.mode_switch_clicked.emit)
        self.btn_mode_switch.setEnabled(False)  # 默认禁用，连接设备后启用
        mode_btn_layout.addWidget(self.btn_mode_switch)
        # mode_btn_layout.addStretch()
        layout.addLayout(mode_btn_layout, 2, 0, 1, 3)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.btn_controller_run = QPushButton("运行")
        self.btn_controller_run.setObjectName("successButton")
        self.btn_controller_run.clicked.connect(self.controller_run_clicked.emit)
        self.btn_controller_run.setEnabled(False)  # 默认禁用
        btn_layout.addWidget(self.btn_controller_run)
        
        self.btn_controller_stop = QPushButton("停止")
        self.btn_controller_stop.setObjectName("dangerButton")
        self.btn_controller_stop.clicked.connect(self.controller_stop_clicked.emit)
        self.btn_controller_stop.setEnabled(False)  # 默认禁用
        btn_layout.addWidget(self.btn_controller_stop)
        layout.addLayout(btn_layout, 3, 0, 1, 3)
        
        layout.setRowStretch(4, 1)
    
    def update_controller_data(self, pv, sv, mv):
        """
        更新温控仪表数据
        
        Args:
            pv: 测量值
            sv: 给定值
            mv: 输出值
        """
        self.lbl_pv.setText(f"{pv:.1f} °C" if pv is not None else "-- °C")
        self.lbl_sv.setText(f"{sv:.1f} °C" if sv is not None else "-- °C")
        self.lbl_mv.setText(f"{mv:.1f} %" if mv is not None else "-- %")
    
    def update_mode_display(self, mode_name: str):
        """
        更新模式显示
        
        Args:
            mode_name: 模式名称
        """
        self.lbl_current_mode.setText(mode_name)
        self.lbl_current_mode.setStyleSheet("font-size: 11pt; color: #00d9ff; font-weight: bold;")
    
    def set_buttons_enabled(self, enabled: bool):
        """设置按钮是否可用"""
        self.btn_controller_run.setEnabled(enabled)
        self.btn_controller_stop.setEnabled(enabled)
    
    def set_mode_switch_enabled(self, enabled: bool):
        """设置模式切换按钮是否可用"""
        self.btn_mode_switch.setEnabled(enabled)

