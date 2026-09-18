#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验控制器
负责着火点实验的业务逻辑和流程控制
"""

import logging
import threading
import json
import math
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer, Qt, Slot

from modbus_multi_device import ModbusDeviceManager
from models.ignition_database import IgnitionDatabase
from models.experiment_states import IgnitionExperimentState
from utils.path_manager import PathManager


class IgnitionController(QObject):
    """着火点实验控制器"""
    
    # 信号定义
    device_connected = Signal(bool, str)  # (成功/失败, 消息)
    experiment_created = Signal(dict)  # 实验配置
    experiment_started = Signal()  # 实验开始
    experiment_stopped = Signal()  # 实验停止
    status_updated = Signal(str)  # 状态更新
    log_message = Signal(str)  # 日志消息
    
    # 监控面板订阅信号
    control_temp_controller_updated = Signal(dict)  # 温控器数据更新 {pv, sv, mv, status}
    sample_temps_updated = Signal(list)  # 样品温度更新 [t1, t2, t3, t4, t5, t6]
    state_changed = Signal(str)  # 实验状态变化
    ignition_detected = Signal(float, list)  # 着火检测 (着火温度, 样品温度列表)
    device_status_changed = Signal(str, bool)  # 设备状态变化 (设备名, 在线状态)
    
    def __init__(self, config=None, parent=None):
        """
        初始化控制器
        
        Args:
            config: 实验配置
            parent: 父对象
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # 通道数量（从配置读取，默认6）
        _sample_channels = self.config.get('ignition_detection', {}).get('sample_channels', list(range(6)))
        self.num_channels = len(_sample_channels)

        # 设备管理器
        self.manager = None
        
        # 数据库
        self.db = IgnitionDatabase(PathManager.get_data_path("ignition_experiment.db"))

        # 实验状态
        self.is_running = False
        self.current_session_id = None
        self.current_experiment_config = None
        self._last_saved_sample_ids = None
        self._shutdown_prepared = False
        self._connect_thread = None
        self._closing = False
        
        # 数据监控定时器（用于副屏实时数据推送）
        self.data_monitor_timer = QTimer(self)
        self.data_monitor_timer.timeout.connect(self._poll_device_data)
        self.data_monitor_timer.setInterval(500)  # 500ms更新一次
        self.device_connected.connect(self._on_devices_connected, Qt.QueuedConnection)
        
        # 当前实验状态（使用枚举）
        self.current_state = IgnitionExperimentState.IDLE
        
        # 着火检测
        self.ignition_threshold = 500.0  # 着火温度阈值（可配置）
        self.ignited_samples = [False] * self.num_channels  # 记录每个样品是否已着火
    
    def connect_devices(self):
        """连接设备（在后台线程中执行）"""
        if self._connect_thread is not None and self._connect_thread.is_alive():
            return
        self._closing = False
        self.log_message.emit("正在连接设备...")
        self._connect_thread = threading.Thread(target=self._execute_connect, daemon=True)
        self._connect_thread.start()
    
    def _execute_connect(self):
        """执行设备连接（后台线程）"""
        try:
            if self.current_session_id is not None:
                self.log_message.emit("✗ 请先结束当前实验会话")
                return False
            self._shutdown_prepared = False
            # 创建设备管理器
            if self.manager is None:
                self.manager = ModbusDeviceManager(config_dict=self.config)
            
            # 执行连接
            if self.manager.connect():
                # 保留命令执行器，退出流程必须确认温控停止后才能断开串口。
                self.manager.start()
                if self._closing:
                    return
                
                # 更新状态
                self._set_state(IgnitionExperimentState.CONNECTED)
                
                self.device_connected.emit(True, "设备连接成功")
                self.logger.info("设备连接成功")
                self.log_message.emit("✓ 设备连接成功")
            else:
                self.device_connected.emit(False, "设备连接失败")
                self.logger.error("设备连接失败")
                self.log_message.emit("✗ 设备连接失败")
        
        except Exception as e:
            self.device_connected.emit(False, f"连接异常: {e}")
            self.logger.error(f"设备连接异常: {e}")
            self.log_message.emit(f"✗ 设备连接异常: {e}")
    
    @Slot(bool, str)
    def _on_devices_connected(self, success, message):
        if success and not self._closing:
            self.start_data_monitoring()

    def create_experiment(self, config: dict):
        """
        创建实验会话
        
        Args:
            config: 实验配置，包含：
                - experiment_name: 实验名称
                - sample_names: 样品名称列表
                - client: 客户
                - operator: 操作员
                - description: 描述
        
        Returns:
            bool: 创建是否成功
        """
        try:
            if self.current_session_id is not None:
                self.log_message.emit("✗ 请先结束当前实验会话")
                return False
            self._shutdown_prepared = False
            # 如果当前是COMPLETED或STOPPED状态，先转换到CONNECTED
            if self.current_state in {IgnitionExperimentState.COMPLETED, IgnitionExperimentState.STOPPED, IgnitionExperimentState.CANCELLED}:
                self._set_state(IgnitionExperimentState.CONNECTED)
                self.logger.debug(f"状态转换: {self.current_state.value} -> CONNECTED (准备创建新实验)")
            
            # 创建数据库会话
            # 将 sample_names 列表序列化为 JSON 字符串
            sample_names = config['sample_names']
            if isinstance(sample_names, list):
                sample_names = json.dumps(sample_names)
            
            session_id = self.db.start_experiment_session(
                experiment_id=config.get('experiment_id'),
                experiment_name=config['experiment_name'],
                sample_names=sample_names,
                client=config['client'],
                operator=config['operator'],
                description=config['description']
            )
            
            if session_id > 0:
                self.current_session_id = session_id
                self.current_experiment_config = config
                
                # 更新状态
                self._set_state(IgnitionExperimentState.PREPARED)
                
                self.log_message.emit(f"✓ 实验已创建: {config.get('experiment_id', '未知')}")
                self.log_message.emit(f"  会话ID: {session_id}")
                self.experiment_created.emit(config)
                self.logger.info(f"实验已创建: {config.get('experiment_id')}, 会话ID: {session_id}")
                return True
            else:
                self.log_message.emit("✗ 创建实验失败")
                self.logger.error("创建实验会话失败")
                return False
                
        except Exception as e:
            self.log_message.emit(f"✗ 创建实验异常: {e}")
            self.logger.error(f"创建实验异常: {e}")
            return False
    
    def start_experiment(self):
        """
        启动实验
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 检查前提条件
            if self.current_session_id is None:
                self.log_message.emit("✗ 请先新建实验！")
                return False
            
            if not self.manager:
                self.log_message.emit("✗ 设备未连接！")
                return False
            
            controller_data = self.manager.get_latest_data('着火点-温控仪表') or {}
            sample_data = self.manager.get_latest_data('着火点-温度模块') or {}
            channels = sample_data.get('channels') or []
            if (not self._valid_temperature(controller_data.get('pv'))
                    or len(channels) < 6
                    or not all(isinstance(channel, dict) and self._valid_temperature(channel.get('temperature')) for channel in channels[:6])):
                self.log_message.emit("✗ 请等待所有温度设备提供有效实时数据")
                return False
            # 检查状态转换是否合法
            if not self.current_state.can_start():
                self.log_message.emit(f"✗ 当前状态不允许启动实验: {self.current_state.description()}")
                return False
            
            # 确保设备管理器已启动（如果连接时已启动，这里不会重复启动）
            if not self.manager.started:
                self.manager.start()
            
            # 确保数据监控已启动（如果连接时已启动，这里不会重复启动）
            if not self.data_monitor_timer.isActive():
                self.start_data_monitoring()
            
            self.log_message.emit("启动实验...")
            
            # 更新会话状态
            if not self.db.update_session(self.current_session_id, status="running"):
                self.log_message.emit("✗ 无法保存实验启动状态")
                return False
            self._set_state(IgnitionExperimentState.RUNNING)
            self.log_message.emit(f"✓ 实验会话已启动 (ID: {self.current_session_id})")
            
            # 更新运行标志
            self.is_running = True
            self.experiment_started.emit()
            
            # 重置着火检测状态
            self.ignited_samples = [False] * self.num_channels
            
            exp_id = self.current_experiment_config.get('experiment_id', '未知')
            self.status_updated.emit(self.current_state.display_text() + f" ({exp_id})")
            self.log_message.emit("✓ 实验已启动")
            self.logger.info(f"实验已启动: {exp_id}")
            
            return True
        
        except Exception as e:
            self.log_message.emit(f"✗ 启动失败: {e}")
            self.logger.error(f"启动实验失败: {e}")
            return False
    
    def stop_experiment(self):
        """
        停止实验
        
        设计说明:
        --------
        停止实验时，只更新实验状态 (is_running = False)，不停止以下组件：
        - 不停止设备管理器 (manager.stop())
        - 不停止数据监控定时器 (data_monitor_timer.stop())
        
        设计理由:
        --------
        1. 设备仍然连接，用户可能需要继续查看实时数据
        2. 副屏实时显示需要持续更新
        3. 只有在断开设备连接或系统清理时才停止设备管理器和数据监控
        
        数据写入控制:
        ------------
        - collect_data() 方法会检查 is_running 标志
        - is_running = False 后，collect_data() 会提前返回，不再写入数据库
        - 从而实现"停止数据写入"但"保持实时显示"的效果
        
        生命周期管理:
        ------------
        - 设备管理器启动: connect_devices() -> _execute_connect()
        - 数据监控启动: connect_devices() -> start_data_monitoring()
        - 设备管理器停止: cleanup() -> manager.stop()
        - 数据监控停止: cleanup() -> data_monitor_timer.stop()
        
        Returns:
            bool: 停止是否成功
        """
        if not self.is_running:
            return False
        
        # 检查状态转换是否合法
        if not self.current_state.can_stop():
            self.log_message.emit(f"✗ 当前状态不允许停止实验: {self.current_state.description()}")
            return False
        
        try:
            self.log_message.emit("停止实验...")
            
            # 更新状态
            self._set_state(IgnitionExperimentState.STOPPED)
            
            # 注意：停止实验时不结束数据库会话
            # 数据库会话只在完成实验时才结束（在页面的_finalize_experiment_internal中处理）
            # 这样可以允许用户在停止后继续查看数据，或完成实验后重置
            
            # 更新运行标志（关键：阻止数据写入）
            self.is_running = False
            self.experiment_stopped.emit()
            
            # 注意：设备管理器和数据监控定时器继续运行
            # 它们将在 cleanup() 方法中停止
            
            exp_id = self.current_experiment_config.get('experiment_id', '未知') if self.current_experiment_config else '未知'
            self.status_updated.emit(self.current_state.display_text() + f" ({exp_id})")
            self.log_message.emit("✓ 实验已停止（设备继续运行，实时数据继续更新）")
            self.log_message.emit("提示：点击'完成实验'按钮可以重置实验状态，创建新的实验会话")
            self.logger.info(f"实验已停止: {exp_id}")
            
            return True
        
        except Exception as e:
            self.log_message.emit(f"✗ 停止失败: {e}")
            self.logger.error(f"停止实验失败: {e}")
            return False
    
    def reset_session(self):
        """
        重置实验会话状态（完成实验后调用）
        
        说明:
        - 清空会话ID和实验配置
        - 重置运行标志
        - 重置着火检测状态
        - 不影响设备管理器和数据监控（继续运行）
        """
        self.current_session_id = None
        self.current_experiment_config = None
        self.is_running = False
        self.ignited_samples = [False] * self.num_channels
        self._last_saved_sample_ids = None
        self.logger.info("实验会话已重置")

    def finalize_experiment(self):
        """Persist successful or failed acquisition before releasing its session."""
        if self.current_session_id is None or self.current_state not in {
            IgnitionExperimentState.STOPPED, IgnitionExperimentState.ERROR,
        }:
            return False
        failed = self.current_state == IgnitionExperimentState.ERROR
        if self.manager is not None and self.manager.started:
            if not self.manager.shutdown_control(
                '着火点-温控仪表', {'set_run_status': {'status': 'StoP'}},
            ):
                self.log_message.emit("✗ 温控器停止未确认，当前会话已保留")
                return False
        if not self.db.end_experiment_session(self.current_session_id, status="error" if failed else "completed"):
            return False
        self._set_state(IgnitionExperimentState.CANCELLED if failed else IgnitionExperimentState.COMPLETED)
        self.reset_session()
        if self.manager is not None and self.manager.started:
            self.manager.resume_controls('着火点-温控仪表')
        return True
    
    def control_temperature_controller(self, action: str):
        """
        控制温控仪表
        
        Args:
            action: 控制动作，如 'run', 'StoP'
        
        Returns:
            bool: 控制是否成功
        """
        if not self.manager or not self.manager.started:
            self.log_message.emit("✗ 设备管理器未启动")
            return False
        
        try:
            self._shutdown_prepared = False
            success = self.manager.send_control_and_wait(
                device_name='着火点-温控仪表',
                control_data={'set_run_status': {'status': action}},
            )
            if not success:
                self.log_message.emit(f"✗ 温控器未确认执行: {action}")
                return False
            self.log_message.emit(f"温控器已执行: {action}")
            self.logger.info(f"控制温控器: {action}")
            return True
        except Exception as e:
            self.log_message.emit(f"✗ 控制失败: {e}")
            self.logger.error(f"控制温控器失败: {e}")
            return False
    
    def set_temperature_program(self, segments: list) -> bool:
        """
        设置温控曲线程序段
        
        Args:
            segments: 程序段列表 [[温度, 时间], ...]
        
        Returns:
            bool: 设置是否成功
        """
        if not self.manager or not self.manager.started:
            self.log_message.emit("✗ 设备管理器未启动")
            return False
        
        try:
            self.log_message.emit(f"正在设置温控曲线 ({len(segments)}个程序段)...")
            self.logger.info(f"开始设置温控曲线: {segments}")
            
            # 发送命令前记录详细信息
            for i, (temp, time_val) in enumerate(segments):
                self.log_message.emit(f"  程序段{i+1}: 温度={temp}°C, 时间={time_val}分钟")
            
            self._shutdown_prepared = False
            success = self.manager.send_control_and_wait(
                device_name='着火点-温控仪表',
                control_data={
                    'set_program_segments': {
                        'segments': segments
                    }
                },
                timeout=30.0,
            )
            if not success:
                self.log_message.emit("✗ 温控曲线未确认写入，请检查设备")
                return False
            self.log_message.emit("✓ 温控曲线已写入并确认")
            self.logger.info(f"温控曲线设置完成: {segments}")
            return True
        except Exception as e:
            self.log_message.emit(f"✗ 设置温控曲线失败: {e}")
            self.logger.error(f"设置温控曲线失败: {e}")
            return False
    
    def collect_data(self):
        """
        采集并保存实验数据
        
        数据采集条件:
        1. 实验必须处于运行状态 (is_running == True)
        2. 实验会话必须存在 (current_session_id is not None)
        3. 炉温必须达到采集起始温度 (pv >= collect_start_temperature)
        4. 炉温必须低于停止温度 (pv < collect_stop_temperature, 默认500℃)
        
        自动停止条件:
        - 当PV >= 500℃时，无论是否检测到着火点，都会自动停止数据采集
        
        Returns:
            bool: 采集是否成功
        """
        # 条件1: 检查实验状态和会话
        if not self.manager or not self.is_running or self.current_session_id is None:
            return False
        
        try:
            # 读取温度数据
            controller_data = self.manager.get_latest_data('着火点-温控仪表')
            temp_module_data = self.manager.get_latest_data('着火点-温度模块')
            
            if not controller_data or not temp_module_data:
                self._fail_acquisition("设备数据已失效，采集已停止，请检查连接")
                return False
            
            pv = controller_data.get('pv')
            if not self._valid_temperature(pv):
                self._fail_acquisition("炉温数据无效，采集已停止")
                return False
            
            # 条件2: 检查温度上限（自动停止条件）
            collect_end_temp = self.config.get('collect_end_temperature', 500.0)
            if pv >= collect_end_temp:
                # PV达到500℃，自动停止数据采集
                if self.is_running:  # 避免重复触发
                    self.log_message.emit("=" * 50)
                    self.log_message.emit(f"⚠ 炉温已达到 {pv:.1f}°C，自动停止数据采集")
                    self.log_message.emit("提示：数据采集已停止，可以点击'完成实验'按钮完成实验")
                    self.log_message.emit("=" * 50)
                    # 自动停止实验（直接更新状态和标志，避免状态检查失败）
                    try:
                        # 更新状态为STOPPED
                        if self.current_state == IgnitionExperimentState.RUNNING:
                            self._set_state(IgnitionExperimentState.STOPPED)
                        
                        # 更新运行标志（关键：阻止数据写入）
                        self.is_running = False
                        
                        # 发送停止信号
                        self.experiment_stopped.emit()
                        
                        # 更新状态显示
                        exp_id = self.current_experiment_config.get('experiment_id', '未知') if self.current_experiment_config else '未知'
                        self.status_updated.emit(self.current_state.display_text() + f" ({exp_id})")
                        
                        self.logger.info(f"自动停止数据采集: PV={pv:.1f}°C >= {collect_end_temp}°C")
                    except Exception as e:
                        self.log_message.emit(f"✗ 自动停止失败: {e}")
                        self.logger.error(f"自动停止数据采集失败: {e}")
                return False  # 不再采集数据
            
            # 条件3: 检查温度下限（采集起始条件）
            collect_start_temp = self.config.get('collect_start_temperature', 200.0)
            if pv < collect_start_temp:
                return False  # 温度未达到，不采集
            
            channels = temp_module_data.get('channels') or []
            
            temperatures = [channel.get('temperature') if isinstance(channel, dict) else None for channel in channels[:6]]
            if len(temperatures) != 6 or not all(self._valid_temperature(value) for value in temperatures):
                self._fail_acquisition("温度通道数据不完整或无效，采集已停止")
                return False

            sample_ids = (controller_data.get('sample_id'), temp_module_data.get('sample_id'))
            if not all(isinstance(value, int) and value > 0 for value in sample_ids):
                self._fail_acquisition("缺少有效采样标识，采集已停止")
                return False
            if self._last_saved_sample_ids is not None and any(
                current <= previous for current, previous in zip(sample_ids, self._last_saved_sample_ids)
            ):
                return False
            
            # 写入数据库（关联会话ID）
            record_id = self.db.insert_ignition_data(
                pv, *temperatures,
                session_id=self.current_session_id  # 关联会话
            )
            
            if record_id > 0:
                self._last_saved_sample_ids = sample_ids
                self.logger.debug(f"数据已写入数据库 (ID: {record_id}, Session: {self.current_session_id})")
                return True
            else:
                self._fail_acquisition("数据写入失败，采集已停止")
                return False
                
        except Exception as e:
            self._fail_acquisition(f"采集数据失败: {e}")
            self.logger.error(f"采集数据失败: {e}")
            return False

    @staticmethod
    def _valid_temperature(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def _fail_acquisition(self, message):
        self.is_running = False
        self._set_state(IgnitionExperimentState.ERROR)
        self.log_message.emit(f"✗ {message}")
        self.experiment_stopped.emit()
        if self.db and self.current_session_id is not None:
            self.db.update_session(self.current_session_id, status="error")
    
    def get_latest_controller_data(self):
        """
        获取最新的温控器数据
        
        Returns:
            dict or None: 温控器数据
        """
        if not self.manager:
            return None
        return self.manager.get_latest_data('着火点-温控仪表')
    
    def get_latest_temperature_data(self):
        """
        获取最新的温度模块数据
        
        Returns:
            dict or None: 温度数据
        """
        if not self.manager:
            return None
        return self.manager.get_latest_data('着火点-温度模块')
    
    def generate_experiment_id(self):
        """
        生成实验编号：IGN-YYYYMMDD--HHMMSS
        
        Returns:
            str: 实验编号
        """
        # today = datetime.now().strftime("%Y%m%d")
        # prefix = f"IGN-{today}"
        
        # # 查询今天已有的实验数量
        # sessions = self.db.get_all_experiment_sessions()
        # today_count = sum(1 for s in sessions if s['experiment_name'] and s['experiment_name'].startswith(prefix))
        # experiment_id = f"{prefix}-{today_count + 1:03d}"
        
        return f"IGN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def get_experiment_status(self):
        """
        获取实验状态
        
        Returns:
            dict: 实验状态信息
        """
        return {
            'is_running': self.is_running,
            'session_id': self.current_session_id,
            'experiment_config': self.current_experiment_config,
            'device_connected': self.manager is not None and hasattr(self.manager, 'started')
        }
    
    def start_data_monitoring(self):
        """启动数据监控（用于副屏实时数据推送）"""
        if not self.data_monitor_timer.isActive():
            self.data_monitor_timer.start()
            self.logger.info("数据监控已启动")
    
    def stop_data_monitoring(self):
        """停止数据监控"""
        if self.data_monitor_timer.isActive():
            self.data_monitor_timer.stop()
            self.logger.info("数据监控已停止")
    
    def _poll_device_data(self):
        """定时轮询设备数据并发送信号（供副屏订阅）"""
        if not self.manager:
            return
        
        try:
            # 获取温控器数据
            temp_data = self.get_latest_controller_data()
            if temp_data:
                pv = temp_data.get('pv', 0.0)
                sv = temp_data.get('sv', 0.0)
                mv = temp_data.get('mv', 0.0)
                status = '在线' if pv is not None else '离线'
                
                self.control_temp_controller_updated.emit({
                    'pv': pv,
                    'sv': sv,
                    'mv': mv,
                    'status': status
                })
            
            # 获取样品温度数据
            temp_module_data = self.get_latest_temperature_data()
            if temp_module_data:
                channels = temp_module_data.get('channels') or []
                # 先构建完整的样品温度快照，避免在循环中途发出不完整的列表
                sample_temps = []
                for i in range(self.num_channels):
                    if i < len(channels):
                        channel = channels[i]
                        value = channel.get('temperature') if isinstance(channel, dict) else None
                        sample_temps.append(value if self._valid_temperature(value) else None)
                    else:
                        sample_temps.append(None)

                # 在完整快照上进行着火检测
                for i, temp in enumerate(sample_temps):
                    if self.is_running and temp is not None and temp >= self.ignition_threshold and not self.ignited_samples[i]:
                        self.ignited_samples[i] = True
                        self.ignition_detected.emit(self.ignition_threshold, list(sample_temps))
                        self.logger.info(f"检测到样品{i+1}着火: {temp}°C")

                self.sample_temps_updated.emit(sample_temps)
            
        except Exception as e:
            self.logger.error(f"轮询设备数据失败: {e}")
    
    def _set_state(self, new_state: IgnitionExperimentState):
        """
        设置实验状态（带转换验证）
        
        Args:
            new_state: 新状态枚举值
        """
        if self.current_state != new_state:
            # 验证状态转换是否合法
            if not self.current_state.can_transition_to(new_state):
                self.logger.warning(
                    f"非法状态转换: {self.current_state.value} -> {new_state.value}"
                )
                return
            
            old_state = self.current_state
            self.current_state = new_state
            self.state_changed.emit(new_state.value)
            self.logger.debug(f"状态变化: {old_state.value} -> {new_state.value}")
    
    def _update_state(self, new_state: str):
        """
        更新实验状态（兼容旧代码，内部转换为枚举）
        
        Args:
            new_state: 状态字符串（兼容旧代码）
        """
        # 将字符串状态映射到枚举（向后兼容）
        state_map = {
            "idle": IgnitionExperimentState.IDLE,
            "heating": IgnitionExperimentState.RUNNING,
            "completed": IgnitionExperimentState.COMPLETED
        }
        
        enum_state = state_map.get(new_state, self.current_state)
        self._set_state(enum_state)
    
    def prepare_shutdown(self):
        """Confirm heater stop and persist an interrupted session before closing resources."""
        if self._shutdown_prepared:
            return True
        self._closing = True
        try:
            if self._connect_thread is not None and self._connect_thread is not threading.current_thread():
                self._connect_thread.join(5.0)
                if self._connect_thread.is_alive():
                    self.log_message.emit("✗ 设备连接尚未结束，请稍后重试退出")
                    return False
            if self.is_running:
                self.stop_experiment()
            self.data_monitor_timer.stop()
            uncontacted = (self.manager is not None
                           and getattr(self.manager, 'can_close_without_device_shutdown', lambda: False)() is True)
            if uncontacted:
                self.log_message.emit("未收到任何设备响应，且未发出控制指令；退出时无需硬件关断确认")
            if self.manager is not None and not uncontacted and self.manager.connected and not self.manager.started:
                if self.manager.start() is False:
                    self.log_message.emit("✗ 无法启动设备停止流程，请重试退出")
                    return False
            if self.manager is not None and not uncontacted and self.manager.started:
                if not self.manager.shutdown_control(
                    device_name='着火点-温控仪表',
                    control_data={'set_run_status': {'status': 'StoP'}},
                ):
                    self.log_message.emit("✗ 温控器停止未确认，请检查设备后重试退出")
                    return False
            if self.current_session_id is not None:
                status = "error" if self.current_state == IgnitionExperimentState.ERROR else "cancelled"
                if not self.db.end_experiment_session(self.current_session_id, status=status):
                    self.log_message.emit("✗ 实验结束状态保存失败，请重试退出")
                    return False
                if status == "cancelled":
                    self._set_state(IgnitionExperimentState.CANCELLED)
                self.reset_session()
            self._shutdown_prepared = True
            return True
        except Exception as error:
            self.logger.error("准备退出失败: %s", error)
            return False

    def cleanup(self):
        """Close resources only after session and device shutdown are confirmed."""
        if not self.prepare_shutdown():
            return False
        try:
            if self.manager is not None:
                if self.manager.disconnect() is False:
                    return False
                self.manager = None
            if self.db is not None:
                self.db.close()
                self.db = None
            return True
        except Exception as error:
            self.logger.error("清理资源失败: %s", error)
            return False
