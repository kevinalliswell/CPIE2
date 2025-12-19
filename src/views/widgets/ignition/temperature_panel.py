#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温度显示面板组件（着火点实验）
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QLabel, QVBoxLayout


class TemperaturePanelWidget(QGroupBox):
    """温度显示面板组件"""
    
    def __init__(self, parent=None):
        """
        初始化温度显示面板
        
        Args:
            parent: 父组件
        """
        super().__init__("样品温度", parent)
        self.temp_labels = []
        self.ignition_labels = []
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        
        for i in range(6):
            row = i // 3
            col = i % 3
            
            # 通道布局
            ch_layout = QVBoxLayout()
            
            ch_label = QLabel(f"样品{i+1}")
            ch_label.setStyleSheet("font-weight: bold;")
            ch_layout.addWidget(ch_label)
            
            # 温度值
            temp_label = QLabel("--°C")
            temp_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a9eff;")
            ch_layout.addWidget(temp_label)
            self.temp_labels.append(temp_label)
            
            # 着火点标签
            ign_label = QLabel("等待检测")
            ign_label.setStyleSheet("font-size: 10pt; color: #999999;")
            ch_layout.addWidget(ign_label)
            self.ignition_labels.append(ign_label)
            
            layout.addLayout(ch_layout, row, col)
    
    def update_temperature(self, channel: int, temperature: float):
        """
        更新指定通道的温度显示
        
        Args:
            channel: 通道索引(0-5)
            temperature: 温度值
        """
        if 0 <= channel < 6:
            if temperature is not None:
                self.temp_labels[channel].setText(f"{temperature:.1f}°C")
            else:
                self.temp_labels[channel].setText("--°C")
    
    def update_all_temperatures(self, temperatures: list):
        """
        批量更新所有通道的温度显示
        
        Args:
            temperatures: 温度列表（6个元素）
        """
        for i, temp in enumerate(temperatures[:6]):
            self.update_temperature(i, temp)
    
    def mark_ignition(self, channel: int, temperature: float, method: str):
        """
        标记着火点
        
        Args:
            channel: 通道索引(0-5)
            temperature: 着火温度
            method: 检测方法
        """
        if 0 <= channel < 6:
            # 更新着火标签
            self.ignition_labels[channel].setText(f"着火点: {temperature:.1f}°C ({method})")
            self.ignition_labels[channel].setStyleSheet(
                "font-size: 10pt; font-weight: bold; color: #f44336;"
            )
            
            # 更新温度标签颜色为红色
            self.temp_labels[channel].setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: #f44336;"
            )
    
    def reset_ignition_status(self, channel: int = None):
        """
        重置着火点状态
        
        Args:
            channel: 通道索引(0-5)，None表示重置所有通道
        """
        if channel is None:
            # 重置所有通道
            for i in range(6):
                self.ignition_labels[i].setText("等待检测")
                self.ignition_labels[i].setStyleSheet("font-size: 10pt; color: #999999;")
                self.temp_labels[i].setStyleSheet(
                    "font-size: 16pt; font-weight: bold; color: #4a9eff;"
                )
        elif 0 <= channel < 6:
            # 重置指定通道
            self.ignition_labels[channel].setText("等待检测")
            self.ignition_labels[channel].setStyleSheet("font-size: 10pt; color: #999999;")
            self.temp_labels[channel].setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: #4a9eff;"
            )

