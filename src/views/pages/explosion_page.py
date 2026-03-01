#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验标签页（重构版）
使用服务层和UI组件分离架构
"""

import os
import shutil
import time
from collections import deque
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QLabel, QPushButton, QTextEdit, QGridLayout,
                               QMessageBox, QCheckBox, QDialog, QApplication)
from PySide6.QtCore import QTimer, Signal, QMetaObject, Qt
import pyqtgraph as pg
from flamekit import FlameKit
from views.dialogs.flame_analyzer.config_manager import FlameAnalyzerConfig
from views.dialogs.flame_analyzer.flame_analyzer_widget import FlameAnalyzerWidget
from views.dialogs.explosion_experiment_dialog import ExplosionExperimentDialog
from controllers.explosion_controller import ExplosionController
from models.experiment_states import ExplosionExperimentState
from utils.path_manager import PathManager

# 导入服务层
from services.explosion import ExperimentValidator, RoundManager, FlameAnalysisHandler

# 导入UI组件
from views.widgets.explosion import (
    ControlPanelWidget,
    CameraPanelWidget,
    RelayPanelWidget,
    ChartPanelWidget,
    RecordsPanelWidget
)

class ExplosionExperimentPage(QWidget):
    """爆炸性实验标签页"""
    
    sequence_completed = Signal()
    # 添加线程安全的信号
    log_message = Signal(str)  # 用于日志输出
    update_status = Signal(str, str)  # (状态文本, 样式)
    update_buttons = Signal(bool, bool, bool)  # (start, stop, new_experiment)
    show_prompt = Signal(str, str, object)  # (标题, 消息, 回调函数)
    connection_result = Signal(bool, str)  # (成功/失败, 消息)
    
    def __init__(self, config, ui_config):
        super().__init__()
        
        self.config = config
        self.ui_config = ui_config
        
        self.controller = ExplosionController(config=config)
        
        # 兼容性：保留manager的引用
        # 数据库通过 self.controller.db 访问
        self.manager = None
        self.is_running = False
        self.sequence_running = False
        self.current_session_id = None
        self.current_exp_config = None
        self.current_round_number = 0
        
        # 火焰分析器
        self.flame_kit = FlameKit(resolution_index=0, exposure_us=4000)
        
        # 火焰分析器配置
        self.flame_config = FlameAnalyzerConfig()

        # 使用PathManager获取火焰分析路径
        self.temp_dir = PathManager.get_flame_temp_path()
        self.result_dir = PathManager.get_flame_results_path()
        self.max_flame_save_dir = PathManager.get_max_flame_images_path()
        
        # 火焰分析结果
        self.max_flame_length = 0.0
        self.max_flame_image_path = None
        self.flame_analyzer_window = None  # 火焰分析器窗口引用
        
        # 多轮实验管理
        self.round_records = []  # 存储每轮实验记录 [{round: 1, flame_length: 150.5, image_path: "xxx"}, ...]
        # 从配置读取实验轮次设置
        test_rounds_config = self.config.get('test-rounds', {})
        self.max_rounds = test_rounds_config.get('max-rounds', 10)  # 默认10轮（国标要求）
        self.phase_rounds = test_rounds_config.get('phase-rounds', 5)  # 默认5轮（国标要求）
        
        # 从配置读取爆炸性评估阈值（保留用于兼容性）
        thresholds_config = self.config.get('explosion-thresholds', {})
        self.threshold_no_explosion = thresholds_config.get('no-explosion', 25.0)
        self.threshold_weak_explosion = thresholds_config.get('weak-explosion', 400.0)
        self.threshold_strong_explosion = thresholds_config.get('strong-explosion', 800.0)
        
        # 温度数据缓存
        self.temp_history = deque(maxlen=200)
        self.time_history = deque(maxlen=200)
        self.pressure_history = deque(maxlen=200)  # 压力历史数据
        self.start_time = None
        
        # 相机（占位，需要导入实际的相机模块）
        self.camera = None
        self.camera_enabled = False
        
        # === 初始化服务层 ===
        # 注意：在manager初始化后才能创建validator
        self.validator = None  # 稍后在设备连接后初始化
        self.round_manager = RoundManager(config)
        self.flame_handler = FlameAnalysisHandler(self.round_manager, self.controller.db)
        
        # 连接线程安全的信号
        self.log_message.connect(self._thread_safe_log)
        self.update_status.connect(self._thread_safe_update_status)
        self.update_buttons.connect(self._thread_safe_update_buttons)
        self.show_prompt.connect(self._thread_safe_show_prompt)
        # self.connection_result.connect(self._on_connection_complete)  # 使用控制器替代
        
        # 连接Controller信号（包括喷吹阀信号）
        self._connect_controller_signals()
        
        # 初始化UI（使用组件）
        self._init_ui()
        
        # 创建定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
    
    def _connect_controller_signals(self):
        """连接控制器信号"""
        if not self.controller:
            return
        
        # 连接信号到槽
        self.controller.device_connected.connect(self._on_controller_device_connected)
        self.controller.experiment_created.connect(self._on_controller_experiment_created)
        self.controller.experiment_started.connect(self._on_controller_experiment_started)
        self.controller.experiment_stopped.connect(self._on_controller_experiment_stopped)
        self.controller.sequence_completed.connect(self._on_controller_sequence_completed)
        self.controller.log_message.connect(self._thread_safe_log)
        self.controller.status_updated.connect(self._thread_safe_update_status)
        # 连接喷吹阀信号（用于触发拍摄）
        self.controller.spray_valve_opened.connect(self._on_spray_valve_opened)
    
    def _init_ui(self):
        """初始化界面（使用组件）"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)

        # 左部：数据显示和曲线
        left_layout = QVBoxLayout()
        
        # 左上：实时数据显示（温控、压力、继电器）
        data_layout = QHBoxLayout()
        
        # 温控仪表状态
        controller_group = self._create_controller_panel()
        data_layout.addWidget(controller_group, 1)

        # 压力仪表状态
        pressure_group = self._create_pressure_panel()
        data_layout.addWidget(pressure_group, 1)

        # 继电器状态 - 使用组件
        self.relay_panel = RelayPanelWidget(self.config, self)
        self.relay_panel.auto_clean_on_clicked.connect(self._on_auto_clean_on)
        self.relay_panel.auto_clean_off_clicked.connect(self._on_auto_clean_off)
        data_layout.addWidget(self.relay_panel, 1)
        
        left_layout.addLayout(data_layout, 0)
        
        # 左下：温度曲线和实验记录卡片（横向布局）
        chart_layout = QHBoxLayout()
        
        # 温度曲线 - 使用组件
        self.chart_panel = ChartPanelWidget(self)
        chart_layout.addWidget(self.chart_panel, 3)
        
        # 实验记录卡片 - 使用组件
        self.records_panel = RecordsPanelWidget(self.max_rounds, self)
        chart_layout.addWidget(self.records_panel, 1)
        
        left_layout.addLayout(chart_layout, 1)
        
        main_layout.addLayout(left_layout, 3)
        
        # 右部：控制和日志
        right_layout = QVBoxLayout()
        
        # 相机控制面板 - 使用组件
        self.camera_panel = CameraPanelWidget(self)
        self.camera_panel.init_camera_clicked.connect(self._init_camera)
        self.camera_panel.preview_clicked.connect(self._toggle_preview)
        self.camera_panel.capture_clicked.connect(self._manual_capture)
        self.camera_panel.calibrate_clicked.connect(self._calibrate_parameters)
        self.camera_panel.analyze_clicked.connect(self._analyze_flame)
        right_layout.addWidget(self.camera_panel, 0)

        # 实验控制面板 - 使用组件
        self.control_panel = ControlPanelWidget(self.config, self)
        self.control_panel.connect_clicked.connect(self._on_connect)
        self.control_panel.new_experiment_clicked.connect(self._on_new_experiment)
        self.control_panel.start_clicked.connect(self._on_start_experiment)
        self.control_panel.stop_clicked.connect(self._on_stop)
        right_layout.addWidget(self.control_panel, 0)
        
        # 右下：实验日志
        log_group = self._create_log_panel()
        right_layout.addWidget(log_group, 1)
        
        main_layout.addLayout(right_layout, 1)
        
        # 保留对控制面板组件的兼容性引用
        self.btn_connect = self.control_panel.btn_connect
        self.btn_new_experiment = self.control_panel.btn_new_experiment
        self.btn_start = self.control_panel.btn_start
        self.btn_stop = self.control_panel.btn_stop
        self.lbl_status = self.control_panel.lbl_status
        self.chk_camera = self.control_panel.chk_camera
        
        # 保留对相机面板的引用
        self.lbl_camera_status = self.camera_panel.lbl_camera_status
        self.btn_preview = self.camera_panel.btn_preview
        self.btn_capture = self.camera_panel.btn_capture
        self.btn_calibrate = self.camera_panel.btn_calibrate
        self.btn_analyze = self.camera_panel.btn_analyze
        
        # 保留对继电器面板的引用
        self.relay_labels = self.relay_panel.relay_labels
        self.btn_auto_clean_on = self.relay_panel.btn_auto_clean_on
        self.btn_auto_clean_off = self.relay_panel.btn_auto_clean_off
        
        # 保留对图表面板的引用
        self.plot_widget = self.chart_panel.plot_widget
        self.plot_curve = self.chart_panel.plot_curve
        self.pressure_axis = self.chart_panel.pressure_axis
        self.pressure_curve = self.chart_panel.pressure_curve
    
    def _create_control_panel(self):
        """创建控制面板"""
        group = QGroupBox("实验控制")
        layout = QGridLayout(group)
        
        # 第1行第1列：连接按钮
        self.btn_connect = QPushButton("连接设备")
        self.btn_connect.setObjectName("primaryButton")
        self.btn_connect.clicked.connect(self._on_connect)
        layout.addWidget(self.btn_connect, 0, 0)
        
        # 第1行第2列：新建实验按钮
        self.btn_new_experiment = QPushButton("新建实验")
        self.btn_new_experiment.setObjectName("primaryButton")
        self.btn_new_experiment.clicked.connect(self._on_new_experiment)
        self.btn_new_experiment.setEnabled(False)
        layout.addWidget(self.btn_new_experiment, 0, 1)
        
        # 第2行第1列：启动实验按钮
        self.btn_start = QPushButton("启动实验")
        self.btn_start.setObjectName("successButton")
        self.btn_start.clicked.connect(self._on_start_experiment)
        self.btn_start.setEnabled(False)
        layout.addWidget(self.btn_start, 1, 0)
        
        # 第2行第2列：停止/完成按钮（智能按钮，根据状态动态显示）
        self.btn_stop = QPushButton("停止实验")
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop, 1, 1)
        
        # 相机选项（隐藏）
        self.chk_camera = QCheckBox("启用相机")
        self.chk_camera.setChecked(self.config['camera']['enabled'])
        # layout.addWidget(self.chk_camera) 隐藏此按钮
        
        # 第4行：状态标签（跨2列）
        self.lbl_status = QLabel("状态: 未连接")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.lbl_status, 3, 0, 1, 2)
        
        # 第5行：检测标准标签（跨2列）
        lbl_standard = QLabel("检测标准: GB/T AQ/T 1045-2010《煤尘爆炸性鉴定规范》")
        lbl_standard.setStyleSheet("font-size: 9pt; color: #666666; padding: 5px 0px;")
        lbl_standard.setWordWrap(True)
        layout.addWidget(lbl_standard, 4, 0, 1, 2)
        
        return group
    
    def _create_controller_panel(self):
        """创建温控仪表面板"""
        group = QGroupBox("温控仪表")
        layout = QGridLayout(group)
        
        # 参数列表：PV, SV, MV
        params = [
            ("PV (测量值)", "lbl_pv", "°C", 18),
            ("SV (给定值)", "lbl_sv", "°C", 14),
            ("MV (输出值)", "lbl_mv", "%", 14)
        ]
        
        for i, (label_text, attr_name, unit, font_size) in enumerate(params):
            row = i // 3
            col = i % 3
            
            # 参数布局
            param_layout = QVBoxLayout()
            
            # 参数标签
            param_label = QLabel(label_text)
            param_label.setStyleSheet("font-weight: bold;")
            param_layout.addWidget(param_label)
            
            # 参数值（单位直接显示在后面）
            value_label = QLabel(f"-- {unit}")
            # 根据参数类型设置颜色
            if attr_name == "lbl_pv":
                color = "#ff4444"  # 亮红色
            elif attr_name == "lbl_sv":
                color = "#44ff44"  # 亮绿色
            else:
                color = "#4a9eff"  # 默认蓝色
            value_label.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold; color: {color};")
            param_layout.addWidget(value_label)
            
            # 保存标签引用
            setattr(self, attr_name, value_label)
            
            layout.addLayout(param_layout, row, col)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.btn_controller_run = QPushButton("运行")
        self.btn_controller_run.setObjectName("successButton")
        self.btn_controller_run.clicked.connect(self._on_controller_run)
        self.btn_controller_run.setEnabled(False)  # 默认禁用
        btn_layout.addWidget(self.btn_controller_run)
        
        self.btn_controller_stop = QPushButton("停止")
        self.btn_controller_stop.setObjectName("dangerButton")
        self.btn_controller_stop.clicked.connect(self._on_controller_stop)
        self.btn_controller_stop.setEnabled(False)  # 默认禁用
        btn_layout.addWidget(self.btn_controller_stop)
        layout.addLayout(btn_layout, 1, 0, 1, 3)
        
        layout.setRowStretch(2, 1)
        
        return group

    def _create_pressure_panel(self):
        """创建压力仪表面板"""
        group = QGroupBox("压力仪表")
        layout = QHBoxLayout(group)
        
        # 压力
        layout.addWidget(QLabel("压力:"))
        self.lbl_pressure = QLabel("-- kPa")
        self.lbl_pressure.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self.lbl_pressure)
        
        return group
    
    def _create_relay_panel(self):
        """创建继电器面板"""
        group = QGroupBox("继电器状态")
        layout = QGridLayout(group)
        
        self.relay_labels = {}
        relay_mapping = self.config['relay_mapping']
        
        # 继电器名称中英文映射
        relay_name_map = {
            'spray_valve': '喷吹阀',
            'purge_valve': '吹扫阀',
            'vacuum_cleaner': '吸尘器',
            'reserved': '备用'
        }
        
        # 2x2布局：每个继电器占2列（名称+状态）
        index = 0
        for name, num in relay_mapping.items():
            row = index // 2  # 每2个继电器换一行
            col_offset = (index % 2) * 2  # 每个继电器占2列，所以偏移量是0或2
            
            # 继电器名称（使用中文）
            chinese_name = relay_name_map.get(name, name)
            layout.addWidget(QLabel(f"{chinese_name}"), row, col_offset)
            
            # 继电器状态
            status_label = QLabel("关闭")
            status_label.setStyleSheet(
                "padding: 2px 6px; background-color: #666; color: white; "
                "border-radius: 3px; font-weight: bold; font-size: 8pt; min-height: 24px; max-height: 24px;"
            )
            layout.addWidget(status_label, row, col_offset + 1)
            
            self.relay_labels[num] = status_label
            index += 1
        
        # 添加自清洁按钮（第3行，跨2列）
        btn_row = 2
        self.btn_auto_clean_on = QPushButton("自清洁开")
        self.btn_auto_clean_on.setObjectName("standardButton")
        self.btn_auto_clean_on.clicked.connect(self._on_auto_clean_on)
        self.btn_auto_clean_on.setEnabled(False)  # 初始状态禁用，等待设备连接
        layout.addWidget(self.btn_auto_clean_on, btn_row, 0, 1, 2)
        
        self.btn_auto_clean_off = QPushButton("自清洁关")
        self.btn_auto_clean_off.setObjectName("standardButton")
        self.btn_auto_clean_off.clicked.connect(self._on_auto_clean_off)
        self.btn_auto_clean_off.setEnabled(False)  # 初始状态禁用，等待设备连接
        layout.addWidget(self.btn_auto_clean_off, btn_row, 2, 1, 2)
        
        return group
    
    def _create_camera_panel(self):
        """创建相机控制面板"""
        group = QGroupBox("相机控制")
        layout = QGridLayout(group)
        
        # 第1行第1列：初始化相机按钮
        btn_init_camera = QPushButton("初始化相机")
        btn_init_camera.setObjectName("primaryButton")
        btn_init_camera.clicked.connect(self._init_camera)
        layout.addWidget(btn_init_camera, 0, 0)
        
        # 第1行第2列：预览按钮
        self.btn_preview = QPushButton("开始预览")
        self.btn_preview.setObjectName("standardButton")
        self.btn_preview.clicked.connect(self._toggle_preview)
        self.btn_preview.setEnabled(False)
        layout.addWidget(self.btn_preview, 0, 1)
        
        # 第2行第1列：手动拍摄按钮
        self.btn_capture = QPushButton("手动拍摄")
        self.btn_capture.setObjectName("standardButton")
        self.btn_capture.clicked.connect(self._manual_capture)
        self.btn_capture.setEnabled(False)
        layout.addWidget(self.btn_capture, 1, 0)

        # 第2行第2列：参数标定
        self.btn_calibrate = QPushButton("参数标定")
        self.btn_calibrate.setObjectName("standardButton")
        self.btn_calibrate.clicked.connect(self._calibrate_parameters)
        self.btn_calibrate.setEnabled(False)
        layout.addWidget(self.btn_calibrate, 1, 1)

        # 分析火焰按钮（暂时隐藏）
        self.btn_analyze = QPushButton("分析火焰")
        self.btn_analyze.setObjectName("warningButton")
        self.btn_analyze.clicked.connect(self._analyze_flame)
        self.btn_analyze.setEnabled(False)
        # layout.addWidget(self.btn_analyze) 暂时隐藏此按钮

        # 第3行：相机状态（跨2列）
        self.lbl_camera_status = QLabel("相机状态: 未初始化")
        layout.addWidget(self.lbl_camera_status, 2, 0, 1, 2)
        
        return group
    
    def _create_chart_panel(self):
        """创建图表面板"""
        group = QGroupBox("温度与压力曲线")
        layout = QVBoxLayout(group)
        
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
        
        return group
    
    def _create_log_panel(self):
        """创建日志面板"""
        group = QGroupBox("实验日志")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return group
    
    def _create_records_panel(self):
        """创建实验记录卡片面板"""
        group = QGroupBox("实验记录")
        layout = QVBoxLayout(group)
        
        # 表格区域（使用GridLayout）
        table_layout = QGridLayout()
        
        # 表头
        headers = ["轮次", "火焰长度(mm)", "状态"]
        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setStyleSheet(
                "font-weight: bold; padding: 5px; "
                "background-color: #3c3c3c; color: #ffffff;"
            )
            header_label.setAlignment(Qt.AlignCenter)
            table_layout.addWidget(header_label, 0, col)
        
        # 数据行（最多10行）
        # 根据实验轮次参数适配行数 self.max_rounds
        max_rows = self.max_rounds + 1
        self.record_labels = []
        for row in range(1, max_rows):
            row_labels = []
            for col in range(3):
                cell_label = QLabel("--")
                cell_label.setStyleSheet(
                    "padding: 5px; background-color: #2b2b2b; "
                    "border: 1px solid #3c3c3c;"
                )
                cell_label.setAlignment(Qt.AlignCenter)
                table_layout.addWidget(cell_label, row, col)
                row_labels.append(cell_label)
            self.record_labels.append(row_labels)
        
        layout.addLayout(table_layout)
        
        # 统计信息区域
        stats_layout = QGridLayout()
        
        # 平均值
        stats_layout.addWidget(QLabel("平均火焰长度:"), 0, 0)
        self.lbl_avg_flame = QLabel("--")
        self.lbl_avg_flame.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #4a9eff;"
        )
        stats_layout.addWidget(self.lbl_avg_flame, 0, 1)
        
        # 当前进度
        stats_layout.addWidget(QLabel("当前进度:"), 1, 0)
        self.lbl_progress = QLabel("未开始")
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #999999;")
        stats_layout.addWidget(self.lbl_progress, 1, 1)
        
        # 实验结论
        stats_layout.addWidget(QLabel("实验结论:"), 2, 0)
        self.lbl_conclusion = QLabel("--")
        self.lbl_conclusion.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #999999;"
        )
        stats_layout.addWidget(self.lbl_conclusion, 2, 1)
        
        layout.addLayout(stats_layout)
        layout.addStretch()
        
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
            
            # 初始化验证器（需要manager）
            self.validator = ExperimentValidator(self.controller.config, self.manager)
            
            # 使用枚举状态更新UI（通过组件）
            state = self.controller.current_state
            self.control_panel.update_status_display(state.display_text(), state.color())
            self.control_panel.set_connect_button_text("连接设备")
            
            # 使用统一按钮状态管理
            self._update_button_states()
            
            # 启动显示更新
            self.update_timer.start(self.ui_config['update_interval'])
        else:
            self.control_panel.update_status_display("状态: 连接失败", "#f44336")
            self.control_panel.set_connect_button_text("连接设备")
            self.control_panel.set_connect_button_enabled(True)
            
            QMessageBox.critical(self, "连接错误", f"{message}: 请检查串口并检查设备是否通电！ ")
    
    def _on_new_experiment(self):
        """新建实验（通过控制器）"""
        try:
            # 生成实验编号
            exp_id = self.controller.generate_experiment_id()
            
            # 创建对话框
            dialog = ExplosionExperimentDialog(exp_id, self)
            
            def on_confirmed(config):
                success = self.controller.create_experiment(config)
                if not success:
                    QMessageBox.critical(self, "错误", "创建实验会话失败！")
            
            dialog.confirmed.connect(on_confirmed)
            dialog.exec()
            
        except Exception as e:
            self.log_message.emit(f"✗ 新建实验异常: {e}")
            QMessageBox.critical(self, "错误", f"新建实验异常:\n{e}")
    
    def _on_controller_experiment_created(self, config):
        """处理控制器的实验创建事件"""
        # 更新本地状态（兼容性）
        self.current_session_id = self.controller.current_session_id
        self.current_exp_config = config
        self.current_round_number = 0
        
        # 清空并从数据库加载历史轮次
        self.round_records.clear()
        
        # 加载已有轮次数据（支持会话恢复）
        if self.current_session_id:
            db_rounds = self.controller.get_session_test_rounds(self.current_session_id)
            for r in db_rounds:
                self.round_records.append({
                    'round': r['round_number'],
                    'flame_length': r['flame_length'],
                    'image_path': r['max_flame_image_path']
                })
            if db_rounds:
                self.log_message.emit(f"✓ 已从数据库加载 {len(db_rounds)} 轮历史数据")
            # 同步控制器轮次计数，避免会话恢复后轮次从0重新计数
            self.controller.sync_round_number(len(db_rounds))
            self.current_round_number = len(db_rounds)
        
        self._update_records_panel()
        
        # 使用统一按钮状态管理
        self._update_button_states()
        
        # 使用枚举状态更新UI
        state = self.controller.current_state
        self.lbl_status.setText(f"{state.display_text()} (ID:{self.current_session_id})")
        self.lbl_status.setStyleSheet(
            f"font-weight: bold; font-size: 12pt; color: {state.color()};"
        )
    
    def _check_experiment_conditions(self):
        """
        检查实验条件是否满足（使用验证器服务）
        
        Returns:
            bool: 条件满足返回True，否则返回False
        """
        # 确保验证器已初始化
        if not self.validator:
            self.validator = ExperimentValidator(self.controller.config, self.manager)
        
        # 调用验证器检查条件
        is_valid, message = self.validator.check_conditions()
        
        if not is_valid:
            QMessageBox.warning(self, "实验条件不满足", message)
            self.log_message.emit("✗ 实验条件检查失败")
            # 解析message中的详细信息并记录
            for line in message.split('\n'):
                if line.strip():
                    self.log_message.emit(f"  {line.strip()}")
        else:
            self.log_message.emit("✓ 实验条件检查通过")
            # 记录详细信息
            for line in message.split('\n'):
                if line.strip():
                    self.log_message.emit(f"  {line.strip()}")
        
        return is_valid
    
    def _on_start_experiment(self):
        """启动实验（通过控制器）"""
        # 检查是否已创建实验
        if self.controller.current_session_id is None:
            QMessageBox.warning(
                self, 
                "警告", 
                "请先点击 [新建实验] 按钮创建实验会话！"
            )
            return
        
        if self.controller.sequence_running:
            QMessageBox.warning(self, "警告", "实验正在进行中")
            return
        
        # 检查是否已达到最大轮次
        if len(self.round_records) >= self.max_rounds:
            QMessageBox.warning(
                self,
                "警告",
                f"已达到最大实验轮次（{self.max_rounds}轮）！\n\n"
                f"请新建实验会话以继续测试。"
            )
            return
        
        # 实验条件检查：温度和压力
        if not self._check_experiment_conditions():
            return
        
        # 检查相机是否初始化
        if not self.camera_enabled:
            reply = QMessageBox.warning(
                self,
                "相机未初始化",
                "相机尚未初始化，无法进行高速拍照。\n\n"
                "是否仍要继续实验？\n"
                "（继续将跳过拍照环节）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.log_message.emit("✗ 实验取消：相机未初始化")
                return
            else:
                self.log_message.emit("⚠ 用户选择在相机未初始化的情况下继续实验")
        
        # 显示实验信息并确认启动
        reply = QMessageBox.question(
            self,
            '确认启动',
            f'确定要启动爆炸性实验吗？\n\n'
            f'实验名称: {self.current_exp_config["experiment_name"]}\n'
            f'样品名称: {self.current_exp_config["sample_name"]}\n'
            f'当前轮次: 第 {self.controller.current_round_number + 1} 轮\n\n'
            f'这将执行完整的时序控制流程。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重置UI数据
            self.start_time = time.time()
            self.temp_history.clear()
            self.time_history.clear()
            self.pressure_history.clear()
            self.max_flame_length = 0.0
            self.max_flame_image_path = None
            
            # 使用控制器启动
            self.controller.start_experiment()
    
    def _on_controller_experiment_started(self):
        """处理控制器的实验启动事件"""
        # 更新本地状态（兼容性）
        self.is_running = True
        self.sequence_running = True
        self.current_round_number = self.controller.current_round_number
        self.manager = self.controller.manager
        
        # 使用统一按钮状态管理
        self._update_button_states()
    
    def _on_spray_valve_opened(self):
        """处理喷吹阀打开事件 - 触发高速拍照"""
        if self.camera_enabled:
            self.log_message.emit("喷吹阀打开，开始高速拍照...")
            self._trigger_camera_capture()
        else:
            self.log_message.emit("⚠ 相机未初始化，跳过拍照")
    
    def _on_controller_sequence_completed(self):
        """处理控制器的时序完成事件"""
        # 更新本地状态
        self.sequence_running = False
        
        # 自动打开火焰分析器（使用QueuedConnection确保线程安全）
        QMetaObject.invokeMethod(
            self,
            "_analyze_flame",
            Qt.QueuedConnection
        )
        
        # 发送完成信号
        self.sequence_completed.emit()
        
        # 使用统一按钮状态管理
        self._update_button_states()
    
    def _control_relay(self, relay_name, state):
        """控制继电器（通过控制器）"""
        self.controller.control_relay(relay_name, state)
    
    def _on_auto_clean_on(self):
        """自清洁开：打开喷吹阀、吹扫阀、吸尘器"""
        if self.is_running or self.sequence_running:
            QMessageBox.warning(self, "警告", "实验进行中，无法执行自清洁操作")
            return
        
        if not self.controller or not self.controller.manager:
            QMessageBox.warning(self, "警告", "设备未连接")
            return
        
        self.log_message.emit("开始自清洁...")
        # 打开喷吹阀、吹扫阀、吸尘器
        self.controller.control_relay('spray_valve', True)
        self.controller.control_relay('purge_valve', True)
        self.controller.control_relay('vacuum_cleaner', True)
        self.log_message.emit("✓ 自清洁已开启")
    
    def _on_auto_clean_off(self):
        """自清洁关：关闭喷吹阀、吹扫阀、吸尘器"""
        if self.is_running or self.sequence_running:
            QMessageBox.warning(self, "警告", "实验进行中，无法执行自清洁操作")
            return
        
        if not self.controller or not self.controller.manager:
            QMessageBox.warning(self, "警告", "设备未连接")
            return
        
        self.log_message.emit("关闭自清洁...")
        # 关闭喷吹阀、吹扫阀、吸尘器
        self.controller.control_relay('spray_valve', False)
        self.controller.control_relay('purge_valve', False)
        self.controller.control_relay('vacuum_cleaner', False)
        self.log_message.emit("✓ 自清洁已关闭")
    
    def _verify_relays_off(self, step_config):
        """验证继电器全部关闭"""
        retry_count = step_config.get('retry_count', 3)
        retry_delay = step_config.get('retry_delay', 0.5)
        
        for attempt in range(retry_count):
            time.sleep(0.5)
            
            relay_data = self.manager.get_latest_data('爆炸性-继电器')
            
            if relay_data:
                relays = relay_data.get('relays', {})
                all_off = all(not state for state in relays.values())
                
                if all_off:
                    self.log_message.emit("  ✓ 所有继电器已关闭")
                    return
                else:
                    on_relays = [name for name, state in relays.items() if state]
                    self.log_message.emit(f"  ⚠ 部分继电器未关闭: {on_relays}")
                    
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
        
        self.log_message.emit("  ✗ 验证失败")
    
    def _on_stop(self):
        """停止/完成按钮点击（智能判断：运行中则停止，已停止则完成）"""
        state = self.controller.current_state
        
        # 如果正在运行，执行停止操作
        if state == ExplosionExperimentState.SEQUENCE_RUNNING:
            self.controller.stop_experiment()
            return
        
        # 如果正在等待分析
        if state == ExplosionExperimentState.WAITING_ANALYSIS:
            # 检查是否还在运行
            if self.is_running or self.sequence_running:
                # 先停止，停止完成后会触发_on_controller_experiment_stopped
                # 在那里会更新按钮状态，用户需要再次点击完成
                self.controller.stop_experiment()
                return
            # 如果已停止，直接完成
            self._finalize_experiment_internal()
            return
        
        # 如果会话已创建但未运行，执行完成操作
        if state == ExplosionExperimentState.SESSION_CREATED:
            self._finalize_experiment_internal()
            return
    
    def _on_controller_experiment_stopped(self):
        """处理控制器的实验停止事件"""
        # 更新本地状态（兼容性）
        self.is_running = False
        self.sequence_running = False
        
        # 使用统一按钮状态管理
        self._update_button_states()
    
    def stop_experiment(self):
        """停止实验（向后兼容）"""
        self._on_stop()
    
    def _finalize_experiment_internal(self):
        """完成实验内部方法（由智能按钮调用）"""
        # 1. 检查是否有活动会话
        if not self.current_session_id:
            QMessageBox.warning(self, "提示", "当前没有活动的实验会话")
            return
        
        # 2. 检查是否正在运行
        if self.is_running or self.sequence_running:
            QMessageBox.warning(self, "提示", "请先停止当前运行的实验")
            return
        
        # 3. 获取当前数据
        rounds = self.controller.get_session_test_rounds(self.current_session_id)
        if not rounds:
            QMessageBox.warning(self, "提示", "当前会话没有测试数据，无法完成实验")
            return

        # 4. 计算统计信息
        avg_length = self.controller.calculate_session_average(self.current_session_id)
        explosion_level = self.controller.classify_explosion_strength(avg_length)
        
        # 5. 确认对话框
        reply = QMessageBox.question(
            self,
            '完成实验',
            f'确定要完成当前实验吗？\n\n'
            f'实验名称: {self.current_exp_config["experiment_name"]}\n'
            f'样品名称: {self.current_exp_config["sample_name"]}\n'
            f'已完成轮次: {len(rounds)}\n'
            f'平均火焰长度: {avg_length:.2f}mm\n'
            f'爆炸性等级: {explosion_level}\n\n'
            f'完成后将无法继续此会话。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 6. 更新状态并调用finalize_experiment
            self.controller._set_state(ExplosionExperimentState.COMPLETED)
            db_status = self.controller.current_state.to_db_status()
            success = self.controller.finalize_experiment(
                self.current_session_id,
                status=db_status if db_status else 'completed'
            )

            if success:
                self.log_message.emit("=" * 50)
                self.log_message.emit("✓ 实验已完成并保存")
                self.log_message.emit(f"  总轮次: {len(rounds)}")
                self.log_message.emit(f"  平均火焰长度: {avg_length:.2f}mm")
                self.log_message.emit(f"  爆炸性等级: {explosion_level}")
                self.log_message.emit("=" * 50)
                
                # 7. 清理会话状态
                self.current_session_id = None
                self.current_exp_config = None
                self.current_round_number = 0
                self.round_records.clear()
                self._update_records_panel()
                
                # 8. 保持COMPLETED状态，不重置为CONNECTED
                # 用户需要通过"新建实验"按钮来开始新的实验会话
                # self.controller._set_state(ExplosionExperimentState.CONNECTED)
                self.is_running = False
                self.sequence_running = False
                
                # 9. 更新按钮状态
                self._update_button_states()
                
                # 10. 更新状态显示（使用枚举）
                state = self.controller.current_state
                self.lbl_status.setText(state.display_text())
                self.lbl_status.setStyleSheet(
                    f"font-weight: bold; font-size: 12pt; color: {state.color()};"
                )
                
                # 10. 显示成功消息
                QMessageBox.information(
                    self,
                    "完成",
                    f"实验已成功完成！\n\n"
                    f"平均火焰长度: {avg_length:.2f}mm\n"
                    f"爆炸性等级: {explosion_level}"
                )
            else:
                self.log_message.emit("✗ 保存实验结果失败")
                QMessageBox.critical(self, "错误", "保存实验结果失败")
    
    def _update_button_states(self):
        """统一更新所有按钮状态（使用枚举状态）"""
        state = self.controller.current_state
        is_running = self.is_running or self.sequence_running
        is_connected = self.manager is not None
        
        # 连接按钮
        self.btn_connect.setEnabled(state == ExplosionExperimentState.IDLE)
        
        # 新建实验：使用枚举方法
        self.btn_new_experiment.setEnabled(state.can_create_experiment())
        
        # 温控器运行/停止按钮（只在设备已连接后启用）
        if hasattr(self, 'btn_controller_run'):
            self.btn_controller_run.setEnabled(state != ExplosionExperimentState.IDLE)
        if hasattr(self, 'btn_controller_stop'):
            self.btn_controller_stop.setEnabled(state != ExplosionExperimentState.IDLE)
        
        # 启动实验：使用枚举方法
        self.btn_start.setEnabled(state.can_start())
        
        # 停止/完成按钮：智能按钮，根据状态动态显示文本和启用状态
        can_stop = state.can_stop()
        can_finalize = state.can_finalize()
        
        # 按钮可用性：停止或完成任一可用时，按钮就可用
        self.btn_stop.setEnabled(can_stop or can_finalize)
        
        # 根据状态动态更新按钮文本和样式
        if state == ExplosionExperimentState.SEQUENCE_RUNNING:
            self.btn_stop.setText("停止实验")
            self.btn_stop.setObjectName("dangerButton")
        elif state == ExplosionExperimentState.WAITING_ANALYSIS:
            # 等待分析时，如果还在运行则显示"停止实验"，否则显示"完成实验"
            if is_running:
                self.btn_stop.setText("停止实验")
                self.btn_stop.setObjectName("dangerButton")
            else:
                self.btn_stop.setText("完成实验")
                self.btn_stop.setObjectName("warningButton")
        elif state == ExplosionExperimentState.SESSION_CREATED:
            self.btn_stop.setText("完成实验")
            self.btn_stop.setObjectName("warningButton")
        else:
            # 其他状态保持默认
            self.btn_stop.setText("停止实验")
            self.btn_stop.setObjectName("dangerButton")
        
        # 应用样式（需要重新设置样式表才能生效）
        self.btn_stop.style().unpolish(self.btn_stop)
        self.btn_stop.style().polish(self.btn_stop)
        
        # 自清洁按钮：已连接且未运行时可用
        self.btn_auto_clean_on.setEnabled(is_connected and not is_running)
        self.btn_auto_clean_off.setEnabled(is_connected and not is_running)
    
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
    
    def _init_camera(self):
        """初始化相机"""
        try:
            self.camera_enabled = self.flame_kit.initialize()
            self.lbl_camera_status.setText("相机状态: " + ("已就绪" if self.camera_enabled else "未找到相机"))
            self.lbl_camera_status.setStyleSheet("color: #4caf50; font-weight: bold;" if self.camera_enabled else "color: #f44336; font-weight: bold;")
            
            self.btn_preview.setEnabled(self.camera_enabled)
            self.btn_capture.setEnabled(self.camera_enabled)
            self.btn_analyze.setEnabled(self.camera_enabled)
            self.btn_calibrate.setEnabled(self.camera_enabled)
            self.log_message.emit(f"相机初始化状态: {'✓ 相机初始化成功' if self.camera_enabled else '✗ 未找到相机'}")
        except Exception as e:
            self.log_message.emit(f"✗ 相机初始化失败: {e}")
            QMessageBox.critical(self, "错误", f"相机初始化失败:\n{e}")
            return

    def _calibrate_parameters(self):
        """参数标定 - 使用交互式对话框"""
        try:
            from views.dialogs.calibration_dialog import CalibrationDialog
            
            # 创建标定对话框
            dialog = CalibrationDialog(self.flame_kit, parent=self)
            
            # 连接标定完成信号
            def on_calibration_completed(mm_per_pixel):
                try:
                    # 保存到 FlameKit 配置
                    self.flame_kit.set_calibration(mm_per_pixel)
                    
                    # 保存到 FlameAnalyzerConfig 配置文件
                    flame_config = FlameAnalyzerConfig()
                    flame_config.update_config('image_processing.mm_per_pixel', mm_per_pixel)
                    flame_config.save_config()
                    
                    self.log_message.emit(f"✓ 参数标定完成: mm_per_pixel={mm_per_pixel:.6f} mm/pixel")
                    
                except Exception as e:
                    self.log_message.emit(f"✗ 保存标定参数失败: {e}")
                    
            dialog.calibration_completed.connect(on_calibration_completed)
            
            # 显示对话框
            result = dialog.exec()
            if result == QDialog.Rejected:
                self.log_message.emit("⚠ 参数标定已取消")
                
        except Exception as e:
            self.log_message.emit(f"✗ 参数标定失败: {e}")
            QMessageBox.critical(self, "错误", f"参数标定失败:\n{e}")
    
    def _toggle_preview(self):
        """切换预览"""
        # TODO: 实现预览功能
        self.flame_kit.preview(60)
        self.log_message.emit("✓ 预览成功")
    
    def _manual_capture(self):
        """手动拍摄"""
        try:
            self.log_message.emit("开始手动拍摄...")
            
            # 清空临时文件夹（避免旧图像干扰）
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        self.log_message.emit(f"⚠ 清理旧文件失败: {file} - {e}")
                self.log_message.emit("✓ 临时文件夹已清空")
            
            # 确保临时文件夹存在
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # 调用相机拍摄
            images, count = self.flame_kit.capture_one_second()
            self.log_message.emit(f"✓ 手动拍摄完成，共计拍摄：{count} 帧")
            
            # 保存图像到临时文件夹
            for image in images:
                shutil.copy(image, os.path.join(self.temp_dir, os.path.basename(image)))
            self.log_message.emit(f"✓ 图像保存完成，共计保存：{len(images)} 帧到 {self.temp_dir}")
            
        except Exception as e:
            self.log_message.emit(f"✗ 拍摄失败: {e}")
    
    def _trigger_camera_capture(self):
        """触发相机拍摄（时序控制中调用）"""
        if not self.camera_enabled:
            return
        
        try:
            # 清空临时文件夹（避免旧图像干扰）
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        self.log_message.emit(f"⚠ 清理旧文件失败: {file} - {e}")
                self.log_message.emit("✓ 临时文件夹已清空")
            
            # 确保临时文件夹存在
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # 调用相机高速拍摄
            images, count = self.flame_kit.capture_one_second()
            self.log_message.emit(f"✓ 自动拍摄完成，共计拍摄：{count} 帧")

            # 保存图像到临时文件夹
            for image in images:
                shutil.copy(image, os.path.join(self.temp_dir, os.path.basename(image)))
            self.log_message.emit(f"✓ 图像保存完成，共计保存：{len(images)} 帧到 {self.temp_dir}")

        except Exception as e:
            self.log_message.emit(f"✗ 相机拍摄失败: {e}")
    
    def _analyze_flame(self):
        """分析火焰 - 打开火焰分析器窗口"""
        print(f"临时存放路径: {self.temp_dir}")
        
        try:
            # 检查临时文件夹是否存在
            if not os.path.exists(self.temp_dir):
                self.log_message.emit(f"✗ 临时文件夹不存在: {self.temp_dir}")
                QMessageBox.warning(self, "警告", f"临时文件夹不存在:\n{self.temp_dir}")
                return
            
            # 检查是否有图像文件
            supported_formats = ('.jpg', '.jpeg', '.png', '.bmp')
            image_files = [f for f in os.listdir(self.temp_dir) 
                          if f.lower().endswith(supported_formats)]
            
            if not image_files:
                self.log_message.emit("✗ 临时文件夹中没有图像文件")
                QMessageBox.warning(self, "警告", "临时文件夹中没有图像文件，请先拍摄图像")
                return
            
            self.log_message.emit(f"找到 {len(image_files)} 张图像，打开分析窗口...")
            
            # 创建并显示火焰分析器窗口
            self.flame_analyzer_window = FlameAnalyzerWidget(
                input_folder=self.temp_dir,
                config=self.flame_config
            )
            
            # 连接窗口关闭信号，接收分析结果
            self.flame_analyzer_window.window_closed.connect(self._on_flame_analysis_complete)
            
            # 显示窗口
            self.flame_analyzer_window.show()
            self.log_message.emit("✓ 火焰分析窗口已打开")
            
        except Exception as e:
            self.log_message.emit(f"✗ 打开火焰分析窗口失败: {e}")
            import traceback
            self.log_message.emit(f"✗ 错误详情: {traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"打开火焰分析窗口失败:\n{e}")
    
    def _on_flame_analysis_complete(self, results: dict):
        """
        火焰分析完成回调（使用服务层处理）
        
        Args:
            results: 分析结果字典
        """
        try:
            # 确保火焰分析窗口已关闭，避免窗口管理冲突
            if hasattr(self, 'flame_analyzer_window') and self.flame_analyzer_window:
                try:
                    if self.flame_analyzer_window.isVisible():
                        self.flame_analyzer_window.close()
                    self.flame_analyzer_window = None
                except Exception:
                    pass
            
            # 使用服务层处理分析结果
            process_result = self.flame_handler.process_analysis_results(
                results=results,
                session_id=self.current_session_id,
                round_number=self.controller.current_round_number,
                round_records=self.round_records
            )
            
            if not process_result['success']:
                for msg in process_result.get('log_messages', []):
                    self.log_message.emit(msg)
                return
            
            # 输出日志
            for msg in process_result['log_messages']:
                self.log_message.emit(msg)
            
            # 更新本地状态
            self.max_flame_length = process_result['max_flame_length']
            self.max_flame_image_path = process_result['max_flame_image_path']
            
            # 添加记录到内存
            self.round_records.append(process_result['record'])
            
            # 更新实验记录卡片
            self._update_records_panel()
            
            # 获取下一步操作建议
            next_action = process_result['next_action']
            action_type = next_action['action']
            message = next_action['message']
            
            # 根据操作类型处理
            if action_type == 'phase2':
                # 询问是否继续第二阶段
                main_window = QApplication.activeWindow()
                parent_window = main_window if main_window else self
                
                reply = QMessageBox.question(
                    parent_window,
                    '继续实验',
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.No:
                    self._show_experiment_conclusion(meets_standard=False)
                else:
                    self.log_message.emit("准备开始第二阶段实验（第6-10轮）")
                    self.controller._set_state(ExplosionExperimentState.SESSION_CREATED)
                    self.is_running = False
                    self.sequence_running = False
                    self._update_button_states()
            
            elif action_type == 'complete':
                # 显示实验结论
                self.log_message.emit(message)
                meets_standard = next_action.get('meets_standard', True)
                self._show_experiment_conclusion(meets_standard=meets_standard)
            
            elif action_type == 'continue':
                # 询问是否继续下一轮
                main_window = QApplication.activeWindow()
                parent_window = main_window if main_window else self
                
                reply = QMessageBox.question(
                    parent_window,
                    '继续实验',
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.No:
                    self.log_message.emit("用户选择停止实验")
                else:
                    self.controller._set_state(ExplosionExperimentState.SESSION_CREATED)
                    self.is_running = False
                    self.sequence_running = False
                    self._update_button_states()
            
            # 清理临时文件夹
            self._cleanup_temp_folders()
            
        except Exception as e:
            self.log_message.emit(f"✗ 处理分析结果失败: {e}")
            import traceback
            self.log_message.emit(f"✗ 错误详情: {traceback.format_exc()}")
            # 即使出错也要清理临时文件夹
            try:
                self._cleanup_temp_folders()
            except Exception:
                pass
    
    def _cleanup_temp_folders(self):
        """清理临时文件夹：temp_captures 和 flame_results"""
        try:
            # 清理 temp_captures 文件夹
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        self.log_message.emit(f"⚠ 删除文件失败: {file} - {e}")
                self.log_message.emit(f"✓ 已清空临时文件夹: {self.temp_dir}")
            
            # 清理 flame_results 文件夹
            if os.path.exists(self.result_dir):
                for item in os.listdir(self.result_dir):
                    item_path = os.path.join(self.result_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            # 删除子文件夹（如 analysis_TIMESTAMP）
                            shutil.rmtree(item_path)
                    except Exception as e:
                        self.log_message.emit(f"⚠ 删除项目失败: {item} - {e}")
                self.log_message.emit(f"✓ 已清空分析结果文件夹: {self.result_dir}")
            
        except Exception as e:
            self.log_message.emit(f"✗ 清理临时文件夹失败: {e}")
    
    def _evaluate_explosion_level(self, avg_flame_length: float) -> tuple:
        """
        根据平均火焰长度评估爆炸性强弱（兼容方法，调用服务层）
        
        Args:
            avg_flame_length: 平均火焰长度(mm)
        
        Returns:
            tuple: (等级文本, 颜色代码)
        """
        return self.round_manager.evaluate_explosion_level(avg_flame_length)
    
    def _update_records_panel(self):
        """更新实验记录卡片显示（使用组件）"""
        try:
            # 使用组件更新记录
            self.records_panel.update_records(
                self.round_records,
                self.round_manager.evaluate_explosion_level
            )
            
            # 更新进度
            current_round = len(self.round_records)
            progress_text, progress_color = self.round_manager.get_progress_info(current_round)
            self.records_panel.update_progress(progress_text, progress_color)
            
            # 更新实验结论（如果已完成阶段）
            if current_round >= self.phase_rounds:
                avg_length = self.round_manager.calculate_average(self.round_records)
                level_text, level_color = self.round_manager.evaluate_explosion_level(avg_length)
                self.records_panel.update_conclusion(level_text, level_color)
            else:
                self.records_panel.update_conclusion("--", "#999999")
        
        except Exception as e:
            self.log_message.emit(f"✗ 更新记录卡片失败: {e}")
    
    def _show_experiment_conclusion(self, meets_standard: bool = None):
        """
        显示实验结论对话框（使用服务层）
        
        Args:
            meets_standard: 是否满足检测标准。None表示自动判断，True表示满足，False表示不满足
        """
        try:
            if not self.round_records:
                return
            
            # 使用服务层构建结论消息
            msg, final_meets_standard = self.flame_handler.build_conclusion_message(
                self.round_records,
                meets_standard
            )
            
            # 显示对话框
            reply = QMessageBox.question(
                self,
                '实验结论',
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 使用服务层构建日志消息
                log_messages = self.flame_handler.build_conclusion_logs(
                    self.round_records,
                    final_meets_standard
                )
                for msg in log_messages:
                    self.log_message.emit(msg)
                
                # 保存实验结果到数据库
                if self.current_session_id:
                    # 更新状态
                    self.controller._set_state(ExplosionExperimentState.COMPLETED)
                    db_status = self.controller.current_state.to_db_status()
                    finalize_success = self.controller.finalize_experiment(
                        session_id=self.current_session_id,
                        status=db_status if db_status else 'completed'
                    )
                    if finalize_success:
                        self.log_message.emit("✓ 实验结果已保存到数据库")
                    else:
                        self.log_message.emit("✗ 保存实验结果到数据库失败")
                
                # 清理会话状态
                self.current_session_id = None
                self.current_exp_config = None
                self.current_round_number = 0
                self.is_running = False
                self.sequence_running = False
                
                # 重置状态为CONNECTED，以便创建新实验
                self.controller._set_state(ExplosionExperimentState.CONNECTED)
                
                # 清空内存记录
                self.round_records.clear()
                self._update_records_panel()
                
                # 更新按钮状态
                self._update_button_states()
                
                # 更新状态显示（使用组件）
                state = self.controller.current_state
                self.control_panel.update_status_display(state.display_text(), state.color())
            
        except Exception as e:
            self.log_message.emit(f"✗ 显示实验结论失败: {e}")
            import traceback
            self.log_message.emit(f"✗ 错误详情: {traceback.format_exc()}")
    
    def _update_display(self):
        """更新显示"""
        if not self.manager:
            return
        
        # 更新温控仪表数据
        self._update_controller_data()
        
        # 更新继电器状态
        self._update_relay_status()

        # 更新压力仪表数据
        self._update_pressure_data()
        
        # 更新图表
        self._update_chart()
    
    def _update_controller_data(self):
        """更新温控仪表数据"""
        data = self.manager.get_latest_data('爆炸性-温控仪表')
        if data:
            pv = data.get('pv')
            sv = data.get('sv')
            mv = data.get('mv')
            
            self.lbl_pv.setText(f"{pv:.1f} °C" if pv is not None else "-- °C")
            self.lbl_sv.setText(f"{sv:.1f} °C" if sv is not None else "-- °C")
            self.lbl_mv.setText(f"{mv:.1f} %" if mv is not None else "-- %")
            
            # 记录温度历史
            if pv is not None and self.start_time:
                current_time = time.time() - self.start_time
                self.time_history.append(current_time)
                self.temp_history.append(pv)
    
    def _update_relay_status(self):
        """更新继电器状态（使用组件）"""
        data = self.manager.get_latest_data('爆炸性-继电器')
        if data:
            relays = data.get('relays', {})
            # 使用组件更新继电器状态
            self.relay_panel.update_all_relay_status(relays)
    
    def _update_pressure_data(self):
        """更新压力仪表数据"""
        data = self.manager.get_latest_data('爆炸性-压力表')
        if data:
            pressure = data.get('pressure', 0.0)
            self.lbl_pressure.setText(f"{pressure:.1f} kPa" if pressure is not None else "-- kPa")
            
            # 记录压力历史
            if pressure is not None and self.start_time:
                self.pressure_history.append(pressure)
    
    def _update_chart(self):
        """更新图表（使用组件）"""
        if self.time_history and self.temp_history:
            times = list(self.time_history)
            temps = list(self.temp_history)
            pressures = list(self.pressure_history) if self.pressure_history else None
            
            # 使用组件更新图表
            self.chart_panel.update_chart(times, temps, pressures)
    
    def _save_test_round(self):
        """保存测试轮次数据到数据库"""
        try:
            if not self.current_session_id:
                self.log_message.emit("⚠ 没有活动的实验会话，无法保存数据")
                return
            
            # 保存轮次数据
            round_id = self.controller.add_test_round(
                session_id=self.current_session_id,
                round_number=self.current_round_number,
                flame_length=self.max_flame_length,
                max_flame_image_path=self.max_flame_image_path
            )
            
            if round_id > 0:
                self.log_message.emit(f"✓ 轮次数据已保存 (ID:{round_id})")
                self.log_message.emit(f"  火焰长度: {self.max_flame_length:.2f}mm")
                if self.max_flame_image_path:
                    self.log_message.emit(f"  图片路径: {self.max_flame_image_path}")
            else:
                self.log_message.emit("✗ 保存轮次数据失败")
                
        except Exception as e:
            self.log_message.emit(f"✗ 保存轮次数据异常: {e}")
    
    def _prompt_next_round(self):
        """询问是否继续下一轮测试"""
        try:
            # 获取当前会话的所有轮次
            rounds = self.controller.get_session_test_rounds(self.current_session_id)
            total_rounds = len(rounds)

            self.log_message.emit(f"当前已完成 {total_rounds} 轮测试")

            # 如果已经完成5轮，计算平均值并判断是否需要继续
            if total_rounds == 5:
                avg_length = self.controller.calculate_session_average(self.current_session_id)
                self.log_message.emit(f"前5轮平均火焰长度: {avg_length:.2f}mm")

                phase_threshold = self.config.get('test-rounds', {}).get('phase-decision-threshold', 20.0)
                if avg_length < phase_threshold:
                    reply = QMessageBox.question(
                        self,
                        '继续测试',
                        f'前5轮平均火焰长度为 {avg_length:.2f}mm，低于{phase_threshold:.0f}mm。\n'
                        f'根据实验流程，需要继续进行后5轮测试。\n\n'
                        f'是否现在继续第6轮测试？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.log_message.emit("准备进行第6轮测试...")
                    else:
                        self.log_message.emit("用户选择暂停，可稍后继续")
                else:
                    self._ask_finalize_experiment(total_rounds)
            
            # 如果已经完成10轮，提示完成实验
            elif total_rounds >= 10:
                self._ask_finalize_experiment(total_rounds)
            
            # 其他情况询问是否继续
            else:
                reply = QMessageBox.question(
                    self,
                    '继续测试',
                    f'已完成 {total_rounds} 轮测试。\n\n'
                    f'是否继续下一轮测试？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.log_message.emit(f"准备进行第{total_rounds + 1}轮测试...")
                else:
                    self.log_message.emit("用户选择暂停，可稍后继续")
                    
        except Exception as e:
            self.log_message.emit(f"✗ 询问下一轮测试异常: {e}")
    
    def _ask_finalize_experiment(self, total_rounds):
        """询问是否完成实验"""
        try:
            avg_length = self.controller.calculate_session_average(self.current_session_id)
            explosion_level = self.controller.classify_explosion_strength(avg_length)

            reply = QMessageBox.question(
                self,
                '完成实验',
                f'实验已完成 {total_rounds} 轮测试。\n\n'
                f'平均火焰长度: {avg_length:.2f}mm\n'
                f'爆炸性等级: {explosion_level}\n\n'
                f'是否结束实验并保存结果？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # 更新状态
                self.controller._set_state(ExplosionExperimentState.COMPLETED)
                db_status = self.controller.current_state.to_db_status()
                success = self.controller.finalize_experiment(
                    self.current_session_id,
                    status=db_status if db_status else 'completed'
                )
                if success:
                    self.log_message.emit("=" * 50)
                    self.log_message.emit("✓ 实验已完成并保存")
                    self.log_message.emit(f"  总轮次: {total_rounds}")
                    self.log_message.emit(f"  平均火焰长度: {avg_length:.2f}mm")
                    self.log_message.emit(f"  爆炸性等级: {explosion_level}")
                    self.log_message.emit("=" * 50)
                    
                    # 清除当前会话
                    self.current_session_id = None
                    self.current_exp_config = None
                    self.current_round_number = 0
                    
                    # 更新按钮状态
                    self.btn_start.setEnabled(False)
                    self.lbl_status.setText("状态: 已连接")
                    self.lbl_status.setStyleSheet(
                        "font-weight: bold; font-size: 12pt; color: #4caf50;"
                    )
                    
                    QMessageBox.information(
                        self,
                        "实验完成",
                        f"实验已成功完成！\n\n"
                        f"平均火焰长度: {avg_length:.2f}mm\n"
                        f"爆炸性等级: {explosion_level}"
                    )
                else:
                    self.log_message.emit("✗ 保存实验结果失败")
            else:
                self.log_message.emit("用户选择继续实验")
                
        except Exception as e:
            self.log_message.emit(f"✗ 完成实验异常: {e}")

    def _thread_safe_log(self, message):
        """线程安全的日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        # 简单规则：不同关键词给不同颜色
        if any(x in message for x in ["✓", "成功", "已连接", "已启动", "已创建","已保存"]):
            color = "#4caf50"   # 绿色，表示成功/提示
        elif any(x in message for x in ["✗", "未启动", "失败", "错误", "异常"]):
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

    def _thread_safe_update_buttons(self, start_enabled, stop_enabled, new_exp_enabled):
        """线程安全的按钮状态更新"""
        self.btn_start.setEnabled(start_enabled)
        self.btn_stop.setEnabled(stop_enabled)
        self.btn_new_experiment.setEnabled(new_exp_enabled)

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
    
    def cleanup(self):
        """
        清理页面资源：停止定时器、释放相机、关闭数据库、清理控制器
        """
        try:
            # 停止更新定时器
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
            
            # 停止实验
            if self.is_running or self.sequence_running:
                self._on_stop()
            
            # 释放相机资源
            if hasattr(self, 'flame_kit') and self.flame_kit:
                try:
                    if hasattr(self.flame_kit, 'release'):
                        self.flame_kit.release()
                except Exception as e:
                    print(f"释放相机资源失败: {e}")
            
            # 关闭火焰分析器窗口
            if hasattr(self, 'flame_analyzer_window') and self.flame_analyzer_window:
                try:
                    self.flame_analyzer_window.close()
                except Exception:
                    pass
            
            # 数据库由Controller管理，无需在此关闭
            
            # 清理控制器资源
            if hasattr(self, 'controller') and self.controller:
                try:
                    if hasattr(self.controller, 'cleanup'):
                        self.controller.cleanup()
                except Exception as e:
                    print(f"清理控制器资源失败: {e}")
            
        except Exception as e:
            print(f"清理页面资源时出错: {e}")

