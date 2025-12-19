#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验记录面板组件
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt


class RecordsPanelWidget(QGroupBox):
    """实验记录面板组件"""
    
    def __init__(self, max_rounds: int = 10, parent=None):
        """
        初始化记录面板
        
        Args:
            max_rounds: 最大轮次数
            parent: 父组件
        """
        super().__init__("实验记录", parent)
        self.max_rounds = max_rounds
        self.record_labels = []
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 表格区域（使用GridLayout）
        table_layout = QGridLayout()
        
        # 表头
        headers = ["轮次", "火焰长度(mm)", "状态"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setStyleSheet(
                "font-weight: bold; padding: 5px; "
                "background-color: #3c3c3c; color: #ffffff;"
            )
            header_label.setAlignment(Qt.AlignCenter)
            table_layout.addWidget(header_label, 0, col)
        
        # 数据行
        max_rows = self.max_rounds + 1
        for row in range(1, max_rows):
            row_labels = []
            for col in range(3):
                cell_label = QLabel("--")
                cell_label.setStyleSheet(
                    "padding: 5px; background-color: #2b2b2b; "
                    "border: 1px solid #3c3c3c;"
                )
                cell_label.setAlignment(Qt.AlignCenter)
                table_layout.addWidget(cell_label, row, col)
                row_labels.append(cell_label)
            self.record_labels.append(row_labels)
        
        layout.addLayout(table_layout)
        
        # 统计信息区域
        stats_layout = QGridLayout()
        
        # 平均值
        stats_layout.addWidget(QLabel("平均火焰长度:"), 0, 0)
        self.lbl_avg_flame = QLabel("--")
        self.lbl_avg_flame.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #4a9eff;"
        )
        stats_layout.addWidget(self.lbl_avg_flame, 0, 1)
        
        # 当前进度
        stats_layout.addWidget(QLabel("当前进度:"), 1, 0)
        self.lbl_progress = QLabel("未开始")
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #999999;")
        stats_layout.addWidget(self.lbl_progress, 1, 1)
        
        # 实验结论
        stats_layout.addWidget(QLabel("实验结论:"), 2, 0)
        self.lbl_conclusion = QLabel("--")
        self.lbl_conclusion.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #999999;"
        )
        stats_layout.addWidget(self.lbl_conclusion, 2, 1)
        
        layout.addLayout(stats_layout)
        layout.addStretch()
    
    def update_records(self, round_records: list, evaluate_func):
        """
        更新实验记录显示
        
        Args:
            round_records: 轮次记录列表 [{'round': 1, 'flame_length': 150.5, 'image_path': '...'}, ...]
            evaluate_func: 评估爆炸性等级的函数 func(flame_length) -> (level_text, level_color)
        """
        # 更新表格数据
        for i, record in enumerate(round_records):
            if i < len(self.record_labels):
                row_labels = self.record_labels[i]
                
                # 轮次
                row_labels[0].setText(str(record['round']))
                
                # 火焰长度
                flame_length = record['flame_length']
                row_labels[1].setText(f"{flame_length:.1f}")
                
                # 状态（根据火焰长度显示颜色）
                level_text, level_color = evaluate_func(flame_length)
                row_labels[2].setText(level_text)
                row_labels[2].setStyleSheet(
                    f"padding: 5px; background-color: {level_color}; "
                    f"color: white; border: 1px solid #3c3c3c; font-weight: bold;"
                )
        
        # 清空未使用的行
        for i in range(len(round_records), len(self.record_labels)):
            for label in self.record_labels[i]:
                label.setText("--")
                label.setStyleSheet(
                    "padding: 5px; background-color: #2b2b2b; "
                    "border: 1px solid #3c3c3c;"
                )
        
        # 更新平均值
        if round_records:
            avg_length = sum(r['flame_length'] for r in round_records) / len(round_records)
            self.lbl_avg_flame.setText(f"{avg_length:.1f} mm")
        else:
            self.lbl_avg_flame.setText("--")
    
    def update_progress(self, progress_text: str, color: str):
        """
        更新进度显示
        
        Args:
            progress_text: 进度文本
            color: 颜色代码
        """
        self.lbl_progress.setText(progress_text)
        self.lbl_progress.setStyleSheet(f"font-weight: bold; color: {color};")
    
    def update_conclusion(self, conclusion_text: str, color: str):
        """
        更新实验结论显示
        
        Args:
            conclusion_text: 结论文本
            color: 颜色代码
        """
        self.lbl_conclusion.setText(conclusion_text)
        self.lbl_conclusion.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {color};"
        )

