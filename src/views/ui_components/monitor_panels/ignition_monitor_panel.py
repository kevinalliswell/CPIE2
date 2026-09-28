"""
着火点实验监控面板
显示炉温、6路样品温度、温度曲线、着火检测等核心数据
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame
)
from PySide6.QtCore import Qt, QTimer

from .base_monitor_panel import BaseMonitorPanel
from .components import LargeMetricCard


class SampleTempItem(QFrame):
    """样品温度显示项（紧凑版）"""
    
    def __init__(self, sample_id: int, parent=None):
        super().__init__(parent)
        
        self.sample_id = sample_id
        
        self.setObjectName("sampleTempItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame#sampleTempItem { "
            "background-color: #ecf0f1; "
            "border: 2px solid #bdc3c7; "
            "border-radius: 6px; "
            "padding: 5px; "
            "}"
        )
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)
        
        # 样品编号（放大字体）
        self.label = QLabel(f"样品 {sample_id}")
        self.label.setStyleSheet("font-weight: bold; color: #7f8c8d; font-size: 14px;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # 温度值（放大字体）
        self.temp_label = QLabel("--")
        self.temp_label.setProperty("class", "temp_value")
        self.temp_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 32px;")
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.temp_label)
        
        # 单位（放大字体）
        unit_label = QLabel("°C")
        unit_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(unit_label)
        
        # 着火指示
        self.ignited_label = QLabel("")
        self.ignited_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ignited_label)
    
    def set_temperature(self, temp: float):
        """设置温度"""
        if temp is None or temp <= 0:
            self.temp_label.setText("--")
        else:
            self.temp_label.setText(f"{temp:.0f}")
    
    def set_ignited(self, ignited: bool):
        """设置着火状态"""
        if ignited:
            self.ignited_label.setText("🔥")
            self.setStyleSheet(
                "QFrame#sampleTempItem { "
                "background-color: #ffe5e5; "
                "border: 2px solid #e74c3c; "
                "border-radius: 6px; "
                "padding: 5px; "
                "}"
            )
        else:
            self.ignited_label.setText("")
            self.setStyleSheet(
                "QFrame#sampleTempItem { "
                "background-color: #ecf0f1; "
                "border: 2px solid #bdc3c7; "
                "border-radius: 6px; "
                "padding: 5px; "
                "}"
            )


class IgnitionMonitorPanel(BaseMonitorPanel):
    """
    着火点实验监控面板
    
    布局：
    - 左侧：炉温卡片 + 6路样品温度网格 + 快捷操作
    - 右侧：温度曲线图 + 日志
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 样品着火状态
        self.sample_ignited = [False] * 6
        
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
        """创建数据区域（只显示温度数据）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 炉温卡片（大卡片）
        self.furnace_temp_card = LargeMetricCard(
            "炉温",
            "--",
            "°C",
            "🔥"
        )
        layout.addWidget(self.furnace_temp_card)
        
        # 6路样品温度网格
        samples_label = QLabel("📊 样品温度")
        samples_label.setObjectName("section_subtitle")
        samples_label.setStyleSheet("font-weight: bold; color: #34495e; font-size: 24px;")
        layout.addWidget(samples_label)
        
        samples_grid = QGridLayout()
        samples_grid.setSpacing(8)
        
        self.sample_items = []
        for i in range(6):
            item = SampleTempItem(i + 1)
            self.sample_items.append(item)
            row = i // 3
            col = i % 3
            samples_grid.addWidget(item, row, col)
        
        layout.addLayout(samples_grid)
        layout.addStretch()
        
        return widget
    
    def connect_controller_signals(self, controller, update_interval=None):
        """连接控制器（使用定时器轮询，和主屏一样的方式）"""
        if controller is None:
            return
        
        # 保存控制器和manager引用
        self.controller = controller
        if hasattr(controller, 'manager'):
            self.manager = controller.manager
        
        # 启动定时器轮询（和主屏一样的方式）
        # 更新间隔由副屏窗口从 ui 配置传入（控制器只持有实验段配置，其中没有 ui 信息）
        try:
            update_interval = int(update_interval) if update_interval else 500
        except (TypeError, ValueError):
            update_interval = 500

        self.update_timer.start(update_interval)
        print(f"[着火点监控面板] 定时器轮询已启动，间隔: {update_interval}ms")
    
    def disconnect_controller_signals(self, controller):
        """断开控制器（停止定时器）"""
        if controller is None:
            return
        
        # 停止定时器
        if self.update_timer:
            self.update_timer.stop()
            print("[着火点监控面板] 定时器已停止")
        
        # 清空引用
        self.controller = None
        self.manager = None
    
    # ==================== 定时器轮询更新（和主屏一样的方式）====================
    
    def _update_display(self):
        """更新显示（和主屏一样的方式）"""
        # 动态获取manager引用（因为控制器可能在连接设备后才创建manager）
        if self.controller and hasattr(self.controller, 'manager'):
            self.manager = self.controller.manager
        
        if not self.manager:
            # 如果manager还没有创建，说明设备可能还没连接
            # 不输出日志，避免刷屏
            return
        
        # 更新温控仪表数据
        self._update_controller_data()
        
        # 更新温度数据
        self._update_temperature_data()
    
    def _update_controller_data(self):
        """更新温控仪表数据（和主屏一样的方式）"""
        data = self.manager.get_latest_data('着火点-温控仪表')
        if data:
            pv = data.get('pv')
            if pv is not None:
                self.furnace_temp_card.set_value(pv, "°C")
            else:
                self.furnace_temp_card.set_value("--")
    
    def _update_temperature_data(self):
        """更新温度数据（和主屏一样的方式）"""
        data = self.manager.get_latest_data('着火点-温度模块')
        if not data:
            return
        
        channels = data.get('channels', [])
        if len(channels) < 6:
            return
        
        # 更新6路样品温度显示
        for i in range(6):
            if i < len(self.sample_items):
                if i < len(channels):
                    temp = channels[i].get('temperature')
                    self.sample_items[i].set_temperature(temp)
                else:
                    self.sample_items[i].set_temperature(None)
    
    def reset(self):
        """重置面板"""
        self.furnace_temp_card.set_value("--")
        
        for i, item in enumerate(self.sample_items):
            item.set_temperature(None)
            item.set_ignited(False)
            self.sample_ignited[i] = False

