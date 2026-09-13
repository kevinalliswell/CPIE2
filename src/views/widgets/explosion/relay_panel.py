#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
继电器状态面板组件
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Signal


class RelayPanelWidget(QGroupBox):
    """继电器状态面板组件"""
    
    # 信号定义
    auto_clean_on_clicked = Signal()
    auto_clean_off_clicked = Signal()
    
    def __init__(self, config, parent=None):
        """
        初始化继电器面板
        
        Args:
            config: 配置字典
            parent: 父组件
        """
        super().__init__("继电器状态", parent)
        self.config = config
        self.relay_labels = {}
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        
        relay_mapping = self.config['relay_mapping']
        
        # 继电器名称中英文映射
        relay_name_map = {
            'spray_valve': '喷吹阀',
            'purge_valve': '吹扫阀',
            'vacuum_cleaner': '吸尘器',
            'reserved': '备用'
        }
        
        # 2x2布局：每个继电器占2列（名称+状态）
        index = 0
        for name, num in relay_mapping.items():
            row = index // 2  # 每2个继电器换一行
            col_offset = (index % 2) * 2  # 每个继电器占2列，所以偏移量是0或2
            
            # 继电器名称（使用中文）
            chinese_name = relay_name_map.get(name, name)
            layout.addWidget(QLabel(f"{chinese_name}"), row, col_offset)
            
            # 继电器状态
            status_label = QLabel("未知")
            status_label.setStyleSheet(
                "padding: 2px 6px; background-color: #666; color: white; "
                "border-radius: 3px; font-weight: bold; font-size: 8pt; min-height: 24px; max-height: 24px;"
            )
            layout.addWidget(status_label, row, col_offset + 1)
            
            self.relay_labels[num] = status_label
            index += 1
        
        # 添加自清洁按钮（第3行，跨2列）
        btn_row = 2
        self.btn_auto_clean_on = QPushButton("自清洁开")
        self.btn_auto_clean_on.setObjectName("standardButton")
        self.btn_auto_clean_on.clicked.connect(self.auto_clean_on_clicked.emit)
        self.btn_auto_clean_on.setEnabled(False)  # 初始状态禁用，等待设备连接
        layout.addWidget(self.btn_auto_clean_on, btn_row, 0, 1, 2)
        
        self.btn_auto_clean_off = QPushButton("自清洁关")
        self.btn_auto_clean_off.setObjectName("standardButton")
        self.btn_auto_clean_off.clicked.connect(self.auto_clean_off_clicked.emit)
        self.btn_auto_clean_off.setEnabled(False)  # 初始状态禁用，等待设备连接
        layout.addWidget(self.btn_auto_clean_off, btn_row, 2, 1, 2)
    
    def update_relay_status(self, relay_num: int, state: bool):
        """
        更新继电器状态显示
        
        Args:
            relay_num: 继电器编号
            state: 继电器状态（True=导通，False=关闭）
        """
        label = self.relay_labels.get(relay_num)
        if label:
            if not isinstance(state, bool):
                label.setText("未知")
                label.setStyleSheet("padding: 5px; background-color: #996600; color: white; border-radius: 3px;")
            elif state:
                label.setText("导通")
                label.setStyleSheet(
                    "padding: 5px; background-color: #4caf50; color: white; "
                    "border-radius: 3px; font-weight: bold;"
                )
            else:
                label.setText("关闭")
                label.setStyleSheet(
                    "padding: 5px; background-color: #666; color: white; "
                    "border-radius: 3px; font-weight: bold;"
                )
    
    def update_all_relay_status(self, relays: dict):
        """
        批量更新所有继电器状态
        
        Args:
            relays: 继电器状态字典 {relay_num: state}
        """
        for relay_name, relay_num in self.config['relay_mapping'].items():
            relay_key = f'relay_{relay_num}'
            self.update_relay_status(relay_num, relays.get(relay_key))
    
    def set_clean_buttons_enabled(self, enabled: bool):
        """
        设置自清洁按钮是否可用
        
        Args:
            enabled: 是否可用
        """
        self.btn_auto_clean_on.setEnabled(enabled)
        self.btn_auto_clean_off.setEnabled(enabled)
