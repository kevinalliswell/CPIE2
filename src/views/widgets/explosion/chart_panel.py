#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表面板组件
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout
import pyqtgraph as pg


class ChartPanelWidget(QGroupBox):
    """温度与压力曲线面板组件"""
    
    def __init__(self, parent=None):
        """
        初始化图表面板
        
        Args:
            parent: 父组件
        """
        super().__init__("温度与压力曲线", parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot_widget.setLabel('left', '温度', units='°C')
        self.plot_widget.setLabel('bottom', '时间', units='s')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置温度Y轴范围（0-1200℃）
        self.plot_widget.setYRange(0, 1200, padding=0)
        
        # 添加图例
        legend = self.plot_widget.addLegend(offset=(10, 10))
        
        # 创建温度曲线
        self.plot_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#ff6b6b', width=2),
            name='炉温'
        )
        
        # 创建右侧Y轴用于显示压力
        self.pressure_axis = pg.ViewBox()
        self.plot_widget.scene().addItem(self.pressure_axis)
        self.plot_widget.getAxis('right').linkToView(self.pressure_axis)
        self.pressure_axis.setXLink(self.plot_widget)
        self.plot_widget.showAxis('right')
        self.plot_widget.setLabel('right', '压力', units='kPa')
        
        # 设置压力Y轴范围（0-100kPa）
        self.pressure_axis.setYRange(0, 100, padding=0)
        
        # 创建压力曲线（在右侧Y轴上）
        self.pressure_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color='#4a9eff', width=2),
            name='压力'
        )
        self.pressure_axis.addItem(self.pressure_curve)
        
        # 手动添加压力曲线到图例
        legend.addItem(self.pressure_curve, '压力')
        
        # 更新视图函数
        def updateViews():
            self.pressure_axis.setGeometry(self.plot_widget.getViewBox().sceneBoundingRect())
            self.pressure_axis.linkedViewChanged(self.plot_widget.getViewBox(), self.pressure_axis.XAxis)
        
        updateViews()
        self.plot_widget.getViewBox().sigResized.connect(updateViews)
        
        layout.addWidget(self.plot_widget)
    
    def update_chart(self, time_data: list, temp_data: list, pressure_data: list = None):
        """
        更新图表数据
        
        Args:
            time_data: 时间数据列表
            temp_data: 温度数据列表
            pressure_data: 压力数据列表（可选）
        """
        if time_data and temp_data:
            # 更新温度曲线
            min_len = min(len(time_data), len(temp_data))
            self.plot_curve.setData(time_data[:min_len], temp_data[:min_len])
            
            # 更新压力曲线
            if pressure_data:
                min_len_pressure = min(len(time_data), len(pressure_data))
                self.pressure_curve.setData(time_data[:min_len_pressure], pressure_data[:min_len_pressure])

