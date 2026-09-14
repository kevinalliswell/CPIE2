#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数配置标签页
"""

import yaml
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QLabel, QPushButton, QLineEdit, QSpinBox,
                               QDoubleSpinBox, QGridLayout, QScrollArea,
                               QMessageBox, QTabWidget, QCheckBox)
from PySide6.QtCore import Signal

# 尝试导入PathManager
try:
    from utils.path_manager import PathManager
    HAS_PATH_MANAGER = True
except ImportError:
    HAS_PATH_MANAGER = False


class ConfigPage(QWidget):
    """参数配置标签页"""
    
    config_updated = Signal(dict)
    
    def __init__(self, config, ui_config, config_path='experiment_config.yaml'):
        super().__init__()
        
        self.config = config
        self.ui_config = ui_config
        self.config_path = config_path
        
        # 加载火焰分析器配置
        self.flame_analyzer_config_path = self._get_flame_analyzer_config_path()
        self.flame_analyzer_config = self._load_flame_analyzer_config()
        
        # 存储所有配置控件
        self.config_widgets = {}
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 着火点实验配置
        ignition_tab = self._create_ignition_config_tab()
        self.tab_widget.addTab(ignition_tab, "着火点实验参数")
        
        # 爆炸性实验配置
        explosion_tab = self._create_explosion_config_tab()
        self.tab_widget.addTab(explosion_tab, "爆炸性实验参数")
        
        # 通用配置
        general_tab = self._create_general_config_tab()
        self.tab_widget.addTab(general_tab, "通用设置")
        
        # 火焰分析器配置
        flame_analyzer_tab = self._create_flame_analyzer_config_tab()
        self.tab_widget.addTab(flame_analyzer_tab, "火焰分析器参数")
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 重置按钮
        btn_reset = QPushButton("重置为默认值")
        btn_reset.clicked.connect(self._on_reset)
        btn_reset.setStyleSheet("QPushButton { background-color: #ff9800; }")
        button_layout.addWidget(btn_reset)
        
        # 保存按钮
        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(self._on_save)
        btn_save.setStyleSheet("QPushButton { background-color: #4caf50; }")
        button_layout.addWidget(btn_save)
        
        # 应用按钮
        btn_apply = QPushButton("应用配置")
        btn_apply.clicked.connect(self._on_apply)
        btn_apply.setStyleSheet("QPushButton { background-color: #4a9eff; }")
        button_layout.addWidget(btn_apply)
        
        layout.addLayout(button_layout)
    
    def _create_ignition_config_tab(self):
        """创建着火点实验配置标签页"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 串口配置
        serial_group = self._create_ignition_serial_group()
        layout.addWidget(serial_group)
        
        # 数据采集配置
        collect_group = self._create_ignition_collect_group()
        layout.addWidget(collect_group)
        
        # 着火点判断参数
        detection_group = self._create_ignition_detection_group()
        layout.addWidget(detection_group)
        
        layout.addStretch()
        
        return scroll
    
    def _create_ignition_serial_group(self):
        """创建着火点实验串口配置组"""
        group = QGroupBox("串口配置")
        layout = QGridLayout(group)
        
        row = 0
        serial_config = self.config['ignition_experiment']['serial']
        
        # COM口
        layout.addWidget(QLabel("COM口:"), row, 0)
        port_edit = QLineEdit(serial_config['port'])
        self.config_widgets['ignition_serial_port'] = port_edit
        layout.addWidget(port_edit, row, 1)
        
        row += 1
        # 波特率
        layout.addWidget(QLabel("波特率:"), row, 0)
        baudrate_spin = QSpinBox()
        baudrate_spin.setRange(1200, 115200)
        baudrate_spin.setValue(int(serial_config['baudrate']))
        self.config_widgets['ignition_serial_baudrate'] = baudrate_spin
        layout.addWidget(baudrate_spin, row, 1)
        
        row += 1
        # 超时
        layout.addWidget(QLabel("超时时间(秒):"), row, 0)
        timeout_spin = QDoubleSpinBox()
        timeout_spin.setRange(0.1, 10.0)
        timeout_spin.setSingleStep(0.1)
        timeout_spin.setValue(float(serial_config['timeout']))
        self.config_widgets['ignition_serial_timeout'] = timeout_spin
        layout.addWidget(timeout_spin, row, 1)
        
        return group
    
    def _create_ignition_collect_group(self):
        """创建数据采集配置组"""
        group = QGroupBox("数据采集配置")
        layout = QGridLayout(group)
        
        row = 0
        collect_start_temp = self.config['ignition_experiment'].get('collect_start_temperature', 200.0)
        
        # 采集判断起始温度
        layout.addWidget(QLabel("采集判断起始温度(°C):"), row, 0)
        start_temp_spin = QDoubleSpinBox()
        start_temp_spin.setRange(0.0, 1000.0)
        start_temp_spin.setSingleStep(10.0)
        start_temp_spin.setValue(float(collect_start_temp))
        self.config_widgets['ignition_collect_start_temp'] = start_temp_spin
        layout.addWidget(start_temp_spin, row, 1)
        
        # 说明信息
        info_label = QLabel("说明: 当温控仪表PV值达到此温度时开始采集数据，低于此温度不采集。")
        info_label.setStyleSheet("color: #9e9e9e; padding: 5px 0px; font-size: 9pt;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label, row + 1, 0, 1, 2)
        
        return group
    
    def _create_ignition_detection_group(self):
        """创建着火点判断参数组"""
        group = QGroupBox("着火点判断参数")
        layout = QVBoxLayout(group)
        
        detection_config = self.config['ignition_experiment']['ignition_detection']
        
        # 启用开关
        chk_enabled = QCheckBox("启用着火点检测")
        chk_enabled.setChecked(detection_config['enabled'])
        self.config_widgets['ignition_detection_enabled'] = chk_enabled
        layout.addWidget(chk_enabled)
        
        # 温度突升法
        rise_group = QGroupBox("温度突升法")
        rise_layout = QGridLayout(rise_group)
        
        criteria = detection_config['criteria']['temperature_rise']
        
        chk_rise = QCheckBox("启用")
        chk_rise.setChecked(criteria['enabled'])
        self.config_widgets['ignition_rise_enabled'] = chk_rise
        rise_layout.addWidget(chk_rise, 0, 0, 1, 2)
        
        rise_layout.addWidget(QLabel("温升阈值(°C):"), 1, 0)
        threshold_spin = QDoubleSpinBox()
        threshold_spin.setRange(1.0, 200.0)
        threshold_spin.setValue(float(criteria['threshold']))
        self.config_widgets['ignition_rise_threshold'] = threshold_spin
        rise_layout.addWidget(threshold_spin, 1, 1)
        
        rise_layout.addWidget(QLabel("时间窗口(秒):"), 2, 0)
        window_spin = QDoubleSpinBox()
        window_spin.setRange(0.1, 10.0)
        window_spin.setSingleStep(0.1)
        window_spin.setValue(float(criteria['time_window']))
        self.config_widgets['ignition_rise_window'] = window_spin
        rise_layout.addWidget(window_spin, 2, 1)
        
        layout.addWidget(rise_group)
        
        # # 绝对温度法
        # abs_group = QGroupBox("绝对温度法")
        # abs_layout = QGridLayout(abs_group)
        
        # abs_criteria = detection_config['criteria']['absolute_temperature']
        
        # chk_abs = QCheckBox("启用")
        # chk_abs.setChecked(abs_criteria['enabled'])
        # self.config_widgets['ignition_abs_enabled'] = chk_abs
        # abs_layout.addWidget(chk_abs, 0, 0, 1, 2)
        
        # abs_layout.addWidget(QLabel("温度阈值(°C):"), 1, 0)
        # abs_threshold_spin = QDoubleSpinBox()
        # abs_threshold_spin.setRange(100.0, 1000.0)
        # abs_threshold_spin.setValue(abs_criteria['threshold'])
        # self.config_widgets['ignition_abs_threshold'] = abs_threshold_spin
        # abs_layout.addWidget(abs_threshold_spin, 1, 1)
        
        # layout.addWidget(abs_group)
        
        # 温升速率法
        rate_group = QGroupBox("温升速率法")
        rate_layout = QGridLayout(rate_group)
        
        rate_criteria = detection_config['criteria']['rise_rate']
        
        chk_rate = QCheckBox("启用")
        chk_rate.setChecked(rate_criteria['enabled'])
        self.config_widgets['ignition_rate_enabled'] = chk_rate
        rate_layout.addWidget(chk_rate, 0, 0, 1, 2)
        
        rate_layout.addWidget(QLabel("速率阈值(°C/s):"), 1, 0)
        rate_threshold_spin = QDoubleSpinBox()
        rate_threshold_spin.setRange(0.0, 100.0)
        rate_threshold_spin.setValue(rate_criteria['threshold'])
        self.config_widgets['ignition_rate_threshold'] = rate_threshold_spin
        rate_layout.addWidget(rate_threshold_spin, 1, 1)
        
        layout.addWidget(rate_group)
        
        # 检测参数
        detection_param_layout = QGridLayout()
        
        detection_param_layout.addWidget(QLabel("检测间隔(秒):"), 0, 0)
        check_interval_spin = QDoubleSpinBox()
        check_interval_spin.setRange(0.05, 2.0)
        check_interval_spin.setSingleStep(0.05)
        check_interval_spin.setValue(float(detection_config['check_interval']))
        self.config_widgets['ignition_check_interval'] = check_interval_spin
        detection_param_layout.addWidget(check_interval_spin, 0, 1)
        
        detection_param_layout.addWidget(QLabel("确认时间(秒):"), 1, 0)
        confirm_time_spin = QDoubleSpinBox()
        confirm_time_spin.setRange(0.1, 5.0)
        confirm_time_spin.setSingleStep(0.1)
        confirm_time_spin.setValue(float(detection_config['confirmation_time']))
        self.config_widgets['ignition_confirm_time'] = confirm_time_spin
        detection_param_layout.addWidget(confirm_time_spin, 1, 1)
        
        layout.addLayout(detection_param_layout)
        
        return group
    
    def _create_explosion_config_tab(self):
        """创建爆炸性实验配置标签页"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 串口配置
        serial_group = self._create_explosion_serial_group()
        layout.addWidget(serial_group)
        
        # 实验条件配置
        conditions_group = self._create_control_conditions_group()
        layout.addWidget(conditions_group)
        
        # 实验轮次配置
        rounds_group = self._create_test_rounds_group()
        layout.addWidget(rounds_group)
        
        # 爆炸性评估阈值配置
        thresholds_group = self._create_explosion_thresholds_group()
        layout.addWidget(thresholds_group)
        
        # 相机配置
        camera_group = self._create_camera_group()
        layout.addWidget(camera_group)
        
        # 时序配置
        sequence_group = self._create_sequence_group()
        layout.addWidget(sequence_group)
        
        layout.addStretch()
        
        return scroll
    
    def _create_explosion_serial_group(self):
        """创建爆炸性实验串口配置组"""
        group = QGroupBox("串口配置")
        layout = QGridLayout(group)
        
        row = 0
        serial_config = self.config['explosion_experiment']['serial']
        
        # COM口
        layout.addWidget(QLabel("COM口:"), row, 0)
        port_edit = QLineEdit(serial_config['port'])
        self.config_widgets['explosion_serial_port'] = port_edit
        layout.addWidget(port_edit, row, 1)
        
        row += 1
        # 波特率
        layout.addWidget(QLabel("波特率:"), row, 0)
        baudrate_spin = QSpinBox()
        baudrate_spin.setRange(1200, 115200)
        baudrate_spin.setValue(int(serial_config['baudrate']))
        self.config_widgets['explosion_serial_baudrate'] = baudrate_spin
        layout.addWidget(baudrate_spin, row, 1)
        
        row += 1
        # 超时
        layout.addWidget(QLabel("超时时间(秒):"), row, 0)
        timeout_spin = QDoubleSpinBox()
        timeout_spin.setRange(0.1, 10.0)
        timeout_spin.setSingleStep(0.1)
        timeout_spin.setValue(float(serial_config['timeout']))
        self.config_widgets['explosion_serial_timeout'] = timeout_spin
        layout.addWidget(timeout_spin, row, 1)
        
        return group
    
    def _create_control_conditions_group(self):
        """创建实验条件配置组"""
        group = QGroupBox("实验条件参数")
        layout = QGridLayout(group)
        
        control_conditions = self.config['explosion_experiment']['control_conditions']
        
        # 目标温度配置
        temp_label = QLabel("目标温度:")
        temp_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        layout.addWidget(temp_label, 0, 0, 1, 2)
        
        row = 1
        layout.addWidget(QLabel("  温度值(℃):"), row, 0)
        temp_value_spin = QDoubleSpinBox()
        temp_value_spin.setRange(1000.0, 1150.0)
        temp_value_spin.setSingleStep(10.0)
        temp_value_spin.setValue(float(control_conditions['target_temperature']['value']))
        self.config_widgets['control_temp_value'] = temp_value_spin
        layout.addWidget(temp_value_spin, row, 1)
        
        row += 1
        layout.addWidget(QLabel("  温度容差(℃):"), row, 0)
        temp_tolerance_spin = QDoubleSpinBox()
        temp_tolerance_spin.setRange(1, 5.0)
        temp_tolerance_spin.setSingleStep(1)
        temp_tolerance_spin.setValue(float(control_conditions['target_temperature']['tolerance']))
        self.config_widgets['control_temp_tolerance'] = temp_tolerance_spin
        layout.addWidget(temp_tolerance_spin, row, 1)
        
        # 目标压力配置
        row += 1
        pressure_label = QLabel("目标压力:")
        pressure_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        layout.addWidget(pressure_label, row, 0, 1, 2)
        
        row += 1
        layout.addWidget(QLabel("  压力值(kPa):"), row, 0)
        pressure_value_spin = QDoubleSpinBox()
        pressure_value_spin.setRange(50.0, 200.0)
        pressure_value_spin.setSingleStep(1.0)
        pressure_value_spin.setValue(float(control_conditions['target_pressure']['value']))
        self.config_widgets['control_pressure_value'] = pressure_value_spin
        layout.addWidget(pressure_value_spin, row, 1)
        
        row += 1
        layout.addWidget(QLabel("  压力容差(kPa):"), row, 0)
        pressure_tolerance_spin = QDoubleSpinBox()
        pressure_tolerance_spin.setRange(1, 5.0)
        pressure_tolerance_spin.setSingleStep(1)
        pressure_tolerance_spin.setValue(float(control_conditions['target_pressure']['tolerance']))
        self.config_widgets['control_pressure_tolerance'] = pressure_tolerance_spin
        layout.addWidget(pressure_tolerance_spin, row, 1)
        
        # 说明信息
        row += 1
        info_label = QLabel(
            "说明: 实验开始时，系统会等待温度和压力达到目标值±容差范围内"
        )
        info_label.setStyleSheet("color: #9e9e9e; font-size: 9pt; padding-top: 10px;")
        layout.addWidget(info_label, row, 0, 1, 2)
        
        return group
    
    def _create_test_rounds_group(self):
        """创建实验轮次配置组"""
        group = QGroupBox("实验轮次设置")
        layout = QGridLayout(group)
        
        test_rounds = self.config['explosion_experiment']['test-rounds']
        
        row = 0
        # 最大轮次
        layout.addWidget(QLabel("最大轮次:"), row, 0)
        max_rounds_spin = QSpinBox()
        self.config_widgets['test_max_rounds'] = max_rounds_spin
        layout.addWidget(max_rounds_spin, row, 1)
        
        row += 1
        # 每阶段轮次
        layout.addWidget(QLabel("每阶段轮次:"), row, 0)
        phase_rounds_spin = QSpinBox()
        self.config_widgets['test_phase_rounds'] = phase_rounds_spin
        layout.addWidget(phase_rounds_spin, row, 1)
        
        row += 1
        # Limits describe supported application behavior, not certification.
        info_label = QLabel(
            "说明:\n"
            "• 当前最多支持10轮，阶段轮次不能超过最大轮次\n"
            "• 轮次参数用于定义实验流程，不代表标准符合性结论"
        )
        info_label.setStyleSheet("color: #9e9e9e; font-size: 9pt; padding-top: 10px;")
        layout.addWidget(info_label, row, 0, 1, 2)

        self.rounds_validation_label = QLabel()
        self.rounds_validation_label.setWordWrap(True)
        self.rounds_validation_label.setStyleSheet('color: #ef5350;')
        layout.addWidget(self.rounds_validation_label, row + 1, 0, 1, 2)
        self._load_round_controls(test_rounds)
        max_rounds_spin.valueChanged.connect(self._on_max_rounds_changed)
        phase_rounds_spin.valueChanged.connect(self._on_phase_rounds_changed)
        
        return group

    def _load_round_controls(self, test_rounds):
        """Display invalid legacy values without silently rewriting them."""
        maximum = self.config_widgets['test_max_rounds']
        phase = self.config_widgets['test_phase_rounds']
        maximum_value, phase_value = test_rounds['max-rounds'], test_rounds['phase-rounds']
        if any(not isinstance(value, int) or isinstance(value, bool)
               for value in (maximum_value, phase_value)):
            raise ValueError('实验轮次配置必须是整数')
        blocked = (maximum.blockSignals(True), phase.blockSignals(True))
        try:
            # Invalid saved values are visible for explicit correction. New
            # valid choices immediately restore the supported widget limits.
            maximum.setRange(min(1, maximum_value), max(10, maximum_value))
            maximum.setValue(maximum_value)
            phase.setRange(min(1, phase_value), max(1, min(maximum_value, 10), phase_value))
            phase.setValue(phase_value)
        finally:
            maximum.blockSignals(blocked[0])
            phase.blockSignals(blocked[1])
        self._update_round_validation()

    def _on_max_rounds_changed(self, value):
        if 1 <= value <= 10:
            self.config_widgets['test_max_rounds'].setRange(1, 10)
            self.config_widgets['test_phase_rounds'].setRange(1, value)
        self._update_round_validation()

    def _on_phase_rounds_changed(self, value):
        maximum = self.config_widgets['test_max_rounds'].value()
        if 1 <= value <= maximum <= 10:
            self.config_widgets['test_phase_rounds'].setRange(1, maximum)
        self._update_round_validation()

    def _validate_round_controls(self):
        maximum = self.config_widgets['test_max_rounds'].value()
        phase = self.config_widgets['test_phase_rounds'].value()
        if not 1 <= phase <= maximum <= 10:
            raise ValueError(
                f'实验轮次配置无效：阶段轮次 {phase}，最大轮次 {maximum}；'
                '需要 1 ≤ 阶段轮次 ≤ 最大轮次 ≤ 10，请修正后再保存或应用')

    def _update_round_validation(self):
        try:
            self._validate_round_controls()
            self.rounds_validation_label.clear()
        except ValueError as exc:
            self.rounds_validation_label.setText(str(exc))
    
    def _create_explosion_thresholds_group(self):
        """创建爆炸性评估阈值配置组"""
        group = QGroupBox("爆炸性评估阈值")
        layout = QGridLayout(group)
        
        thresholds = self.config['explosion_experiment']['explosion-thresholds']
        
        row = 0
        # 无爆炸性阈值
        layout.addWidget(QLabel("无爆炸性阈值(mm):"), row, 0)
        no_explosion_spin = QDoubleSpinBox()
        no_explosion_spin.setRange(1.0, 100.0)
        no_explosion_spin.setSingleStep(1.0)
        no_explosion_spin.setValue(thresholds['no-explosion'])
        self.config_widgets['threshold_no_explosion'] = no_explosion_spin
        layout.addWidget(no_explosion_spin, row, 1)
        
        row += 1
        # 弱爆炸性阈值
        layout.addWidget(QLabel("弱爆炸性阈值(mm):"), row, 0)
        weak_explosion_spin = QDoubleSpinBox()
        weak_explosion_spin.setRange(50.0, 600.0)
        weak_explosion_spin.setSingleStep(10.0)
        weak_explosion_spin.setValue(thresholds['weak-explosion'])
        self.config_widgets['threshold_weak_explosion'] = weak_explosion_spin
        layout.addWidget(weak_explosion_spin, row, 1)
        
        row += 1
        # 强爆炸性阈值
        layout.addWidget(QLabel("强爆炸性阈值(mm):"), row, 0)
        strong_explosion_spin = QDoubleSpinBox()
        strong_explosion_spin.setRange(600.0, 1200.0)
        strong_explosion_spin.setSingleStep(10.0)
        strong_explosion_spin.setValue(thresholds['strong-explosion'])
        self.config_widgets['threshold_strong_explosion'] = strong_explosion_spin
        layout.addWidget(strong_explosion_spin, row, 1)
        
        row += 1
        # 说明信息
        info_label = QLabel(
            "说明:\n"
            "• 无爆炸性: < 无爆炸性阈值\n"
            "• 弱爆炸性: 无爆炸性阈值 ~ 弱爆炸性阈值\n"
            "• 强爆炸性: 弱爆炸性阈值 ~ 强爆炸性阈值\n"
            "• 超强爆炸性: ≥ 强爆炸性阈值"
        )
        info_label.setStyleSheet("color: #9e9e9e; font-size: 9pt; padding-top: 10px;")
        layout.addWidget(info_label, row, 0, 1, 2)
        
        return group
    
    def _create_camera_group(self):
        """创建相机配置组"""
        group = QGroupBox("相机配置")
        layout = QGridLayout(group)
        
        camera_config = self.config['explosion_experiment']['camera']
        
        row = 0
        # 启用相机
        chk_camera = QCheckBox("启用相机")
        chk_camera.setChecked(camera_config['enabled'])
        self.config_widgets['camera_enabled'] = chk_camera
        layout.addWidget(chk_camera, row, 0, 1, 2)
        
        row += 1
        # 拍摄时长
        layout.addWidget(QLabel("拍摄时长(秒):"), row, 0)
        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(0.5, 10.0)
        duration_spin.setSingleStep(0.1)
        duration_spin.setValue(float(camera_config['capture_duration']))
        self.config_widgets['camera_duration'] = duration_spin
        layout.addWidget(duration_spin, row, 1)
        
        row += 1
        # 触发延时
        layout.addWidget(QLabel("历史触发延时（未启用）:"), row, 0)
        delay_spin = QDoubleSpinBox()
        delay_spin.setRange(0.0, 5.0)
        delay_spin.setSingleStep(0.1)
        delay_spin.setValue(float(camera_config['trigger_delay']))
        delay_spin.setEnabled(False)
        delay_spin.setToolTip("此历史参数暂不生效。拍摄随喷吹触发，精确同步需现场确认。")
        self.config_widgets['camera_trigger_delay'] = delay_spin
        layout.addWidget(delay_spin, row, 1)
        
        return group
    
    def _create_sequence_group(self):
        """创建时序配置组"""
        group = QGroupBox("时序配置")
        layout = QVBoxLayout(group)
        
        # 关键延时参数配置
        delay_layout = QGridLayout()
        
        # 获取sequence_steps
        sequence_steps = self.config['explosion_experiment']['sequence_steps']
        
        # 找到三个关键延时步骤
        spray_delay = next((s for s in sequence_steps if s['step'] == 2), {})
        wait_delay = next((s for s in sequence_steps if s['step'] == 4), {})
        purge_delay = next((s for s in sequence_steps if s['step'] == 6), {})
        
        row = 0
        # 喷吹延时 (step 2)
        delay_layout.addWidget(QLabel("喷吹延时(秒):"), row, 0)
        spray_delay_spin = QDoubleSpinBox()
        spray_delay_spin.setRange(0.1, 10.0)
        spray_delay_spin.setSingleStep(0.1)
        spray_delay_spin.setValue(float(spray_delay.get('duration', 0.5)))
        self.config_widgets['sequence_spray_delay'] = spray_delay_spin
        delay_layout.addWidget(spray_delay_spin, row, 1)
        
        row += 1
        # 等待延时 (step 4)
        delay_layout.addWidget(QLabel("等待延时(秒):"), row, 0)
        wait_delay_spin = QDoubleSpinBox()
        wait_delay_spin.setRange(0.1, 30.0)
        wait_delay_spin.setSingleStep(0.1)
        wait_delay_spin.setValue(float(wait_delay.get('duration', 3.0)))
        self.config_widgets['sequence_wait_delay'] = wait_delay_spin
        delay_layout.addWidget(wait_delay_spin, row, 1)
        
        row += 1
        # 吹扫延时 (step 6)
        delay_layout.addWidget(QLabel("吹扫延时(秒):"), row, 0)
        purge_delay_spin = QDoubleSpinBox()
        purge_delay_spin.setRange(0.1, 60.0)
        purge_delay_spin.setSingleStep(0.1)
        purge_delay_spin.setValue(float(purge_delay.get('duration', 5.0)))
        self.config_widgets['sequence_purge_delay'] = purge_delay_spin
        delay_layout.addWidget(purge_delay_spin, row, 1)
        
        layout.addLayout(delay_layout)
        
        # 提示信息
        info_label = QLabel(
            "提示: 其他复杂的时序步骤配置请直接编辑配置文件。"
        )
        info_label.setStyleSheet("color: #9e9e9e; padding: 10px; font-size: 9pt;")
        layout.addWidget(info_label)
        
        return group
    
    def _create_general_config_tab(self):
        """创建通用配置标签页"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 界面更新配置
        ui_group = QGroupBox("界面更新配置")
        ui_layout = QGridLayout(ui_group)
        
        row = 0
        ui_layout.addWidget(QLabel("界面更新间隔(毫秒):"), row, 0)
        update_interval_spin = QSpinBox()
        update_interval_spin.setRange(100, 2000)
        update_interval_spin.setSingleStep(100)
        update_interval_spin.setValue(int(self.ui_config['update_interval']))
        self.config_widgets['ui_update_interval'] = update_interval_spin
        ui_layout.addWidget(update_interval_spin, row, 1)
        
        row += 1
        ui_layout.addWidget(QLabel("图表更新间隔(毫秒):"), row, 0)
        chart_interval_spin = QSpinBox()
        chart_interval_spin.setRange(50, 1000)
        chart_interval_spin.setSingleStep(50)
        chart_interval_spin.setValue(int(self.ui_config['chart']['update_interval']))
        self.config_widgets['chart_update_interval'] = chart_interval_spin
        ui_layout.addWidget(chart_interval_spin, row, 1)
        
        row += 1
        ui_layout.addWidget(QLabel("图表最大点数:"), row, 0)
        max_points_spin = QSpinBox()
        max_points_spin.setRange(50, 20000)
        max_points_spin.setSingleStep(50)
        max_points_spin.setValue(int(self.ui_config['chart']['max_points']))
        self.config_widgets['chart_max_points'] = max_points_spin
        ui_layout.addWidget(max_points_spin, row, 1)
        
        layout.addWidget(ui_group)
        
        layout.addStretch()
        
        return scroll
    
    def _get_flame_analyzer_config_path(self):
        """获取火焰分析器配置文件路径"""
        if HAS_PATH_MANAGER:
            return PathManager.get_config_path('flame_analyzer_config.yaml')
        else:
            # 备用方案：使用相对路径
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent
            return os.path.join(project_root, 'configs', 'flame_analyzer_config.yaml')
    
    def _load_flame_analyzer_config(self):
        """加载火焰分析器配置"""
        try:
            config_path = Path(self.flame_analyzer_config_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                # 如果配置文件不存在，返回默认配置
                return {
                    'image_processing': {
                        'flame_threshold': 128,
                        'mm_per_pixel': 0.1
                    }
                }
        except Exception as e:
            QMessageBox.warning(
                self,
                '警告',
                f'加载火焰分析器配置失败: {e}\n将使用默认配置。'
            )
            return {
                'image_processing': {
                    'flame_threshold': 128,
                    'mm_per_pixel': 0.1
                }
            }
    
    def _create_flame_analyzer_config_tab(self):
        """创建火焰分析器配置标签页"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 图像处理参数配置
        image_processing_group = QGroupBox("图像处理参数")
        image_processing_layout = QGridLayout(image_processing_group)
        
        image_processing_config = self.flame_analyzer_config.get('image_processing', {})
        
        row = 0
        # 火焰检测阈值
        image_processing_layout.addWidget(QLabel("火焰检测阈值:"), row, 0)
        threshold_spin = QSpinBox()
        threshold_spin.setRange(0, 255)
        threshold_spin.setValue(int(image_processing_config.get('flame_threshold', 128)))
        self.config_widgets['flame_threshold'] = threshold_spin
        image_processing_layout.addWidget(threshold_spin, row, 1)
        
        # 说明信息
        threshold_info = QLabel("说明: 用于二值化图像，值越大越严格。范围: 0-255")
        threshold_info.setStyleSheet("color: #9e9e9e; padding: 5px 0px; font-size: 9pt;")
        threshold_info.setWordWrap(True)
        image_processing_layout.addWidget(threshold_info, row, 2)
        
        row += 1
        # 每像素对应的毫米数
        image_processing_layout.addWidget(QLabel("像素比例(mm/pixel):"), row, 0)
        mm_per_pixel_spin = QDoubleSpinBox()
        mm_per_pixel_spin.setRange(0.001, 10.0)
        mm_per_pixel_spin.setSingleStep(0.01)
        mm_per_pixel_spin.setDecimals(6)
        mm_per_pixel_spin.setValue(float(image_processing_config.get('mm_per_pixel', 0.1)))
        self.config_widgets['mm_per_pixel'] = mm_per_pixel_spin
        image_processing_layout.addWidget(mm_per_pixel_spin, row, 1)
        
        # 说明信息
        mm_per_pixel_info = QLabel("说明: 用于将像素尺寸转换为实际毫米数。需要根据相机标定设置。")
        mm_per_pixel_info.setStyleSheet("color: #9e9e9e; padding: 5px 0px; font-size: 9pt;")
        mm_per_pixel_info.setWordWrap(True)
        image_processing_layout.addWidget(mm_per_pixel_info, row, 2)
        
        layout.addWidget(image_processing_group)
        
        layout.addStretch()
        
        return scroll
    
    def _on_reset(self):
        """重置为默认值"""
        reply = QMessageBox.question(
            self,
            '确认重置',
            '确定要重置所有配置为默认值吗？\n未保存的更改将丢失。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 重新加载实验配置文件
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                
                # 重新加载火焰分析器配置
                self.flame_analyzer_config = self._load_flame_analyzer_config()
                
                # 更新所有控件
                self._update_widgets_from_config()
                
                QMessageBox.information(self, "成功", "配置已重置为默认值")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置配置失败:\n{e}")
    
    def _on_save(self):
        """保存配置到文件"""
        try:
            # 更新配置字典
            self._update_config_from_widgets()
            
            # 保存实验配置到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    {
                        'ignition_experiment': self.config['ignition_experiment'],
                        'explosion_experiment': self.config['explosion_experiment'],
                        'ui': self.ui_config
                    },
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            # 保存火焰分析器配置
            self._save_flame_analyzer_config()
            
            QMessageBox.information(self, "成功", "配置已保存到文件")
            
            # 发射配置更新信号
            self.config_updated.emit(self.config)
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败:\n{e}")
    
    def _on_apply(self):
        """应用配置（不保存到文件）"""
        try:
            # 更新配置字典
            self._update_config_from_widgets()
            
            # 注意：应用时也更新火焰分析器配置到内存，但不保存到文件
            # 这样在应用后，如果用户再次打开火焰分析器，会使用新的配置
            
            QMessageBox.information(
                self,
                "成功",
                "配置已应用到当前会话\n注意: 配置未保存到文件"
            )
            
            # 发射配置更新信号
            self.config_updated.emit(self.config)
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用配置失败:\n{e}")
    
    def _update_widgets_from_config(self):
        """从配置更新控件"""
        # 着火点串口
        serial_config = self.config['ignition_experiment']['serial']
        self.config_widgets['ignition_serial_port'].setText(serial_config['port'])
        self.config_widgets['ignition_serial_baudrate'].setValue(int(serial_config['baudrate']))
        self.config_widgets['ignition_serial_timeout'].setValue(float(serial_config['timeout']))
        
        # 数据采集配置
        collect_start_temp = self.config['ignition_experiment'].get('collect_start_temperature', 200.0)
        self.config_widgets['ignition_collect_start_temp'].setValue(float(collect_start_temp))
        
        # 着火点检测
        detection_config = self.config['ignition_experiment']['ignition_detection']
        self.config_widgets['ignition_detection_enabled'].setChecked(detection_config['enabled'])
        
        criteria = detection_config['criteria']
        self.config_widgets['ignition_rise_enabled'].setChecked(criteria['temperature_rise']['enabled'])
        self.config_widgets['ignition_rise_threshold'].setValue(float(criteria['temperature_rise']['threshold']))
        self.config_widgets['ignition_rise_window'].setValue(float(criteria['temperature_rise']['time_window']))
        
        # self.config_widgets['ignition_abs_enabled'].setChecked(criteria['absolute_temperature']['enabled'])
        # self.config_widgets['ignition_abs_threshold'].setValue(float(criteria['absolute_temperature']['threshold']))
        
        self.config_widgets['ignition_rate_enabled'].setChecked(criteria['rise_rate']['enabled'])
        self.config_widgets['ignition_rate_threshold'].setValue(float(criteria['rise_rate']['threshold']))
        
        self.config_widgets['ignition_check_interval'].setValue(float(detection_config['check_interval']))
        self.config_widgets['ignition_confirm_time'].setValue(float(detection_config['confirmation_time']))
        
        # 爆炸性串口
        explosion_serial = self.config['explosion_experiment']['serial']
        self.config_widgets['explosion_serial_port'].setText(explosion_serial['port'])
        self.config_widgets['explosion_serial_baudrate'].setValue(int(explosion_serial['baudrate']))
        self.config_widgets['explosion_serial_timeout'].setValue(float(explosion_serial['timeout']))
        
        # 实验条件
        control_conditions = self.config['explosion_experiment']['control_conditions']
        self.config_widgets['control_temp_value'].setValue(float(control_conditions['target_temperature']['value']))
        self.config_widgets['control_temp_tolerance'].setValue(float(control_conditions['target_temperature']['tolerance']))
        self.config_widgets['control_pressure_value'].setValue(float(control_conditions['target_pressure']['value']))
        self.config_widgets['control_pressure_tolerance'].setValue(float(control_conditions['target_pressure']['tolerance']))
        
        # 实验轮次
        test_rounds = self.config['explosion_experiment']['test-rounds']
        self._load_round_controls(test_rounds)
        
        # 爆炸性评估阈值
        thresholds = self.config['explosion_experiment']['explosion-thresholds']
        self.config_widgets['threshold_no_explosion'].setValue(thresholds['no-explosion'])
        self.config_widgets['threshold_weak_explosion'].setValue(thresholds['weak-explosion'])
        self.config_widgets['threshold_strong_explosion'].setValue(thresholds['strong-explosion'])
        
        # 相机
        camera_config = self.config['explosion_experiment']['camera']
        self.config_widgets['camera_enabled'].setChecked(camera_config['enabled'])
        self.config_widgets['camera_duration'].setValue(float(camera_config['capture_duration']))
        self.config_widgets['camera_trigger_delay'].setValue(float(camera_config['trigger_delay']))
        
        # 时序延时
        sequence_steps = self.config['explosion_experiment']['sequence_steps']
        spray_delay = next((s for s in sequence_steps if s['step'] == 2), {})
        wait_delay = next((s for s in sequence_steps if s['step'] == 4), {})
        purge_delay = next((s for s in sequence_steps if s['step'] == 6), {})
        
        self.config_widgets['sequence_spray_delay'].setValue(float(spray_delay.get('duration', 0.5)))
        self.config_widgets['sequence_wait_delay'].setValue(float(wait_delay.get('duration', 3.0)))
        self.config_widgets['sequence_purge_delay'].setValue(float(purge_delay.get('duration', 5.0)))
        
        # UI
        self.config_widgets['ui_update_interval'].setValue(int(self.ui_config['update_interval']))
        self.config_widgets['chart_update_interval'].setValue(int(self.ui_config['chart']['update_interval']))
        self.config_widgets['chart_max_points'].setValue(int(self.ui_config['chart']['max_points']))
        
        # 火焰分析器配置
        image_processing_config = self.flame_analyzer_config.get('image_processing', {})
        if 'flame_threshold' in self.config_widgets:
            self.config_widgets['flame_threshold'].setValue(int(image_processing_config.get('flame_threshold', 128)))
        if 'mm_per_pixel' in self.config_widgets:
            self.config_widgets['mm_per_pixel'].setValue(float(image_processing_config.get('mm_per_pixel', 0.1)))
    
    def _update_config_from_widgets(self):
        """从控件更新配置"""
        # Reject before mutating the shared configuration or opening its file.
        self._validate_round_controls()
        # 着火点串口
        self.config['ignition_experiment']['serial']['port'] = self.config_widgets['ignition_serial_port'].text()
        self.config['ignition_experiment']['serial']['baudrate'] = self.config_widgets['ignition_serial_baudrate'].value()
        self.config['ignition_experiment']['serial']['timeout'] = self.config_widgets['ignition_serial_timeout'].value()
        
        # 数据采集配置
        self.config['ignition_experiment']['collect_start_temperature'] = self.config_widgets['ignition_collect_start_temp'].value()
        
        # 着火点检测
        self.config['ignition_experiment']['ignition_detection']['enabled'] = self.config_widgets['ignition_detection_enabled'].isChecked()
        
        criteria = self.config['ignition_experiment']['ignition_detection']['criteria']
        criteria['temperature_rise']['enabled'] = self.config_widgets['ignition_rise_enabled'].isChecked()
        criteria['temperature_rise']['threshold'] = self.config_widgets['ignition_rise_threshold'].value()
        criteria['temperature_rise']['time_window'] = self.config_widgets['ignition_rise_window'].value()
        
        # criteria['absolute_temperature']['enabled'] = self.config_widgets['ignition_abs_enabled'].isChecked()
        # criteria['absolute_temperature']['threshold'] = self.config_widgets['ignition_abs_threshold'].value()
        
        criteria['rise_rate']['enabled'] = self.config_widgets['ignition_rate_enabled'].isChecked()
        criteria['rise_rate']['threshold'] = self.config_widgets['ignition_rate_threshold'].value()
        
        self.config['ignition_experiment']['ignition_detection']['check_interval'] = self.config_widgets['ignition_check_interval'].value()
        self.config['ignition_experiment']['ignition_detection']['confirmation_time'] = self.config_widgets['ignition_confirm_time'].value()
        
        # 爆炸性串口
        self.config['explosion_experiment']['serial']['port'] = self.config_widgets['explosion_serial_port'].text()
        self.config['explosion_experiment']['serial']['baudrate'] = self.config_widgets['explosion_serial_baudrate'].value()
        self.config['explosion_experiment']['serial']['timeout'] = self.config_widgets['explosion_serial_timeout'].value()
        
        # 实验条件
        self.config['explosion_experiment']['control_conditions']['target_temperature']['value'] = self.config_widgets['control_temp_value'].value()
        self.config['explosion_experiment']['control_conditions']['target_temperature']['tolerance'] = self.config_widgets['control_temp_tolerance'].value()
        self.config['explosion_experiment']['control_conditions']['target_pressure']['value'] = self.config_widgets['control_pressure_value'].value()
        self.config['explosion_experiment']['control_conditions']['target_pressure']['tolerance'] = self.config_widgets['control_pressure_tolerance'].value()
        
        # 实验轮次
        self.config['explosion_experiment']['test-rounds']['max-rounds'] = self.config_widgets['test_max_rounds'].value()
        self.config['explosion_experiment']['test-rounds']['phase-rounds'] = self.config_widgets['test_phase_rounds'].value()
        
        # 爆炸性评估阈值
        self.config['explosion_experiment']['explosion-thresholds']['no-explosion'] = self.config_widgets['threshold_no_explosion'].value()
        self.config['explosion_experiment']['explosion-thresholds']['weak-explosion'] = self.config_widgets['threshold_weak_explosion'].value()
        self.config['explosion_experiment']['explosion-thresholds']['strong-explosion'] = self.config_widgets['threshold_strong_explosion'].value()
        
        # 相机
        self.config['explosion_experiment']['camera']['enabled'] = self.config_widgets['camera_enabled'].isChecked()
        self.config['explosion_experiment']['camera']['capture_duration'] = self.config_widgets['camera_duration'].value()
        self.config['explosion_experiment']['camera']['trigger_delay'] = self.config_widgets['camera_trigger_delay'].value()
        
        # 时序延时
        sequence_steps = self.config['explosion_experiment']['sequence_steps']
        for step in sequence_steps:
            if step['step'] == 2:  # 喷吹延时
                step['duration'] = self.config_widgets['sequence_spray_delay'].value()
            elif step['step'] == 4:  # 等待延时
                step['duration'] = self.config_widgets['sequence_wait_delay'].value()
            elif step['step'] == 6:  # 吹扫延时
                step['duration'] = self.config_widgets['sequence_purge_delay'].value()
        
        # UI
        self.ui_config['update_interval'] = self.config_widgets['ui_update_interval'].value()
        self.ui_config['chart']['update_interval'] = self.config_widgets['chart_update_interval'].value()
        self.ui_config['chart']['max_points'] = self.config_widgets['chart_max_points'].value()
        
        # 火焰分析器配置
        if 'flame_threshold' in self.config_widgets and 'mm_per_pixel' in self.config_widgets:
            if 'image_processing' not in self.flame_analyzer_config:
                self.flame_analyzer_config['image_processing'] = {}
            self.flame_analyzer_config['image_processing']['flame_threshold'] = self.config_widgets['flame_threshold'].value()
            self.flame_analyzer_config['image_processing']['mm_per_pixel'] = self.config_widgets['mm_per_pixel'].value()
    
    def _save_flame_analyzer_config(self):
        """保存火焰分析器配置到文件"""
        try:
            # 确保目录存在
            config_path = Path(self.flame_analyzer_config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有配置（保留其他配置项）
            existing_config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 合并配置（保留其他配置项，只更新image_processing）
            merged_config = existing_config.copy()
            merged_config['image_processing'] = self.flame_analyzer_config.get('image_processing', {})
            
            # 保存到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    merged_config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            print(f"火焰分析器配置已保存到: {config_path}")
        
        except Exception as e:
            QMessageBox.warning(
                self,
                '警告',
                f'保存火焰分析器配置失败: {e}\n配置将在应用时生效，但不会保存到文件。'
            )
