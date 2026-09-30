"""
爆炸性实验监控面板
显示温度、压力、火焰图像、实验进度等核心数据
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout
)
from PySide6.QtCore import QTimer
import math

from .base_monitor_panel import BaseMonitorPanel
from .components import LargeMetricCard, RelayStatusCard


def _valid_measurement(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class ExplosionMonitorPanel(BaseMonitorPanel):
    """
    爆炸性实验监控面板
    
    布局：
    - 左侧：实时数据卡片（温度、压力）
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 控制器和manager引用
        self.controller = None
        self.manager = None
        
        # 创建定时器（和主屏一样的方式）
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
    
    def setup_ui(self):
        """初始化UI"""
        # 只显示数据卡片
        widget = self._create_data_area()
        self.main_layout.addWidget(widget)
    
    def _create_data_area(self) -> QWidget:
        """创建数据区域（显示温度、压力和继电器状态）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 实时数据卡片（温度和压力）
        data_grid = QGridLayout()
        data_grid.setSpacing(10)
        
        # 温度卡片
        self.temp_card = LargeMetricCard(
            "点火器温度",
            "--",
            "°C",
            "🌡️",
            "实验温度条件: 1100±2°C"
        )
        
        # 压力卡片
        self.pressure_card = LargeMetricCard(
            "喷吹压力",
            "--",
            "kPa",
            "📊",
            "实验压力条件: 50±2kPa"
        )
        
        data_grid.addWidget(self.temp_card, 0, 0)
        data_grid.addWidget(self.pressure_card, 0, 1)
        
        layout.addLayout(data_grid)
        
        # 继电器状态卡片
        self.relay_card = RelayStatusCard()
        self._set_relay_states({})
        layout.addWidget(self.relay_card)
        
        layout.addStretch()
        
        return widget
    
    def connect_controller_signals(self, controller):
        """连接控制器（使用定时器轮询，和主屏一样的方式）"""
        if controller is None:
            return
        
        # 保存控制器和manager引用
        self.controller = controller
        if hasattr(controller, 'manager'):
            self.manager = controller.manager
        
        # 启动定时器轮询（和主屏一样的方式）
        # 默认更新间隔500ms，可以从ui_config获取
        update_interval = 500  # ms
        if hasattr(controller, 'config') and controller.config:
            ui_config = controller.config.get('ui_config', {})
            update_interval = ui_config.get('update_interval', 500)
        
        self.update_timer.start(update_interval)
        print(f"[爆炸性监控面板] 定时器轮询已启动，间隔: {update_interval}ms")
    
    def disconnect_controller_signals(self, controller):
        """断开控制器（停止定时器）"""
        # 停止定时器
        if self.update_timer:
            self.update_timer.stop()
            print("[爆炸性监控面板] 定时器已停止")
        
        # 清空引用
        self.controller = None
        self.manager = None
        self.reset()
    
    # ==================== 定时器轮询更新（和主屏一样的方式）====================
    
    def _update_display(self):
        """更新显示（和主屏一样的方式）"""
        # 动态获取manager引用（因为控制器可能在连接设备后才创建manager）
        if self.controller and hasattr(self.controller, 'manager'):
            self.manager = self.controller.manager
        
        if not self.manager:
            self.reset()
            return
        
        # 更新温控仪表数据
        self._update_controller_data()
        
        # 更新压力仪表数据
        self._update_pressure_data()
        
        # 更新继电器状态
        self._update_relay_status()
    
    def _update_controller_data(self):
        """更新温控仪表数据（和主屏一样的方式）"""
        data = self.manager.get_latest_data('爆炸性-温控仪表')
        pv = data.get('pv') if isinstance(data, dict) else None
        self.temp_card.set_value(pv if _valid_measurement(pv) else "--", "°C")
    
    def _update_pressure_data(self):
        """更新压力仪表数据（和主屏一样的方式）"""
        data = self.manager.get_latest_data('爆炸性-压力表')
        pressure = data.get('pressure') if isinstance(data, dict) else None
        self.pressure_card.set_value(pressure if _valid_measurement(pressure) else "--", "kPa")
    
    def _update_relay_status(self):
        """更新继电器状态（和主屏一样的方式）"""
        data = self.manager.get_latest_data('爆炸性-继电器')
        relays = data.get('relays') if isinstance(data, dict) else None
        if not isinstance(relays, dict):
            relays = {}
        self._set_relay_states({key: relays.get(f'relay_{key}')
                                for key in self.relay_card.relay_labels})

    def _set_relay_states(self, states):
        """缺失状态显示未知，只有明确的布尔读回值才能显示导通/关闭。"""
        known_states = {key: value for key, value in states.items() if isinstance(value, bool)}
        self.relay_card.update_relay_states(known_states)
        for key, label in self.relay_card.relay_labels.items():
            if key not in known_states:
                label.setText("未知")
                label.setStyleSheet(
                    "padding: 2px 6px; background-color: #b9770e; color: white; "
                    "border-radius: 6px; font-weight: bold; font-size: 16px; "
                    "min-height: 10px; max-height: 40px;"
                )
    
    def reset(self):
        """重置面板"""
        self.temp_card.set_value("--")
        self.pressure_card.set_value("--")
        self._set_relay_states({})
