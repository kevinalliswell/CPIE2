#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验模式切换对话框
用于选择预设模式或自定义温控曲线
"""

import copy
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QRadioButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator

from utils.path_manager import PathManager


class ModeSwitchDialog(QDialog):
    """实验模式切换对话框"""
    
    # 信号：确认时发出 (模式名称, 程序段列表)
    confirmed = Signal(str, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presets = []
        self.current_segments = []
        self.current_mode_name = "自定义模式"
        
        self.setup_ui()
        self.load_presets()
        self.apply_styles()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("实验模式切换")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("选择实验模式")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title_label)
        
        # 模式选择区域
        mode_group = QGroupBox("预设模式")
        mode_layout = QVBoxLayout(mode_group)
        
        # 创建按钮组管理单选按钮
        self.mode_button_group = QButtonGroup(self)
        
        # 预设模式单选按钮（稍后动态添加）
        self.preset_radios = []
        self.preset_descriptions = []
        
        mode_layout.addStretch()
        main_layout.addWidget(mode_group)
        self.mode_group_layout = mode_layout
        
        # 温控曲线参数表格
        table_group = QGroupBox("温控曲线参数")
        table_layout = QVBoxLayout(table_group)
        
        # 说明文字
        info_label = QLabel("程序段格式：[温度(℃), 时间(分钟)]，负时间值表示特殊控制（-121表示停止运行）")
        info_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        info_label.setWordWrap(True)
        table_layout.addWidget(info_label)
        
        # 创建表格
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(3)
        self.segments_table.setHorizontalHeaderLabels(["程序段号", "目标温度(℃)", "时间(分钟)"])
        self.segments_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.segments_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.segments_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.segments_table.setMinimumHeight(200)
        self.segments_table.itemChanged.connect(self._on_table_item_changed)
        table_layout.addWidget(self.segments_table)
        
        # 表格操作按钮
        table_btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("添加程序段")
        btn_add.clicked.connect(self._add_segment)
        table_btn_layout.addWidget(btn_add)
        
        btn_delete = QPushButton("删除选中")
        btn_delete.clicked.connect(self._delete_segment)
        table_btn_layout.addWidget(btn_delete)
        
        table_btn_layout.addStretch()
        table_layout.addLayout(table_btn_layout)
        
        main_layout.addWidget(table_group)
        
        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        self._style_button(cancel_btn, "#6c757d")
        
        confirm_btn = QPushButton("确认应用")
        confirm_btn.clicked.connect(self.on_confirm)
        self._style_button(confirm_btn, "#28a745")
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        main_layout.addLayout(button_layout)
    
    def load_presets(self):
        """从配置文件加载预设模式"""
        try:
            preset_path = PathManager.get_config_path("presets.json")
            with open(preset_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.presets = config.get('presets', [])
            
            # 清空现有单选按钮
            for radio in self.preset_radios:
                radio.deleteLater()
            for desc in self.preset_descriptions:
                desc.deleteLater()
            self.preset_radios.clear()
            self.preset_descriptions.clear()
            
            # 动态创建预设模式单选按钮
            for i, preset in enumerate(self.presets):
                radio = QRadioButton(preset['name'])
                radio.toggled.connect(lambda checked, p=preset: self._on_preset_selected(checked, p))
                self.mode_button_group.addButton(radio, i)
                self.preset_radios.append(radio)
                self.mode_group_layout.insertWidget(i * 2, radio)
                
                # 描述标签
                desc = QLabel(f"  {preset['description']}")
                desc.setStyleSheet("font-size: 11px; color: #aaaaaa; padding-left: 25px;")
                desc.setWordWrap(True)
                self.preset_descriptions.append(desc)
                self.mode_group_layout.insertWidget(i * 2 + 1, desc)
            
            # 添加自定义模式选项
            custom_radio = QRadioButton("自定义模式")
            custom_radio.toggled.connect(lambda checked: self._on_custom_selected(checked))
            self.mode_button_group.addButton(custom_radio, len(self.presets))
            self.preset_radios.append(custom_radio)
            self.mode_group_layout.insertWidget(len(self.presets) * 2, custom_radio)
            
            custom_desc = QLabel("  完全自定义温控曲线参数")
            custom_desc.setStyleSheet("font-size: 11px; color: #aaaaaa; padding-left: 25px;")
            self.preset_descriptions.append(custom_desc)
            self.mode_group_layout.insertWidget(len(self.presets) * 2 + 1, custom_desc)
            
            # 默认选择第一个预设
            if self.presets:
                self.preset_radios[0].setChecked(True)
            
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"无法加载预设配置：{e}")
    
    def _on_preset_selected(self, checked, preset):
        """预设模式被选中"""
        if checked:
            self.current_mode_name = preset['name']
            # 深拷贝：表格编辑会原地修改内层 [温度, 时间] 列表，浅拷贝会污染预设本身
            self.current_segments = copy.deepcopy(preset['segments'])
            self._update_table()
    
    def _on_custom_selected(self, checked):
        """自定义模式被选中"""
        if checked:
            self.current_mode_name = "自定义模式"
            # 保持当前表格中的数据
    
    def _update_table(self):
        """更新表格显示"""
        self.segments_table.blockSignals(True)  # 阻止信号避免循环触发
        
        self.segments_table.setRowCount(len(self.current_segments))
        
        for i, (temp, time) in enumerate(self.current_segments):
            # 程序段号
            item_num = QTableWidgetItem(str(i + 1))
            item_num.setTextAlignment(Qt.AlignCenter)
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)  # 只读
            self.segments_table.setItem(i, 0, item_num)
            
            # 温度
            item_temp = QTableWidgetItem(str(temp))
            item_temp.setTextAlignment(Qt.AlignCenter)
            self.segments_table.setItem(i, 1, item_temp)
            
            # 时间
            item_time = QTableWidgetItem(str(time))
            item_time.setTextAlignment(Qt.AlignCenter)
            self.segments_table.setItem(i, 2, item_time)
        
        self.segments_table.blockSignals(False)
    
    def _on_table_item_changed(self, item):
        """表格内容改变"""
        if item.column() == 0:  # 程序段号不可编辑
            return
        
        row = item.row()
        col = item.column()
        try:
            value = float(item.text())

            if col == 1:  # 温度
                self.current_segments[row][0] = value
            elif col == 2:  # 时间
                self.current_segments[row][1] = int(value)

            # 如果修改了表格，自动切换到自定义模式
            if self.preset_radios:
                self.preset_radios[-1].setChecked(True)

        except (ValueError, IndexError):
            # 非法输入：把单元格恢复为当前有效值，避免表格显示与实际数据不一致
            try:
                old_value = self.current_segments[row][0 if col == 1 else 1]
                self.segments_table.blockSignals(True)
                item.setText(str(old_value))
            except IndexError:
                pass
            finally:
                self.segments_table.blockSignals(False)
    
    def _add_segment(self):
        """添加新程序段"""
        self.current_segments.append([100, 10])  # 默认值：100℃, 10分钟
        self._update_table()
        
        # 切换到自定义模式
        if self.preset_radios:
            self.preset_radios[-1].setChecked(True)
    
    def _delete_segment(self):
        """删除选中的程序段"""
        selected_rows = set()
        for item in self.segments_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的程序段")
            return
        
        # 从后往前删除，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.current_segments):
                del self.current_segments[row]
        
        self._update_table()
        
        # 切换到自定义模式
        if self.preset_radios:
            self.preset_radios[-1].setChecked(True)
    
    def on_confirm(self):
        """确认按钮点击"""
        # 验证数据
        if not self.current_segments:
            QMessageBox.warning(self, "验证失败", "至少需要一个程序段！")
            return
        
        # 验证温度和时间范围
        for i, (temp, time) in enumerate(self.current_segments):
            if temp < -200 or temp > 2000:
                QMessageBox.warning(self, "验证失败", 
                    f"程序段{i+1}温度超出范围（-200~2000℃）")
                return
            
            if time < -32768 or time > 32767:
                QMessageBox.warning(self, "验证失败", 
                    f"程序段{i+1}时间超出范围（-32768~32767分钟）")
                return
        
        # 发送信号
        self.confirmed.emit(self.current_mode_name, self.current_segments)
        self.accept()
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #16213e,
                    stop: 1 #0f3460
                );
            }
            
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                font-size: 14px;
                color: #ffffff;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #00d9ff;
            }
            
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
                spacing: 8px;
            }
            
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            
            QRadioButton::indicator:unchecked {
                border: 2px solid #888;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
            }
            
            QRadioButton::indicator:checked {
                border: 2px solid #00d9ff;
                border-radius: 8px;
                background: #00d9ff;
            }
            
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                color: #ffffff;
                gridline-color: rgba(255, 255, 255, 0.1);
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QTableWidget::item:selected {
                background-color: rgba(0, 217, 255, 0.3);
            }
            
            QHeaderView::section {
                background-color: rgba(0, 217, 255, 0.2);
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
    
    def _style_button(self, button, color):
        """设置按钮样式"""
        button.setMinimumHeight(36)
        button.setMinimumWidth(100)
        button.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 25px;
            }}
            QPushButton:hover {{
                background: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background: {self._darken_color(color, 0.8)};
            }}
        """)
    
    def _darken_color(self, color, factor=0.85):
        """使颜色变暗"""
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

