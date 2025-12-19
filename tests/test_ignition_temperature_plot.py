#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验温度数据可视化测试脚本
读取 ignition_experiment.db 中的 ignition_realtime_data 表
使用 pyqtgraph 绘制 pv 和 ch1-ch6 温度随时间变化的曲线
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import sqlite3

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
from PySide6.QtCore import Qt
import pyqtgraph as pg
import numpy as np


class IgnitionTemperaturePlotWindow(QMainWindow):
    """着火点温度数据可视化窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("着火点实验温度数据可视化")
        self.setGeometry(100, 100, 1400, 900)
        
        # 数据库路径
        self.db_path = project_root / 'data' / 'ignition_experiment.db'
        
        # 数据存储
        self.timestamps = []
        self.pv_data = []
        self.ch_data = {f'ch{i}': [] for i in range(1, 7)}
        
        # 设置深色主题
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11pt;
                padding: 5px;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题和控制区域
        control_layout = QHBoxLayout()
        
        title = QLabel("🔥 着火点实验温度数据可视化")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #4a9eff;")
        control_layout.addWidget(title)
        
        control_layout.addStretch()
        
        # 刷新按钮
        self.btn_refresh = QPushButton("刷新数据")
        self.btn_refresh.clicked.connect(self.load_data)
        control_layout.addWidget(self.btn_refresh)
        
        # 会话选择下拉框
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(200)
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)
        control_layout.addWidget(QLabel("选择会话:"))
        control_layout.addWidget(self.session_combo)
        
        main_layout.addLayout(control_layout)
        
        # 信息标签
        self.info_label = QLabel("正在加载数据...")
        self.info_label.setStyleSheet("color: #95a5a6; font-size: 10pt;")
        main_layout.addWidget(self.info_label)
        
        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', '温度', units='°C', color='#e0e0e0', fontSize=12)
        self.plot_widget.setLabel('bottom', '时间', units='秒', color='#e0e0e0', fontSize=12)
        self.plot_widget.setTitle("温度-时间曲线", color='#e0e0e0', size='14pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        
        # 设置颜色
        colors = {
            'pv': '#ff6b6b',      # 红色 - 炉膛温度
            'ch1': '#4ecdc4',     # 青色 - 样品1
            'ch2': '#45b7d1',     # 蓝色 - 样品2
            'ch3': '#f7dc6f',     # 黄色 - 样品3
            'ch4': '#bb8fce',     # 紫色 - 样品4
            'ch5': '#85c1e9',     # 浅蓝 - 样品5
            'ch6': '#52be80'      # 绿色 - 样品6
        }
        
        # 创建曲线
        self.curves = {}
        self.curves['pv'] = self.plot_widget.plot(
            pen=pg.mkPen(color=colors['pv'], width=2),
            name='炉膛温度 (PV)'
        )
        
        for i in range(1, 7):
            ch_name = f'ch{i}'
            self.curves[ch_name] = self.plot_widget.plot(
                pen=pg.mkPen(color=colors[ch_name], width=2),
                name=f'样品{i} (CH{i})'
            )
        
        main_layout.addWidget(self.plot_widget)
        
        # 加载数据
        self.load_sessions()
        self.load_data()
    
    def load_sessions(self):
        """加载所有实验会话"""
        try:
            if not os.path.exists(self.db_path):
                self.info_label.setText(f"❌ 数据库文件不存在: {self.db_path}")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询所有会话
            cursor.execute("""
                SELECT id, experiment_id, experiment_name, start_time, end_time
                FROM experiment_sessions
                ORDER BY start_time DESC
            """)
            
            sessions = cursor.fetchall()
            conn.close()
            
            self.session_combo.clear()
            self.session_combo.addItem("全部数据", None)
            
            for session in sessions:
                session_id, exp_id, exp_name, start_time, end_time = session
                display_text = f"会话 {session_id}"
                if exp_id:
                    display_text += f" - {exp_id}"
                elif exp_name:
                    display_text += f" - {exp_name}"
                if start_time:
                    display_text += f" ({start_time[:19]})"
                
                self.session_combo.addItem(display_text, session_id)
            
            if len(sessions) > 0:
                self.info_label.setText(f"✓ 找到 {len(sessions)} 个实验会话")
            else:
                self.info_label.setText("⚠ 未找到实验会话，将显示所有数据")
                
        except Exception as e:
            self.info_label.setText(f"❌ 加载会话失败: {str(e)}")
    
    def on_session_changed(self, index):
        """会话选择改变时重新加载数据"""
        self.load_data()
    
    def load_data(self):
        """从数据库加载温度数据"""
        try:
            if not os.path.exists(self.db_path):
                self.info_label.setText(f"❌ 数据库文件不存在: {self.db_path}")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取选中的会话ID
            session_id = self.session_combo.currentData()
            
            # 构建查询
            if session_id is not None:
                # 查询特定会话的数据
                cursor.execute("""
                    SELECT timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                    FROM ignition_realtime_data
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))
            else:
                # 查询所有数据
                cursor.execute("""
                    SELECT timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                    FROM ignition_realtime_data
                    ORDER BY timestamp ASC
                """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                self.info_label.setText("⚠ 未找到数据")
                # 清空图表
                self.timestamps = []
                self.pv_data = []
                for ch in self.ch_data:
                    self.ch_data[ch] = []
                self.update_plot()
                return
            
            # 解析数据
            self.timestamps = []
            self.pv_data = []
            for ch in self.ch_data:
                self.ch_data[ch] = []
            
            # 解析第一个时间戳作为基准
            first_timestamp = None
            
            for row in rows:
                timestamp_str, pv, ch1, ch2, ch3, ch4, ch5, ch6 = row
                
                # 解析时间戳
                try:
                    # 尝试带毫秒的格式
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        # 尝试不带毫秒的格式
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                
                if first_timestamp is None:
                    first_timestamp = timestamp
                
                # 计算相对时间（秒）
                elapsed_seconds = (timestamp - first_timestamp).total_seconds()
                
                self.timestamps.append(elapsed_seconds)
                self.pv_data.append(float(pv) if pv is not None else 0.0)
                self.ch_data['ch1'].append(float(ch1) if ch1 is not None else 0.0)
                self.ch_data['ch2'].append(float(ch2) if ch2 is not None else 0.0)
                self.ch_data['ch3'].append(float(ch3) if ch3 is not None else 0.0)
                self.ch_data['ch4'].append(float(ch4) if ch4 is not None else 0.0)
                self.ch_data['ch5'].append(float(ch5) if ch5 is not None else 0.0)
                self.ch_data['ch6'].append(float(ch6) if ch6 is not None else 0.0)
            
            # 更新信息标签
            data_count = len(self.timestamps)
            if data_count > 0:
                time_range = f"{self.timestamps[0]:.1f} - {self.timestamps[-1]:.1f} 秒"
                pv_range = f"{min(self.pv_data):.1f} - {max(self.pv_data):.1f}°C"
                self.info_label.setText(
                    f"✓ 已加载 {data_count} 条数据 | 时间范围: {time_range} | "
                    f"炉膛温度范围: {pv_range}"
                )
            else:
                self.info_label.setText("⚠ 数据解析失败")
            
            # 更新图表
            self.update_plot()
            
        except Exception as e:
            import traceback
            error_msg = f"❌ 加载数据失败: {str(e)}\n{traceback.format_exc()}"
            self.info_label.setText(error_msg)
            print(error_msg)
    
    def update_plot(self):
        """更新图表显示"""
        if not self.timestamps:
            return
        
        # 转换为 numpy 数组
        time_array = np.array(self.timestamps)
        pv_array = np.array(self.pv_data)
        
        # 更新 PV 曲线
        self.curves['pv'].setData(time_array, pv_array)
        
        # 更新各通道曲线
        for ch_name in self.ch_data:
            if self.ch_data[ch_name]:
                ch_array = np.array(self.ch_data[ch_name])
                self.curves[ch_name].setData(time_array, ch_array)
        
        # 自动调整坐标轴范围
        if len(time_array) > 0:
            self.plot_widget.setXRange(time_array[0], time_array[-1], padding=0.05)
        
        # 计算Y轴范围（包含所有数据）
        all_values = [pv_array]
        for ch_name in self.ch_data:
            if self.ch_data[ch_name]:
                all_values.append(np.array(self.ch_data[ch_name]))
        
        if all_values:
            all_data = np.concatenate(all_values)
            if len(all_data) > 0:
                y_min = np.min(all_data)
                y_max = np.max(all_data)
                y_padding = (y_max - y_min) * 0.1
                self.plot_widget.setYRange(
                    max(0, y_min - y_padding), 
                    y_max + y_padding, 
                    padding=0
                )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建窗口
    window = IgnitionTemperaturePlotWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
