"""
实验详情卡片基类
提供公共的UI组件和方法
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal


class BaseDetailCard(QWidget):
    """
    实验详情卡片基类
    提供通用的UI框架和公共方法
    """
    
    # 信号
    refresh_requested = Signal()  # 请求刷新详情
    generate_report_requested = Signal()  # 请求生成报告
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.experiment_data = None
        
        # 初始化UI
        self.setup_ui()
    
    def setup_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.2);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 217, 255, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 217, 255, 0.5);
            }
        """)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        
        # 空状态提示
        self.empty_label = QLabel("请从左侧列表选择一个实验查看详情")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 13px;
                padding: 60px 20px;
            }
        """)
        self.content_layout.addWidget(self.empty_label)
        self.content_layout.addStretch()
        
        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area)
        
        # 底部按钮区域
        self.button_widget = self.create_button_area()
        self.button_widget.setVisible(False)  # 初始隐藏
        main_layout.addWidget(self.button_widget)
    
    # ==================== 公共方法 ====================
    
    def create_button_area(self) -> QWidget:
        """创建底部按钮区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border-top: 1px solid rgba(0, 217, 255, 0.2);
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 生成报告按钮
        self.report_btn = QPushButton("📄 生成报告")
        self.report_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #000;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00e8ff,
                    stop: 1 #00a8d0
                );
            }
        """)
        self.report_btn.clicked.connect(self.generate_report_requested.emit)
        
        layout.addStretch()
        layout.addWidget(self.report_btn)
        layout.addStretch()
        
        return widget
    
    def clear_content(self):
        """清空内容"""
        # 删除所有widget（除了empty_label）
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()
        
        # 隐藏空状态
        self.empty_label.setVisible(False)
    
    def show_empty_state(self, message: str = "请从左侧列表选择一个实验查看详情"):
        """显示空状态"""
        self.clear_content()
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.content_layout.addWidget(self.empty_label)
        self.content_layout.addStretch()
        
        # 隐藏按钮区域
        self.button_widget.setVisible(False)
    
    # ==================== UI组件创建（公共方法） ====================
    
    def create_title_section(self, code: str, type_label: str) -> QWidget:
        """创建标题区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(0, 217, 255, 0.2),
                    stop: 1 rgba(0, 217, 255, 0.05)
                );
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 实验编号
        code_label = QLabel(code)
        code_label.setStyleSheet("color: #00d9ff; font-size: 12px; ")
        
        # 实验类型
        type_label_widget = QLabel(type_label)
        type_label_widget.setStyleSheet("color: #aaa; font-size: 12px;")

        layout.addWidget(type_label_widget)
        layout.addWidget(code_label)

        
        return widget
    
    def create_info_section(self, title: str, items: list) -> QWidget:
        """
        创建信息区域
        Args:
            title: 标题
            items: 信息项列表 [(标签, 值, 颜色), ...]
        """
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #00d9ff; font-size: 11px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: rgba(255, 255, 255, 0.1); max-height: 1px;")
        layout.addWidget(separator)
        
        # 信息项
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        
        for i, (label, value, color) in enumerate(items):
            row = i // 2
            col = (i % 2) * 2
            
            # 标签
            label_widget = QLabel(f"{label}:")
            label_widget.setStyleSheet("color: #888; font-size: 10px;")
            label_widget.setFixedWidth(70)
            grid_layout.addWidget(label_widget, row, col)
            
            # 值
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
            grid_layout.addWidget(value_widget, row, col + 1)
        
        layout.addLayout(grid_layout)
        
        return widget
    
    def create_note_section(self, note: str) -> QWidget:
        """创建备注区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 165, 0, 0.1);
                border-left: 3px solid #ff9800;
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("📝 备注")
        title_label.setStyleSheet("color: #ff9800; font-size: 10px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 备注内容
        note_label = QLabel(note)
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #ddd; font-size: 10px; line-height: 1.4;")
        layout.addWidget(note_label)
        
        return widget
    
    def create_description_section(self, title: str, text: str) -> QWidget:
        """创建描述文本区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 217, 255, 0.05);
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #00d9ff; font-size: 10px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 内容
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: #ccc; font-size: 10px; line-height: 1.4;")
        layout.addWidget(text_label)
        
        return widget

