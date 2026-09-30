#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验标签页
"""

import time
import os
import threading
import numpy as np
from collections import deque
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QLabel, QPushButton, QTextEdit, QGridLayout,
                               QMessageBox, QSplitter)
from PySide6.QtCore import QTimer, Signal, Qt
import pyqtgraph as pg

from utils.tangent_method_detector import TangentMethodDetector
from views.dialogs.ignition_experiment_dialog import IgnitionExperimentDialog
from views.dialogs.mode_switch_dialog import ModeSwitchDialog
from controllers.ignition_controller import IgnitionController
from models.experiment_states import IgnitionExperimentState

# 导入服务层
from services.ignition import (
    TemperatureConditionValidator,
    IgnitionDetectionService,
    DataCollectionService
)

# 导入UI组件
from views.widgets.ignition import (
    ControlPanelWidget,
    ControllerPanelWidget,
    TemperaturePanelWidget
)


class IgnitionExperimentPage(QWidget):
    """着火点实验标签页"""
    
    ignition_detected = Signal(int, float)  # 通道号, 着火温度
    connection_result = Signal(bool, str)  # (成功/失败, 消息)
    
    def __init__(self, config, ui_config):
        super().__init__()
        
        self.config = config
        self.ui_config = ui_config

        # 通道数量（从配置读取，默认6）
        _sample_channels = self.config.get('ignition_detection', {}).get('sample_channels', list(range(6)))
        self.num_channels = len(_sample_channels)

        # 控制器
        self.controller = IgnitionController(config=config)
        
        # 兼容性：保留manager的引用
        # 数据库通过 self.controller.db 访问
        self.manager = None
        self.is_running = False
        self.current_session_id = None
        self.current_experiment_config = None  # 当前实验配置
        
        # 温度数据缓存
        max_points = self.ui_config.get('chart', {}).get('max_points', 5000)
        self.temp_history = {i: deque(maxlen=max_points) for i in range(self.num_channels)}
        self.time_history = deque(maxlen=max_points)
        self.start_time = None

        # 着火点检测
        self.ignition_detected_flags = [False] * self.num_channels
        self.ignition_temperatures = [None] * self.num_channels
        self.last_temperatures = [None] * self.num_channels
        self.last_check_time = time.time()
        self._last_plot_sample_id = None
        
        # 切线法检测器
        tangent_config = self.config['ignition_detection'].get('tangent_method', {})
        self.tangent_detector = TangentMethodDetector(tangent_config)
        self.tangent_results = [None] * self.num_channels  # 存储切线法检测结果
        
        # 模式管理
        self.current_mode_name = None  # 当前模式名称
        self.current_mode_segments = None  # 当前模式的程序段列表
        
        # === 初始化服务层 ===
        # 注意：在manager初始化后才能创建validator
        self.temp_validator = None  # 稍后在设备连接后初始化
        self.ignition_detector = IgnitionDetectionService(config, self.tangent_detector)
        self.data_collector = None  # 稍后在控制器初始化后创建
        
        # 连接线程安全的信号（兼容性保留）
        # self.connection_result.connect(self._on_connection_complete)
        
        # 连接Controller信号
        self._connect_controller_signals()
        
        # 初始化UI
        self._init_ui()
        
        # 创建定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
    
    def _connect_controller_signals(self):
        """连接控制器信号（使用队列连接确保线程安全）"""
        if not self.controller:
            return
        
        # 使用队列连接确保槽函数在主线程执行
        self.controller.device_connected.connect(
            self._on_controller_device_connected,
            Qt.QueuedConnection
        )
        self.controller.experiment_created.connect(
            self._on_controller_experiment_created,
            Qt.QueuedConnection
        )
        self.controller.experiment_started.connect(
            self._on_controller_experiment_started,
            Qt.QueuedConnection
        )
        self.controller.experiment_stopped.connect(
            self._on_controller_experiment_stopped,
            Qt.QueuedConnection
        )
        self.controller.log_message.connect(
            self._thread_safe_log,
            Qt.QueuedConnection
        )
    
    def _init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建可调整的分割器
        splitter = QSplitter(Qt.Horizontal, self)
        
        # 左部分：图表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        chart_group = self._create_chart_panel()
        left_layout.addWidget(chart_group)
        splitter.addWidget(left_widget)

        # 右部分：控制面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 右1：样品温度显示面板 - 使用组件
        self.temperature_panel = TemperaturePanelWidget(self)
        right_layout.addWidget(self.temperature_panel, 0)

        # 右2：温控仪表状态显示面板 - 使用组件
        self.controller_panel = ControllerPanelWidget(self)
        self.controller_panel.mode_switch_clicked.connect(self._on_mode_switch)
        self.controller_panel.controller_run_clicked.connect(self._on_controller_run)
        self.controller_panel.controller_stop_clicked.connect(self._on_controller_stop)
        right_layout.addWidget(self.controller_panel, 0)

        # 右3： 实验控制面板 - 使用组件
        self.control_panel = ControlPanelWidget(self)
        self.control_panel.connect_clicked.connect(self._on_connect)
        self.control_panel.new_experiment_clicked.connect(self._on_new_experiment)
        self.control_panel.start_stop_clicked.connect(self._on_start_stop)
        self.control_panel.finalize_clicked.connect(self._on_finalize)
        right_layout.addWidget(self.control_panel, 0)

        # 右4： 日志面板（尽可能大）
        log_group = self._create_log_panel()
        right_layout.addWidget(log_group, 10)

        splitter.addWidget(right_widget)
        
        # 保留对组件内部控件的兼容性引用
        self.btn_connect = self.control_panel.btn_connect
        self.btn_new_experiment = self.control_panel.btn_new_experiment
        self.btn_start = self.control_panel.btn_start
        self.btn_finalize = self.control_panel.btn_finalize
        self.lbl_status = self.control_panel.lbl_status
        
        self.lbl_pv = self.controller_panel.lbl_pv
        self.lbl_sv = self.controller_panel.lbl_sv
        self.lbl_mv = self.controller_panel.lbl_mv
        self.lbl_current_mode = self.controller_panel.lbl_current_mode
        self.btn_mode_switch = self.controller_panel.btn_mode_switch
        self.btn_controller_run = self.controller_panel.btn_controller_run
        self.btn_controller_stop = self.controller_panel.btn_controller_stop
        
        self.temp_labels = self.temperature_panel.temp_labels
        self.ignition_labels = self.temperature_panel.ignition_labels
        
        # 设置初始比例（3:1）
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 200])  # 初始大小比例
        
        layout.addWidget(splitter)
    
    def _create_chart_panel(self):
        """创建图表面板"""
        group = QGroupBox("温度曲线")
        layout = QVBoxLayout(group)
        
        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot_widget.setLabel('left', '温度', units='°C')
        self.plot_widget.setLabel('bottom', '时间', units='s')
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 创建曲线
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7dc6f', '#bb8fce', '#85c1e9']
        self.plot_curves = []
        for i in range(self.num_channels):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=colors[i % len(colors)], width=2),
                name=f'样品{i+1}'
            )
            self.plot_curves.append(curve)
        
        layout.addWidget(self.plot_widget)
        
        return group
    
    def _create_log_panel(self):
        """创建日志面板"""
        group = QGroupBox("实验日志")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return group
    
    def _on_connect(self):
        """连接设备（通过控制器）"""
        # 禁用连接按钮，防止重复点击
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("连接中...")
        
        # 更新状态
        self.lbl_status.setText("状态: 连接中...")
        self.lbl_status.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #ff9800;"
        )
        
        # 使用控制器连接设备
        self.controller.connect_devices()
    
    def _on_controller_device_connected(self, success, message):
        """处理控制器的设备连接结果"""
        if success:
            # 更新manager引用（兼容性）
            self.manager = self.controller.manager
            
            # 初始化服务层实例（需要manager）
            self.temp_validator = TemperatureConditionValidator(self.config, self.manager)
            self.data_collector = DataCollectionService(self.config, self.controller)
            
            # 使用枚举状态更新UI
            state = self.controller.current_state
            self._thread_safe_update_status(
                state.display_text(),
                f"font-weight: bold; font-size: 12pt; color: {state.color()};"
            )
            self.btn_connect.setText("连接设备")
            self._update_button_states()
            
            # 启动显示更新（连接设备后立即开始实时数据更新）
            self.update_timer.start(self.ui_config['update_interval'])
        else:
            # 状态1: 应用启动（连接失败后恢复）
            self._thread_safe_update_status(
                "状态: 连接失败",
                "font-weight: bold; font-size: 12pt; color: #f44336;"
            )
            self.btn_connect.setText("连接设备")
            self._update_button_states()
            
            QMessageBox.critical(self, "连接错误", f"{message}: 请检查串口并检查设备是否通电！ ")
    
    
    def _on_new_experiment(self):
        """新建实验"""
        # 生成实验编号
        experiment_id = self.controller.generate_experiment_id()
        
        # 打开对话框
        dialog = IgnitionExperimentDialog(experiment_id, parent=self)
        dialog.confirmed.connect(self._on_experiment_config_confirmed)
        dialog.exec()
    
    def _on_experiment_config_confirmed(self, config: dict):
        """实验配置确认（通过控制器创建）"""
        success = self.controller.create_experiment(config)
        
        if not success:
            QMessageBox.critical(self, "错误", "创建实验会话失败")
    
    def _on_controller_experiment_created(self, config):
        """处理控制器的实验创建事件"""
        # 更新本地状态（兼容性）
        self.current_session_id = self.controller.current_session_id
        self.current_experiment_config = config
        
        # 新建实验时清空温度曲线缓存
        for i in range(self.num_channels):
            self.temp_history[i].clear()
            self.ignition_detected_flags[i] = False
            self.ignition_temperatures[i] = None
            self.last_temperatures[i] = None
        self.time_history.clear()
        self.start_time = None
        self._last_plot_sample_id = None
        
        # 重置着火标签显示（使用UI组件）
        self.temperature_panel.reset_ignition_status()
        
        # 使用枚举状态更新UI
        state = self.controller.current_state
        self._thread_safe_update_status(
            f"{state.display_text()} ({config.get('experiment_id', '未知')})",
            f"font-weight: bold; font-size: 12pt; color: {state.color()};"
        )
        self._update_button_states()
    
    def _on_start_stop(self):
        """启动/停止实验智能处理（根据状态判断）"""
        state = self.controller.current_state
        
        if state == IgnitionExperimentState.PREPARED:
            # 准备状态 -> 启动实验
            self._on_start()
        elif state == IgnitionExperimentState.RUNNING:
            # 运行状态 -> 停止实验
            self._on_stop()
        else:
            self._thread_safe_log(f"⚠ 启动/停止按钮在非法状态下被点击: {state.value}")
    
    def _on_stop(self):
        """停止实验（内部方法）"""
        if not self.is_running:
            return
        
        # 使用控制器停止（不停止定时器，保持实时数据更新）
        self.controller.stop_experiment()
    
    def _on_finalize(self):
        """完成实验按钮点击"""
        state = self.controller.current_state
        
        # 只有STOPPED或RUNNING状态可以完成
        if not state.can_finalize():
            QMessageBox.warning(self, "提示", "当前状态不允许完成实验")
            return
        
        # 如果还在运行，先停止
        if state == IgnitionExperimentState.RUNNING:
            self._on_stop()
        
        # 执行完成操作
        self._finalize_experiment_internal()
    
    def _on_controller_experiment_stopped(self):
        """处理控制器的实验停止事件"""
        # 更新本地状态（兼容性）
        self.is_running = False
        
        # 使用枚举状态更新UI
        state = self.controller.current_state
        exp_id = self.current_experiment_config.get('experiment_id', '未知') if self.current_experiment_config else '未知'
        self._thread_safe_update_status(
            f"{state.display_text()} ({exp_id})",
            f"font-weight: bold; font-size: 12pt; color: {state.color()};"
        )
        self._update_button_states()
    
    def _on_start(self):
        """启动实验（通过控制器）"""
        if self.controller.current_session_id is None:
            QMessageBox.warning(self, "提示", "请先新建实验！")
            return
        
        # 每次启动都检查温度条件（温度必须 < collect_start_temperature）
        if not self._check_temperature_condition():
            return
        
        # 使用控制器启动
        success = self.controller.start_experiment()
        
        if not success:
            QMessageBox.critical(self, "错误", "启动实验失败")
            return
        
        # 记录启动时间（用于图表相对时间计算）
        if self.start_time is None:
            self.start_time = time.monotonic()
        
        # 注意：温度曲线已在新建实验时清空，这里不再清空
        
        # 重置采集日志标志（使用服务层）
        if self.data_collector:
            self.data_collector.reset_collect_flag()
        
        # 启动定时器（如果未启动）
        if not self.update_timer.isActive():
            self.update_timer.start(self.ui_config['update_interval'])
    
    def _check_temperature_condition(self):
        """
        检查温度条件是否满足启动要求（使用验证器服务）
        
        Returns:
            bool: 条件满足返回True，否则返回False
        """
        # 确保验证器已初始化
        if not self.temp_validator:
            self.temp_validator = TemperatureConditionValidator(self.config, self.manager)
        
        # 调用验证器检查条件
        is_valid, message = self.temp_validator.check_start_condition()
        
        if not is_valid:
            # 显示错误消息
            if "连接" in message or "数据" in message:
                QMessageBox.warning(self, "条件检查失败", message)
            elif "异常" in message:
                QMessageBox.critical(self, "条件检查异常", message)
            else:
                QMessageBox.warning(self, "实验条件不满足", message)
            
            self._thread_safe_log(f"✗ 启动实验失败")
        else:
            self._thread_safe_log(f"✓ {message}")
        
        return is_valid
    
    def _on_controller_experiment_started(self):
        """处理控制器的实验启动事件"""
        # 更新本地状态（兼容性）
        self.is_running = True
        self.manager = self.controller.manager
        
        # 使用枚举状态更新UI
        state = self.controller.current_state
        exp_id = self.current_experiment_config.get('experiment_id', '未知') if self.current_experiment_config else '未知'
        self._thread_safe_update_status(
            f"{state.display_text()} ({exp_id})",
            f"font-weight: bold; font-size: 12pt; color: {state.color()};"
        )
        self._update_button_states()

    # 实现数据采集，写入数据库
    def _on_collect(self):
        """
        采集数据（使用数据采集服务）
        
        注意: 
        - 温度阈值判断已移至 controller.collect_data() 中
        - 此方法仅负责调用服务层方法
        """
        if not self.is_running or not self.data_collector:
            return
        
        try:
            # 使用数据采集服务采集数据
            success, is_first_time = self.data_collector.collect_data()
            
            if success and is_first_time:
                collect_start_temp = self.data_collector.get_collect_start_temperature()
                self._thread_safe_log(f"✓ 数据采集已启用（起始温度: {collect_start_temp}°C）")
                
        except Exception as e:
            self._thread_safe_log(f"✗ 采集数据失败: {e}")

    def stop_experiment(self):
        """停止实验（向后兼容）"""
        self._on_stop()
    
    def _finalize_experiment_internal(self):
        """完成实验内部方法（由完成实验按钮调用）"""
        # 1. 检查是否有活动会话
        if not self.current_session_id:
            QMessageBox.warning(self, "提示", "当前没有活动的实验会话")
            return
        
        # 2. 确认对话框
        failed = self.controller.current_state == IgnitionExperimentState.ERROR
        action = "结束异常实验" if failed else "完成实验"
        outcome = "已有数据将保留，实验记录标记为异常。" if failed else "完成后可以创建新的实验会话。"
        exp_id = self.current_experiment_config.get('experiment_id', '未知') if self.current_experiment_config else '未知'
        reply = QMessageBox.question(
            self,
            action,
            f'确定要{action}吗？\n\n'
            f'实验编号: {exp_id}\n'
            f'实验名称: {self.current_experiment_config.get("experiment_name", "未知") if self.current_experiment_config else "未知"}\n\n'
            f'{outcome}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if not self.controller.finalize_experiment():
                QMessageBox.critical(self, "保存失败", "实验未能完成，当前会话已保留，请重试。")
                return
            
            # 4. 记录日志
            self._thread_safe_log("=" * 50)
            self._thread_safe_log("实验已结束，异常状态及已有数据已保留" if failed else "✓ 实验已完成")
            self._thread_safe_log(f"  实验编号: {exp_id}")
            self._thread_safe_log("=" * 50)
            
            # 5. 清理会话状态（控制器和页面同步）
            self.current_session_id = None
            self.current_experiment_config = None
            self.is_running = False
            
            # 6. 重置页面UI状态（使用UI组件）
            for i in range(self.num_channels):
                self.ignition_detected_flags[i] = False
                self.ignition_temperatures[i] = None
            self.temperature_panel.reset_ignition_status()
            
            # 注意：保持COMPLETED状态，不要立即转换为CONNECTED
            # 在下次新建实验时，会自动转换为CONNECTED
            
            # 7. 更新按钮状态
            self._update_button_states()
            
            # 8. 更新状态显示
            state = self.controller.current_state
            self._thread_safe_update_status(
                state.display_text(),
                f"font-weight: bold; font-size: 12pt; color: {state.color()};"
            )
            
            # 9. 显示成功消息
            QMessageBox.information(
                self,
                "完成",
                "实验已成功完成！\n\n可以创建新的实验会话进行下一轮实验。"
            )
    
    def _control_controller(self, action):
        """控制温控仪表（通过控制器）"""
        self.controller.control_temperature_controller(action)
    
    def _on_controller_run(self):
        """温控器运行按钮点击 - 需要确认"""
        reply = QMessageBox.question(
            self,
            "确认运行",
            "确定要启动温控器运行吗？\n\n这将开始加热炉体。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._control_controller('run')
    
    def _on_controller_stop(self):
        """温控器停止按钮点击 - 需要确认"""
        reply = QMessageBox.question(
            self,
            "确认停止",
            "确定要停止温控器运行吗？\n\n这将停止加热程序。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._control_controller('StoP')
    
    def _on_mode_switch(self):
        """打开模式切换对话框"""
        # 检查是否可以切换模式（只在实验创建前允许）
        if self.current_session_id is not None:
            QMessageBox.warning(
                self, "无法切换", 
                "实验已创建，无法切换模式！\n\n请完成当前实验后再切换模式。"
            )
            return
        
        # 打开对话框
        dialog = ModeSwitchDialog(parent=self)
        dialog.confirmed.connect(self._on_mode_confirmed)
        dialog.exec()
    
    def _on_mode_confirmed(self, mode_name, segments):
        """处理模式确认"""
        self.current_mode_name = mode_name
        self.current_mode_segments = segments
        
        # 更新UI显示（使用UI组件）
        self.controller_panel.update_mode_display(mode_name)
        
        # 应用到温控器
        success = self._apply_mode_to_controller(segments)
        
        if success:
            self._thread_safe_log(f"✓ 模式已切换: {mode_name} ({len(segments)}个程序段)")
        else:
            self._thread_safe_log(f"✗ 模式切换失败")
    
    def _apply_mode_to_controller(self, segments):
        """将温控曲线应用到温控器"""
        if not self.controller.manager or not self.controller.manager.started:
            QMessageBox.warning(self, "错误", "设备未连接或未启动！")
            return False
        
        try:
            # 通过控制器发送程序段设置命令
            success = self.controller.set_temperature_program(segments)
            return success
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置温控曲线失败：{e}")
            return False
    
    def _update_display(self):
        """Update only valid new samples; acquisition errors stop analysis too."""
        if not self.manager:
            return
        if self.controller.is_running:
            self._on_collect()
        self._update_controller_data()
        new_sample = self._update_temperature_data()
        if self.controller.is_running and new_sample:
            self._check_ignition()
            self._update_chart()

    def _update_controller_data(self):
        data = self.manager.get_latest_data('着火点-温控仪表') or {}
        values = [data.get(key) for key in ('pv', 'sv', 'mv')]
        self.controller_panel.update_controller_data(*[
            value if self.controller._valid_temperature(value) else None for value in values
        ])

    def _update_temperature_data(self):
        data = self.manager.get_latest_data('着火点-温度模块') or {}
        channels = data.get('channels') or []
        temperatures = []
        for i, channel_number in enumerate(self.config['ignition_detection']['sample_channels']):
            channel = channels[channel_number] if 0 <= channel_number < len(channels) else None
            value = channel.get('temperature') if isinstance(channel, dict) else None
            value = value if self.controller._valid_temperature(value) else None
            self.last_temperatures[i] = value
            self.temperature_panel.update_temperature(i, value)
            temperatures.append(value)
        sample_id = data.get('sample_id')
        if (not self.controller.is_running or self.start_time is None
                or not temperatures or any(value is None for value in temperatures)
                or sample_id is None or sample_id == getattr(self, '_last_plot_sample_id', None)):
            return False
        self._last_plot_sample_id = sample_id
        self.time_history.append(time.monotonic() - self.start_time)
        for index, value in enumerate(temperatures):
            self.temp_history[index].append(value)
        return True

    def _check_ignition(self):
        """检测着火点（使用检测服务）"""
        if not self.ignition_detector:
            return
        
        # 使用检测服务检测着火点
        check_interval = self.config['ignition_detection']['check_interval']
        
        # 获取数据采集起始温度
        start_temp = 150.0
        if self.data_collector:
            start_temp = self.data_collector.get_collect_start_temperature()
        
        results = self.ignition_detector.check_ignition(
            self.temp_history,
            self.ignition_detected_flags,
            check_interval,
            start_temp,
            sample_times=self.time_history,
        )
        
        # 处理检测结果
        for channel, temperature, method in results:
            self._mark_ignition(channel, temperature, method)
    
    def _mark_ignition(self, channel, temperature, method):
        """标记着火点（使用检测服务和UI组件）"""
        # 更新标志
        self.ignition_detected_flags[channel] = True
        self.ignition_temperatures[channel] = temperature
        
        # 使用检测服务创建标记信息
        mark_info = self.ignition_detector.create_ignition_mark_info(channel, temperature, method)
        
        # 使用UI组件标记着火点
        self.temperature_panel.mark_ignition(channel, temperature, method)
        
        # 记录日志
        self._thread_safe_log(mark_info['log_message'])
        
        # 记录到数据库
        if self.current_session_id is not None:
            self.controller.db.record_ignition_detection(
                session_id=self.current_session_id,
                channel=channel + 1,  # 通道号从1开始
                ignition_temperature=temperature,
                detection_method=method
            )
        
        # 发送信号
        self.ignition_detected.emit(channel, temperature)
    
    def _update_chart(self):
        """更新图表"""
        if not self.time_history or not self.is_running:
            return
        
        times = list(self.time_history)
        if not times:
            return
        
        # 更新所有通道的曲线
        for i in range(self.num_channels):
            if self.temp_history[i] and len(self.temp_history[i]) > 0:
                temps = list(self.temp_history[i])
                # 确保长度一致，取最小长度
                min_len = min(len(times), len(temps))
                if min_len > 0:
                    self.plot_curves[i].setData(times[:min_len], temps[:min_len])
            else:
                # 如果没有数据，清空曲线
                self.plot_curves[i].setData([], [])
    
    def _thread_safe_log(self, message):
        """添加日志（支持不同类型消息的颜色显示）"""
        timestamp = time.strftime("%H:%M:%S")
        # 简单规则：不同关键词给不同颜色
        if any(x in message for x in ["✓", "成功", "已连接", "已启动", "已创建", "检测到着火点"]):
            color = "#4caf50"   # 绿色，表示成功/提示
        elif any(x in message for x in ["✗", "失败", "错误", "异常"]):
            color = "#f44336"   # 红色，表示错误
        elif any(x in message for x in ["警告", "⚠"]):
            color = "#ff9800"   # 橙色，警告
        else:
            color = "#eeeeee"   # 默认灰白

        # 用HTML格式插入文本
        html = f'<span style="color:{color};">[{timestamp}] {message}</span>'
        self.log_text.append(html)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _thread_safe_update_status(self, text, style):
        """线程安全的状态更新"""
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(style)
    
    def _thread_safe_update_buttons(self, connect_enabled, new_exp_enabled, start_enabled, stop_enabled, tangent_analysis_enabled=False):
        """线程安全的按钮状态更新（兼容旧代码，内部调用_update_button_states）"""
        self._update_button_states()
    
    def _update_button_states(self):
        """统一更新所有按钮状态（使用枚举状态和UI组件）"""
        state = self.controller.current_state
        
        # 使用UI组件更新控制面板按钮状态
        self.control_panel.update_button_states(state)
        
        # 模式切换按钮（只在设备已连接且未创建实验时启用）
        mode_switch_enabled = (
            state in [IgnitionExperimentState.CONNECTED, IgnitionExperimentState.COMPLETED]
            and self.current_session_id is None
        )
        self.controller_panel.set_mode_switch_enabled(mode_switch_enabled)
        
        # 温控器运行/停止按钮（只在设备已连接后启用）
        controller_buttons_enabled = state != IgnitionExperimentState.IDLE
        self.controller_panel.set_buttons_enabled(controller_buttons_enabled)
        
        # 切线法分析按钮（保持原有逻辑）
        if hasattr(self, 'btn_tangent_analysis'):
            self.btn_tangent_analysis.setEnabled(state == IgnitionExperimentState.STOPPED)
    
    def _thread_safe_show_prompt(self, title, message, callback):
        """线程安全的对话框显示"""
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if callback:
            callback(reply == QMessageBox.Yes)
    
    
    def prepare_shutdown(self):
        if not self.controller.prepare_shutdown():
            return False
        self.is_running = False
        self.current_session_id = self.controller.current_session_id
        self.current_experiment_config = self.controller.current_experiment_config
        self.update_timer.stop()
        return True

    def cleanup(self):
        if not self.prepare_shutdown():
            return False
        return self.controller.cleanup()
