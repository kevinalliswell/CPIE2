#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
切线法分析结果对话框
独立显示切线法分析结果，避免与实时图表混淆
"""

import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QWidget,
                               QMessageBox, QInputDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

from utils.tangent_method_detector import TangentMethodDetector


class TangentAnalysisDialog(QDialog):
    """切线法分析结果对话框"""
    
    def __init__(self, session_id, db, config, parent=None):
        super().__init__(parent)
        
        self.session_id = session_id
        self.db = db
        self.config = config
        self.analysis_results = {}  # {channel: result}
        
        self.setWindowTitle(f"切线法着火点分析 - 实验会话 {session_id}")
        self.setMinimumSize(900, 900)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border: 1px solid #555555;
            }
            QTabBar::tab:selected {
                background-color: #4a9eff;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #555555;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        
        self._init_ui()
        self._perform_analysis()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # # 标题
        # title = QLabel("🔬 切线法着火点分析")
        # title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        # title.setStyleSheet("color: #4a9eff; padding: 10px;")
        # title.setAlignment(Qt.AlignCenter)
        # layout.addWidget(title)
        
        # 说明
        desc = QLabel(
            "根据温度曲线的放热峰切线交点估计着火温度\n"
            "分析结果需结合原始实验记录复核"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #999999; padding: 5px; font-size: 10pt;")
        layout.addWidget(desc)
        
        # 创建标签页（6个样品）
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 为每个样品创建一个标签页
        self.sample_widgets = []
        for i in range(6):
            sample_widget = self._create_sample_widget(i)
            self.sample_widgets.append(sample_widget)
            self.tab_widget.addTab(sample_widget, f"样品 {i+1}")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 新增：保存所有分析结果按钮
        self.btn_save_all = QPushButton("保存所有分析结果")
        self.btn_save_all.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_save_all.clicked.connect(self._save_all_analysis_results)
        button_layout.addWidget(self.btn_save_all)
        
        self.btn_close = QPushButton("关闭")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def _create_sample_widget(self, channel):
        """创建单个样品的显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 结果信息区域
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(10, 10, 10, 10)
        
        # 结果标签（占位，分析后更新）
        result_label = QLabel("分析中...")
        result_label.setObjectName(f"result_label_{channel}")
        result_label.setStyleSheet("""
            font-size: 12pt;
            padding: 15px;
            background-color: #3a3a3a;
            border-radius: 5px;
            border: 1px solid #555555;
        """)
        info_layout.addWidget(result_label)
        
        layout.addWidget(info_widget)
        
        # 图表
        plot_widget = pg.PlotWidget()
        plot_widget.setObjectName(f"plot_widget_{channel}")
        # plot_widget.setBackground('#1e1e1e')
        plot_widget.setBackground(None) # 设置背景为透明

        plot_widget.setLabel('left', '温度', units='°C')
        plot_widget.setLabel('bottom', '时间', units='分钟')
        plot_widget.setTitle(f"样品 {channel+1} 温度曲线及切线法分析", 
                            color='#e0e0e0', size='14pt')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.addLegend(offset=(10, 10))
        
        layout.addWidget(plot_widget)
        
        # 按钮区域（居中）
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # 左侧弹性空间
        
        # 添加"手动输入"按钮
        btn_manual_input = QPushButton("手动输入着火温度")
        btn_manual_input.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        btn_manual_input.clicked.connect(lambda: self._manual_input_temperature(channel))
        btn_manual_input.setObjectName(f"btn_manual_{channel}")
        button_layout.addWidget(btn_manual_input)
        
        # 添加"保存图片"按钮
        btn_save_image = QPushButton(f"保存样品{channel+1}分析图")
        btn_save_image.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
        """)
        btn_save_image.clicked.connect(lambda: self._save_analysis_image(channel))
        btn_save_image.setObjectName(f"btn_save_{channel}")
        button_layout.addWidget(btn_save_image)
        
        button_layout.addStretch()  # 右侧弹性空间
        
        layout.addLayout(button_layout)
        
        return widget
    
    def _perform_analysis(self):
        """执行切线法分析"""
        self.analysis_results.clear()
        try:
            # 从数据库读取完整数据
            session_data = self.db.get_session_temperature_data(self.session_id)
            
            if not session_data:
                for channel in range(6):
                    self._update_result_label(channel, None, "没有实验数据")
                return
            
            # 构建时间和温度数组
            time_seconds = np.array([record['elapsed_seconds'] for record in session_data], dtype=float)
            if not np.all(np.isfinite(time_seconds)) or np.any(np.diff(time_seconds) <= 0):
                raise ValueError("时间数据必须有限且严格递增")
            time_minutes = time_seconds / 60.0  # 转换为分钟
            
            # 创建检测器（兼容传入完整配置根节点或 ignition_experiment 子节点）
            config = self.config or {}
            config = config.get('ignition_experiment', config)
            tangent_config = config.get('ignition_detection', {}).get('tangent_method', {})
            detector = TangentMethodDetector(tangent_config)
            
            # 对每个样品进行分析
            for i in range(6):
                try:
                    temp_array = np.array(
                        [record[f'sample{i+1}_temperature'] for record in session_data], dtype=float
                    )
                except (KeyError, TypeError, ValueError):
                    self._update_result_label(i, None, "数据无效")
                    continue
                
                # 检查数据有效性
                if len(temp_array) < 50:
                    self._update_result_label(i, None, "数据不足")
                    continue
                
                if not np.all(np.isfinite(temp_array)) or np.max(temp_array) < 30:
                    self._update_result_label(i, None, "数据无效")
                    continue
                
                # 执行切线法检测
                result = detector.detect_ignition(time_seconds, temp_array)
                
                if result is not None:
                    # 添加检测方法标记
                    result['method'] = 'tangent'
                    self.analysis_results[i] = result
                    
                    # 更新结果标签
                    self._update_result_label(i, result, "成功")
                    
                    # 绘制图表
                    self._plot_analysis_result(i, time_minutes, temp_array, result)
                else:
                    self._update_result_label(i, None, "检测失败")
                    # 仍然绘制温度曲线
                    self._plot_temperature_only(i, time_minutes, temp_array)
            
        except Exception:
            for channel in range(6):
                if channel not in self.analysis_results:
                    self._update_result_label(channel, None, "实验数据无法分析")
            import traceback
            traceback.print_exc()
    
    def _update_result_label(self, channel, result, status):
        """更新结果标签"""
        label = self.sample_widgets[channel].findChild(QLabel, f"result_label_{channel}")
        
        if result is not None:
            confidence = result.get('confidence', 0)
            
            # 判断置信度
            if confidence < 0.8:
                confidence_color = '#ff9800'  # 橙色警告
                confidence_warning = " ⚠️ 置信度较低，建议手动确认"
                border_color = '#ff9800'
                bg_color = '#4a3a2a'
            else:
                confidence_color = '#4caf50'  # 绿色正常
                confidence_warning = ""
                border_color = '#4caf50'
                bg_color = '#2a4a2a'
            
            # 检测方法标记
            method = result.get('method', 'tangent')
            method_text = {
                'tangent': '切线法',
                'manual': '手动输入',
                'realtime': '实时检测'
            }.get(method, method)
            
            text = (
                f"<b>检测方法:</b> <span style='color: #4a9eff;'>{method_text}</span><br>"
                f"<b>着火点温度:</b> <span style='color: #ff9800; font-size: 18pt;'>"
                f"{result['ignition_temp']:.1f}°C</span><br>"
                f"<b>着火点时刻:</b> {result['ignition_time']/60:.1f} 分钟 "
                f"({result['ignition_time']:.0f} 秒)<br>"
                f"<b>置信度:</b> <span style='color: {confidence_color};'>{confidence:.2f}</span>"
                f"{confidence_warning}<br>"
                f"<b>基线拟合:</b> y = {result['baseline_fit'][0]:.3f}x + {result['baseline_fit'][1]:.3f} "
                f"(R={result.get('r1', result.get('baseline_r', 0)):.3f})<br>"
                f"<b>峰顶拟合:</b> y = {result['peak_fit'][0]:.3f}x + {result['peak_fit'][1]:.3f} "
                f"(R={result.get('r2', result.get('peak_r', 0)):.3f})"
            )
            label.setStyleSheet(f"""
                font-size: 11pt;
                padding: 15px;
                background-color: {bg_color};
                border-radius: 5px;
                border: 2px solid {border_color};
                color: #e0e0e0;
            """)
        else:
            text = f"<b>分析状态:</b> <span style='color: #f44336;'>{status}</span>"
            label.setStyleSheet("""
                font-size: 11pt;
                padding: 15px;
                background-color: #4a2a2a;
                border-radius: 5px;
                border: 2px solid #f44336;
                color: #e0e0e0;
            """)
        
        label.setText(text)
    
    def _plot_analysis_result(self, channel, time_minutes, temp_array, result):
        """绘制分析结果（包含切线）"""
        plot_widget = self.sample_widgets[channel].findChild(pg.PlotWidget, f"plot_widget_{channel}")
        plot_widget.clear()
        plot_widget.addLegend(offset=(10, 10))
        
        # 样品颜色
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7dc6f', '#bb8fce', '#85c1e9']
        channel_color = colors[channel]
        
        # 1. 绘制温度曲线
        plot_widget.plot(
            time_minutes, temp_array,
            pen=pg.mkPen(color=channel_color, width=2),
            name='温度曲线'
        )
        
        # 2. 绘制基线拟合
        k1, b1 = result['baseline_fit']
        baseline_range = result['baseline_range']
        t_ig_seconds = result['ignition_time']
        t_ig_minutes = t_ig_seconds / 60.0
        
        # 从数据中提取时间（秒）
        time_seconds = time_minutes * 60
        baseline_time_seconds = time_seconds[baseline_range[0]:baseline_range[1]]
        
        # 延伸到交点
        extended_baseline_time_seconds = np.linspace(
            baseline_time_seconds[0], 
            t_ig_seconds + 180,  # 延伸到交点后3分钟
            50
        )
        extended_baseline_minutes = extended_baseline_time_seconds / 60.0
        extended_baseline_temp = k1 * extended_baseline_time_seconds + b1
        
        plot_widget.plot(
            extended_baseline_minutes, extended_baseline_temp,
            pen=pg.mkPen(color='red', width=2, style=Qt.DashLine),
            name='基线拟合'
        )
        
        # 3. 绘制峰顶拟合
        k2, b2 = result['peak_fit']
        peak_range = result['peak_range']
        
        peak_time_seconds = time_seconds[peak_range[0]:peak_range[1]]
        
        # 延伸到交点
        extended_peak_time_seconds = np.linspace(
            max(baseline_time_seconds[0], t_ig_seconds - 180),  # 从交点前3分钟
            peak_time_seconds[-1],
            50
        )
        extended_peak_minutes = extended_peak_time_seconds / 60.0
        extended_peak_temp = k2 * extended_peak_time_seconds + b2
        
        plot_widget.plot(
            extended_peak_minutes, extended_peak_temp,
            pen=pg.mkPen(color='blue', width=2, style=Qt.DotLine),
            name='峰顶拟合'
        )
        
        # 4. 标注着火点
        T_ig = result['ignition_temp']
        
        scatter = pg.ScatterPlotItem(
            [t_ig_minutes], [T_ig],
            symbol='star', size=20,
            brush=pg.mkBrush(color='orange'),
            pen=pg.mkPen(color='red', width=2)
        )
        plot_widget.addItem(scatter)
        
        # 5. 添加文本标注
        text = pg.TextItem(
            f"着火点\n{T_ig:.1f}°C\n{t_ig_minutes:.1f}min",
            color='orange',
            anchor=(0.5, 1.5),
            border=pg.mkPen(color='red', width=2),
            fill=pg.mkBrush(0, 0, 0, 180)
        )
        text.setPos(t_ig_minutes, T_ig)
        plot_widget.addItem(text)
        
        # 6. 添加垂直辅助线
        inf_line = pg.InfiniteLine(
            pos=t_ig_minutes,
            angle=90,
            pen=pg.mkPen(color='orange', width=1, style=Qt.DotLine)
        )
        inf_line.setOpacity(0.5)
        plot_widget.addItem(inf_line)
    
    def _plot_temperature_only(self, channel, time_minutes, temp_array):
        """仅绘制温度曲线（分析失败时）"""
        plot_widget = self.sample_widgets[channel].findChild(pg.PlotWidget, f"plot_widget_{channel}")
        plot_widget.clear()
        
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7dc6f', '#bb8fce', '#85c1e9']
        channel_color = colors[channel]
        
        plot_widget.plot(
            time_minutes, temp_array,
            pen=pg.mkPen(color=channel_color, width=2),
            name='温度曲线'
        )
    
    
    def _manual_input_temperature(self, channel):
        """手动输入着火温度"""
        try:
            # 获取当前分析结果（如果有）
            current_result = self.analysis_results.get(channel)
            default_value = current_result['ignition_temp'] if current_result else 100.0
            
            # 弹出输入对话框
            temp, ok = QInputDialog.getDouble(
                self,
                f"手动输入着火温度 - 样品{channel+1}",
                "请输入人工判断的着火温度（°C）:",
                default_value,  # value
                100.0,            # minValue
                600.0,         # maxValue
                1               # decimals
            )
            
            if ok:
                if not np.isfinite(temp):
                    QMessageBox.warning(self, "输入无效", "着火温度必须是有限数值")
                    return
                # 从数据库获取温度数据以找到对应时间
                session_data = self.db.get_session_temperature_data(self.session_id)
                
                if not session_data:
                    QMessageBox.warning(self, "错误", "无法读取实验数据")
                    return
                
                # 构建时间和温度数组
                time_seconds = np.array([record['elapsed_seconds'] for record in session_data], dtype=float)
                temp_array = np.array([record[f'sample{channel+1}_temperature'] for record in session_data], dtype=float)
                if (not np.all(np.isfinite(time_seconds)) or not np.all(np.isfinite(temp_array))
                        or np.any(np.diff(time_seconds) <= 0)):
                    QMessageBox.warning(self, "数据无效", "实验温度必须有限，时间必须有限且严格递增")
                    return
                
                # 找到最接近输入温度的时间点
                idx = np.argmin(np.abs(temp_array - temp))
                ignition_time = float(time_seconds[idx])
                
                # 创建或更新结果
                if current_result:
                    # 保留原有分析结果，只更新温度、时间和方法
                    current_result['ignition_temp'] = temp
                    current_result['ignition_time'] = ignition_time
                    current_result['method'] = 'manual'
                    current_result['confidence'] = 1.0  # 手动输入置信度设为1.0
                else:
                    # 创建新的手动输入结果
                    current_result = {
                        'ignition_temp': temp,
                        'ignition_time': ignition_time,
                        'method': 'manual',
                        'confidence': 1.0,
                        'baseline_fit': [0, 0],
                        'peak_fit': [0, 0],
                        'r1': 0,
                        'r2': 0,
                        'baseline_range': [0, 0],
                        'peak_range': [0, 0]
                    }
                
                # 保存到分析结果
                self.analysis_results[channel] = current_result
                
                # 更新UI
                self._update_result_label(channel, current_result, "手动输入")
                
                # 重新绘制图表（如果有完整数据）
                time_minutes = time_seconds / 60.0
                if current_result.get('baseline_fit', [0, 0])[0] != 0:
                    self._plot_analysis_result(channel, time_minutes, temp_array, current_result)
                else:
                    # 只绘制温度曲线和着火点标记
                    self._plot_temperature_with_marker(channel, time_minutes, temp_array, temp, ignition_time/60.0)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"手动输入失败: {e}")
    
    def _plot_temperature_with_marker(self, channel, time_minutes, temp_array, ignition_temp, ignition_time_minutes):
        """绘制温度曲线和着火点标记（用于手动输入）"""
        plot_widget = self.sample_widgets[channel].findChild(pg.PlotWidget, f"plot_widget_{channel}")
        plot_widget.clear()
        plot_widget.addLegend(offset=(10, 10))
        
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7dc6f', '#bb8fce', '#85c1e9']
        channel_color = colors[channel]
        
        # 绘制温度曲线
        plot_widget.plot(
            time_minutes, temp_array,
            pen=pg.mkPen(color=channel_color, width=2),
            name='温度曲线'
        )
        
        # 标注手动输入的着火点
        scatter = pg.ScatterPlotItem(
            [ignition_time_minutes], [ignition_temp],
            symbol='star', size=20,
            brush=pg.mkBrush(color='orange'),
            pen=pg.mkPen(color='red', width=2)
        )
        plot_widget.addItem(scatter)
        
        # 添加文本标注
        text = pg.TextItem(
            f"着火点(手动)\n{ignition_temp:.1f}°C\n{ignition_time_minutes:.1f}min",
            color='orange',
            anchor=(0.5, 1.5),
            border=pg.mkPen(color='red', width=2),
            fill=pg.mkBrush(0, 0, 0, 180)
        )
        text.setPos(ignition_time_minutes, ignition_temp)
        plot_widget.addItem(text)
        
        # 添加垂直辅助线
        inf_line = pg.InfiniteLine(
            pos=ignition_time_minutes,
            angle=90,
            pen=pg.mkPen(color='orange', width=1, style=Qt.DotLine)
        )
        inf_line.setOpacity(0.5)
        plot_widget.addItem(inf_line)
    
    def _save_single_channel_data(self, channel, result, image_dir):
        """
        保存单个通道的分析图和数据
        
        Args:
            channel: 通道索引(0-5)
            result: 分析结果字典
            image_dir: 图片保存目录
            
        Returns:
            bool: 是否保存成功
        """
        import os
        
        # 生成文件名
        image_filename = f"tangent_ch{channel+1}.png"
        image_path = os.path.join(image_dir, image_filename)
        
        # 保存图片
        plot_widget = self.sample_widgets[channel].findChild(pg.PlotWidget, f"plot_widget_{channel}")
        exporter = ImageExporter(plot_widget.plotItem)
        exporter.parameters()['width'] = 1200  # 设置宽度
        exporter.export(image_path)
        
        # 获取检测方法
        detection_method = result.get('method', 'tangent')
        
        # 保存或更新数据库记录
        success = self.db.upsert_ignition_detection(
            session_id=self.session_id,
            channel=channel + 1,
            ignition_temperature=result['ignition_temp'],
            detection_method=detection_method,
            image_path=image_path
        )
        
        return success
    
    def _save_analysis_image(self, channel):
        """保存单个样品的分析图和数据"""
        result = self.analysis_results.get(channel)
        if result is None:
            QMessageBox.warning(self, "提示", f"样品{channel+1}没有有效的分析结果")
            return
        
        try:
            # 获取实验信息
            from utils.path_manager import PathManager
            import os
            
            # 查询会话信息获取实验编号
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT experiment_id FROM experiment_sessions WHERE id = ?", (self.session_id,))
            row = cursor.fetchone()
            experiment_id = row[0] if row and row[0] else f'session_{self.session_id}'
            
            # 创建保存目录
            image_dir = PathManager.get_data_path(f"analysis_images/{experiment_id}")
            os.makedirs(image_dir, exist_ok=True)
            
            # 调用公共保存方法
            success = self._save_single_channel_data(channel, result, image_dir)
            
            if success:
                # 生成图片路径用于显示
                image_filename = f"tangent_ch{channel+1}.png"
                image_path = os.path.join(image_dir, image_filename)
                detection_method = result.get('method', 'tangent')
                
                QMessageBox.information(
                    self, 
                    "保存成功", 
                    f"样品{channel+1}分析结果已保存\n"
                    f"着火温度: {result['ignition_temp']:.1f}°C\n"
                    f"检测方法: {detection_method}\n"
                    f"图片路径: {image_path}"
                )
            else:
                raise Exception("数据库保存失败")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def _save_all_analysis_results(self):
        """批量保存所有样品的分析结果到数据库"""
        if not self.analysis_results:
            QMessageBox.warning(self, "提示", "没有可保存的分析结果")
            return
        
        # 检查置信度
        low_confidence_channels = []
        for channel, result in self.analysis_results.items():
            confidence = result.get('confidence', 0)
            method = result.get('method', 'tangent')
            # 只检查切线法结果，手动输入的不检查
            if method == 'tangent' and confidence < 0.85:
                low_confidence_channels.append((channel + 1, confidence))
        
        # 如果有低置信度样品，提醒用户
        if low_confidence_channels:
            warning_text = "检测到以下样品的置信度低于0.85，建议手动修正后再保存：\n\n"
            for ch, conf in low_confidence_channels:
                warning_text += f"样品{ch}: 置信度 {conf:.2f}\n"
            warning_text += "\n是否继续保存？"
            
            reply = QMessageBox.question(
                self,
                "⚠️ 置信度警告",
                warning_text,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # 开始批量保存
        saved_count = 0
        failed_channels = []
        
        try:
            from utils.path_manager import PathManager
            import os
            
            # 查询会话信息获取实验编号
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT experiment_id FROM experiment_sessions WHERE id = ?", (self.session_id,))
            row = cursor.fetchone()
            experiment_id = row[0] if row and row[0] else f'session_{self.session_id}'
            
            # 创建保存目录
            image_dir = PathManager.get_data_path(f"analysis_images/{experiment_id}")
            os.makedirs(image_dir, exist_ok=True)
            
            # 批量保存每个样品
            for channel in range(6):
                if channel in self.analysis_results:
                    try:
                        result = self.analysis_results[channel]
                        
                        # 调用公共保存方法
                        success = self._save_single_channel_data(channel, result, image_dir)
                        
                        if success:
                            saved_count += 1
                        else:
                            failed_channels.append(channel+1)
                            
                    except Exception:
                        failed_channels.append(channel+1)
            
            # 显示保存结果
            if failed_channels:
                QMessageBox.warning(
                    self, 
                    "保存完成", 
                    f"已成功保存 {saved_count} 个样品的分析结果到数据库\n"
                    f"失败的样品: {', '.join(map(str, failed_channels))}"
                )
            else:
                QMessageBox.information(
                    self, 
                    "保存成功", 
                    f"已成功保存 {saved_count} 个样品的分析结果到数据库\n"
                    f"图片保存路径: {image_dir}"
                )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"保存过程发生异常: {e}")
