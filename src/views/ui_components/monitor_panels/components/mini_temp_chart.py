"""
小型温度曲线图
适用于触摸屏显示温度变化趋势
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from collections import deque
import pyqtgraph as pg


class MiniTempChart(QFrame):
    """
    小型温度曲线图
    显示温度变化趋势（简化版）
    """
    
    def __init__(self, title: str = "温度曲线", max_points: int = 100, 
                 width: int = 380, height: int = 220, parent=None):
        super().__init__(parent)
        
        self.setObjectName("miniTempChart")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.max_points = max_points

        self.view_width = width
        self.view_height = height
        
        # 数据存储
        self.time_data = deque(maxlen=max_points)
        self.temp_data = deque(maxlen=max_points)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel(f"📈 {title}")
        title_label.setObjectName("miniChartTitle")
        title_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(title_label)
        
        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_widget.setMinimumSize(self.view_width, self.view_height)
        self.plot_widget.setBackground('#ecf0f1')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', '温度', units='°C')
        self.plot_widget.setLabel('bottom', '时间', units='s')
        
        # 创建曲线
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#e74c3c', width=2),
            symbol='o',
            symbolSize=4,
            symbolBrush='#c0392b'
        )
        
        layout.addWidget(self.plot_widget)
        
        # 当前温度标签
        self.current_temp_label = QLabel("当前温度: --")
        self.current_temp_label.setObjectName("miniChartCurrentTemp")
        self.current_temp_label.setStyleSheet("color: #7f8c8d;")
        self.current_temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_temp_label)
    
    def add_data_point(self, time: float, temperature: float):
        """
        添加数据点
        Args:
            time: 时间（秒）
            temperature: 温度（°C）
        """
        if temperature is None:
            return
        
        self.time_data.append(time)
        self.temp_data.append(temperature)
        
        # 更新曲线
        self.curve.setData(list(self.time_data), list(self.temp_data))
        
        # 更新当前温度标签
        self.current_temp_label.setText(f"当前温度: {temperature:.1f}°C")
    
    def clear_data(self):
        """清空数据"""
        self.time_data.clear()
        self.temp_data.clear()
        self.curve.setData([], [])
        self.current_temp_label.setText("当前温度: --")
    
    def set_y_range(self, min_temp: float, max_temp: float):
        """设置Y轴范围"""
        self.plot_widget.setYRange(min_temp, max_temp, padding=0.1)

