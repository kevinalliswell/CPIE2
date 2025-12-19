"""
紧凑型日志组件
适用于触摸屏显示，只显示最新的几条日志
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PySide6.QtCore import Qt
from datetime import datetime
from collections import deque


class CompactLogWidget(QFrame):
    """
    紧凑型日志组件
    只显示最新的N条日志（默认5条）
    """
    
    def __init__(self, max_logs: int = 5, parent=None):
        super().__init__(parent)
        
        self.setObjectName("compactLogWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)  # 使用deque自动限制长度
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 标题（放大字体）
        title_label = QLabel("📋 实验日志")
        title_label.setObjectName("compactLogTitle")
        title_label.setStyleSheet("font-weight: bold; color: #34495e; font-size: 20px;")
        main_layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # 日志容器
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_layout.setSpacing(3)
        self.log_layout.addStretch()  # 让日志从上往下显示
        
        scroll_area.setWidget(self.log_container)
        main_layout.addWidget(scroll_area)
    
    def add_log(self, message: str, log_type: str = "info"):
        """
        添加日志
        Args:
            message: 日志消息
            log_type: 日志类型 (info, warning, error, success)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 日志图标
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        icon = icons.get(log_type, "ℹ️")
        
        # 日志颜色
        colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "success": "#27ae60"
        }
        color = colors.get(log_type, "#3498db")
        
        # 创建日志项（放大字体）
        log_text = f"{icon} [{timestamp}] {message}"
        log_label = QLabel(log_text)
        log_label.setObjectName("compactLogItem")
        log_label.setWordWrap(True)
        log_label.setStyleSheet(f"color: {color}; padding: 5px; font-size: 16px;")
        
        # 添加到布局（插入到stretch之前）
        insert_index = self.log_layout.count() - 1
        self.log_layout.insertWidget(insert_index, log_label)
        
        # 保存日志引用
        self.logs.append(log_label)
        
        # 如果超过最大数量，删除最旧的
        if self.log_layout.count() - 1 > self.max_logs:  # -1是因为有stretch
            oldest_item = self.log_layout.itemAt(0)
            if oldest_item and oldest_item.widget():
                widget = oldest_item.widget()
                self.log_layout.removeWidget(widget)
                widget.deleteLater()
    
    def clear_logs(self):
        """清空所有日志"""
        # 删除所有日志widget
        while self.log_layout.count() > 1:  # 保留最后的stretch
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.logs.clear()
    
    def info(self, message: str):
        """添加信息日志"""
        self.add_log(message, "info")
    
    def warning(self, message: str):
        """添加警告日志"""
        self.add_log(message, "warning")
    
    def error(self, message: str):
        """添加错误日志"""
        self.add_log(message, "error")
    
    def success(self, message: str):
        """添加成功日志"""
        self.add_log(message, "success")

