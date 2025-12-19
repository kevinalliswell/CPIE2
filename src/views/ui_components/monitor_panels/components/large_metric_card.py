"""
大尺寸指标卡片
适用于触摸屏显示，字体大、清晰
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class LargeMetricCard(QFrame):
    """
    大尺寸指标卡片
    专为触摸屏设计，字体大、易读
    """
    
    def __init__(self, title: str, value: str = "--", unit: str = "", 
                 icon: str = "📊", hint: str = "", parent=None):
        super().__init__(parent)
        
        self.setObjectName("largeMetricCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("largeMetricIcon")
        self.icon_label.setStyleSheet("font-size: 32px;")
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("largeMetricTitle")
        self.title_label.setStyleSheet("font-weight: bold; color: #666; font-size: 22px;")
        
        title_layout.addWidget(self.icon_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 数值行
        value_layout = QHBoxLayout()
        value_layout.setSpacing(8)
        
        self.value_label = QLabel(value)
        self.value_label.setObjectName("largeMetricValue")
        self.value_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 48px;")
        
        self.unit_label = QLabel(unit)
        self.unit_label.setObjectName("largeMetricUnit")
        self.unit_label.setStyleSheet("color: #7f8c8d; font-size: 22px;")
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        value_layout.addWidget(self.value_label)
        if unit:
            value_layout.addWidget(self.unit_label)
        value_layout.addStretch()
        
        layout.addLayout(value_layout)
        
        # 提示行
        if hint:
            self.hint_label = QLabel(hint)
            self.hint_label.setObjectName("largeMetricHint")
            self.hint_label.setStyleSheet("color: #95a5a6; font-size: 16px;")
            layout.addWidget(self.hint_label)
        else:
            self.hint_label = None
    
    def set_value(self, value, unit: str = None):
        """
        更新数值
        Args:
            value: 数值（可以是数字或字符串）
            unit: 可选的单位更新
        """
        if value is None:
            self.value_label.setText("--")
        elif isinstance(value, (int, float)):
            self.value_label.setText(f"{value:.1f}")
        else:
            self.value_label.setText(str(value))
        
        if unit is not None:
            self.unit_label.setText(unit)
    
    def set_status(self, status: str):
        """
        设置状态（改变颜色）
        Args:
            status: normal, warning, danger
        """
        if status == "warning":
            self.value_label.setStyleSheet("font-weight: bold; color: #f39c12;")
        elif status == "danger":
            self.value_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        else:
            self.value_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
    
    def set_hint(self, hint: str):
        """更新提示文本"""
        if self.hint_label:
            self.hint_label.setText(hint)

