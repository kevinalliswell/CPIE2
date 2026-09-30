"""
监控面板基类
所有监控面板的共同接口和功能
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal


class BaseMonitorPanel(QWidget):
    """
    监控面板基类
    定义所有监控面板的通用接口
    """
    
    # 信号
    error_occurred = Signal(str)  # 错误信号
    status_changed = Signal(str)  # 状态变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # 初始化UI
        self.setup_ui()
    
    def setup_ui(self):
        """初始化UI - 子类必须实现"""
        raise NotImplementedError("子类必须实现setup_ui方法")
    
    def connect_controller_signals(self, controller):
        """连接控制器信号 - 子类必须实现"""
        raise NotImplementedError("子类必须实现connect_controller_signals方法")
    
    def disconnect_controller_signals(self, controller):
        """断开控制器信号 - 子类可选实现"""
        pass
    
    def update_display(self):
        """更新显示 - 子类可选实现"""
        pass
    
    def reset(self):
        """重置面板 - 子类可选实现"""
        pass

