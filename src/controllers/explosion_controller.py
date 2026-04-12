#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验控制器
负责爆炸性实验的业务逻辑和流程控制
"""

import logging
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer
from flamekit import FlameKit
from modbus_multi_device import ModbusDeviceManager
from models.explosion_database import ExplosionDatabase
from models.experiment_states import ExplosionExperimentState
from utils.path_manager import PathManager


class ExplosionController(QObject):
    """爆炸性实验控制器"""
    
    # 信号定义
    device_connected = Signal(bool, str)  # (成功/失败, 消息)
    experiment_created = Signal(dict)  # 实验配置
    experiment_started = Signal()  # 实验开始
    experiment_stopped = Signal()  # 实验停止
    sequence_completed = Signal()  # 时序完成
    status_updated = Signal(str, str)  # (状态文本, 样式)
    log_message = Signal(str)  # 日志消息
    spray_valve_opened = Signal()  # 喷吹阀打开（触发拍摄）
    
    # 监控面板订阅信号
    temp_controller_updated = Signal(dict)  # 温控器数据更新 {pv, sv, mv, status}
    pressure_updated = Signal(float)  # 压力数据更新
    relay_status_updated = Signal(dict)  # 继电器状态更新 {relay_id: state}
    state_changed = Signal(str)  # 实验状态变化
    progress_updated = Signal(int, str)  # 进度更新 (百分比, 消息)
    flame_image_updated = Signal(object)  # 火焰图像更新
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
        
        # 设备管理器
        self.manager = None
        self.flame_kit = FlameKit(resolution_index=0, exposure_us=4000)
        
        # 数据库
        db_path = PathManager.get_data_path("explosion_experiment.db")
        self.db = ExplosionDatabase(db_path)

        # 使用PathManager获取火焰分析路径
        self.temp_dir = PathManager.get_flame_temp_path()
        self.result_dir = PathManager.get_flame_results_path()
        self.max_flame_save_dir = PathManager.get_max_flame_images_path()
        
        # 实验状态
        self.is_running = False
        self.sequence_running = False
        self.current_session_id = None
        self.current_exp_config = None
        self.current_round_number = 0
        
        # 数据监控定时器（用于副屏实时数据推送）
        self.data_monitor_timer = QTimer(self)
        self.data_monitor_timer.timeout.connect(self._poll_device_data)
        self.data_monitor_timer.setInterval(500)  # 500ms更新一次
        
        # 当前实验状态（使用枚举）
        self.current_state = ExplosionExperimentState.IDLE
        self._relay_settle_delay_ms = int(self.config.get('relay_settle_delay_ms', 80))
        self._max_nonblocking_delay_ms = int(self.config.get('max_nonblocking_delay_ms', 200))
        self._sequence_abort_reason = None
        self._sequence_error = None

    def _interruptible_wait(self, duration_seconds: float) -> bool:
        """分片等待，允许时序停止时尽快退出。返回True表示完成等待。"""
        remaining_ms = max(0, int(duration_seconds * 1000))
        chunk_ms = max(20, min(self._max_nonblocking_delay_ms, 200))

        while remaining_ms > 0:
            if not self.sequence_running:
                return False
            wait_ms = min(chunk_ms, remaining_ms)
            threading.Event().wait(wait_ms / 1000.0)
            remaining_ms -= wait_ms

        return True

    def _abort_sequence(self, message: str, set_error_state: bool = True):
        """记录时序中止原因并更新内部标记。"""
        self._sequence_abort_reason = message
        self.sequence_running = False
        self.log_message.emit(message)
        self.logger.warning(message)
        if set_error_state:
            self._sequence_error = RuntimeError(message)

    def _handle_sequence_interrupted(self):
        """统一处理时序中断后的状态收尾。"""
        if self._sequence_abort_reason:
            self.log_message.emit(f"时序被中断: {self._sequence_abort_reason}")
        else:
            self.log_message.emit("时序被中断")
        self.logger.info("实验时序已中断")
        self.is_running = False

    def _schedule_relay_success_log(self, relay_name: str, state_str: str):
        """异步输出继电器控制成功日志，避免短暂阻塞调用线程。"""
        self.log_message.emit(f"  ✓ {relay_name} -> {state_str}")
        self.logger.debug(f"继电器控制: {relay_name} -> {state_str}")

    def _handle_sequence_stop_or_abort(self):
        """在步骤失败或外部停止后停止时序并输出一次中断日志。"""
        self.sequence_running = False
        self._handle_sequence_interrupted()

    def _should_transition_to_waiting_analysis(self) -> bool:
        """判断当前是否应在时序结束后进入等待分析状态。"""
        return (
            self.current_session_id is not None
            and self.current_state not in {
                ExplosionExperimentState.ERROR,
                ExplosionExperimentState.SESSION_CREATED,
                ExplosionExperimentState.CONNECTED,
                ExplosionExperimentState.IDLE,
            }
        )

    def _emit_current_status(self):
        """按当前状态刷新状态文本。"""
        self.status_updated.emit(
            self.current_state.display_text(),
            f"font-weight: bold; font-size: 12pt; color: {self.current_state.color()};"
        )

    def _emit_waiting_analysis_status(self):
        """刷新等待分析状态显示。"""
        self.status_updated.emit(
            f"状态: 等待分析 (会话ID:{self.current_session_id})",
            f"font-weight: bold; font-size: 12pt; color: {self.current_state.color()};"
        )

    def _set_post_sequence_state(self):
        """根据时序执行结果更新结束状态。"""
        if self.current_state == ExplosionExperimentState.ERROR:
            self.is_running = False
            self._emit_current_status()
        elif self._should_transition_to_waiting_analysis():
            self._set_state(ExplosionExperimentState.WAITING_ANALYSIS)
            self._emit_waiting_analysis_status()
        elif self.current_session_id:
            self.is_running = False
            self._emit_current_status()
        else:
            self.is_running = False
            self._set_state(ExplosionExperimentState.IDLE)
            self._emit_current_status()

    def connect_devices(self):
        """连接设备（在后台线程中执行）"""
        self.log_message.emit("正在连接设备...")
        thread = threading.Thread(target=self._execute_connect, daemon=True)
        thread.start()
    
    def _execute_connect(self):
        """执行设备连接（后台线程）"""
        try:
            # 创建设备管理器
            self.manager = ModbusDeviceManager(config_dict=self.config)
            
            # 执行连接
            if self.manager.connect():
                # 启动管理器
                self.manager.start()
                
                # 更新状态
                self._set_state(ExplosionExperimentState.CONNECTED)
                
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
    
    def create_experiment(self, config: dict):
        """
        创建实验会话
        
        Args:
            config: 实验配置，包含：
                - experiment_name: 实验名称
                - sample_name: 样品名称
                - description: 描述
                - client: 客户
                - operator: 操作员
        
        Returns:
            bool: 创建是否成功
        """
        try:
            # 创建数据库会话
            session_id = self.db.start_experiment_session(
                experiment_id=config.get('experiment_id'),
                experiment_name=config['experiment_name'],
                sample_name=config['sample_name'],
                client=config.get('client'),
                operator=config.get('operator'),
                description=config['description']
            )
            
            if session_id > 0:
                self.current_session_id = session_id
                self.current_exp_config = config
                self.current_round_number = 0  # 重置轮次
                
                # 更新状态
                self._set_state(ExplosionExperimentState.SESSION_CREATED)
                
                self.log_message.emit("=" * 50)
                self.log_message.emit("✓ 实验已创建")
                self.log_message.emit(f"  实验编号: {config.get('experiment_id', '未知')}")
                self.log_message.emit(f"  实验名称: {config['experiment_name']}")
                self.log_message.emit(f"  样品名称: {config['sample_name']}")
                self.log_message.emit(f"  委托单位: {config.get('client', '')}")
                self.log_message.emit(f"  操作员: {config.get('operator', '')}")
                self.log_message.emit(f"  会话ID: {session_id}")
                self.log_message.emit("=" * 50)
                
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
        启动实验（带时序控制）
        
        Returns:
            bool: 启动是否成功
        """
        # 检查前提条件
        if self.current_session_id is None:
            self.log_message.emit("✗ 请先新建实验！")
            return False
        
        if self.sequence_running:
            self.log_message.emit("✗ 实验正在进行中")
            return False
        
        if not self.manager:
            self.log_message.emit("✗ 设备未连接！")
            return False
        
        # 检查状态转换是否合法
        if not self.current_state.can_start():
            self.log_message.emit(f"✗ 当前状态不允许启动实验: {self.current_state.description()}")
            return False
        
        # 增加轮次
        self.current_round_number += 1
        
        # 启动时序控制
        self._start_sequence()
        return True
    
    def _start_sequence(self):
        """启动时序控制"""
        self.log_message.emit("=" * 50)
        self.log_message.emit(f"启动实验时序控制 - 第 {self.current_round_number} 轮")
        self.log_message.emit(f"会话ID: {self.current_session_id}")
        
        # 更新状态
        self.is_running = True
        self.sequence_running = True
        self._sequence_abort_reason = None
        self._sequence_error = None
        self._set_state(ExplosionExperimentState.SEQUENCE_RUNNING)
        
        self.status_updated.emit(
            f"状态: 实验中 (第{self.current_round_number}轮)",
            f"font-weight: bold; font-size: 12pt; color: {self.current_state.color()};"
        )
        
        self.experiment_started.emit()
        
        # 在新线程中执行时序
        thread = threading.Thread(target=self._execute_sequence, daemon=True)
        thread.start()
    
    def _execute_sequence(self):
        """执行时序控制（后台线程）"""
        try:
            steps = self.config.get('sequence_steps', [])

            for step in steps:
                if not self.sequence_running:
                    self._handle_sequence_interrupted()
                    break

                step_num = step['step']
                name = step['name']
                action = step['action']

                self.log_message.emit(f"[步骤{step_num}] {name}")

                if action == 'relay_on':
                    relay = step['relay']
                    # 如果是打开喷吹阀，发送信号触发拍摄
                    if relay == 'spray_valve':
                        self.spray_valve_opened.emit()
                    if not self.control_relay(relay, True):
                        self._abort_sequence(f"步骤{step_num} 执行失败: 无法打开继电器 {relay}")
                        break

                elif action == 'relay_off':
                    relay = step['relay']
                    if not self.control_relay(relay, False):
                        self._abort_sequence(f"步骤{step_num} 执行失败: 无法关闭继电器 {relay}")
                        break

                elif action == 'relay_multi_on':
                    relays = step['relays']
                    for relay in relays:
                        if not self.control_relay(relay, True):
                            self._abort_sequence(f"步骤{step_num} 执行失败: 无法打开继电器 {relay}")
                            break
                    if not self.sequence_running:
                        self._handle_sequence_stop_or_abort()
                        break

                elif action == 'relay_multi_off':
                    relays = step['relays']
                    for relay in relays:
                        if not self.control_relay(relay, False):
                            self._abort_sequence(f"步骤{step_num} 执行失败: 无法关闭继电器 {relay}")
                            break
                    if not self.sequence_running:
                        self._handle_sequence_stop_or_abort()
                        break

                elif action == 'delay':
                    duration = step['duration']
                    self.log_message.emit(f"  延时 {duration}秒...")
                    if not self._interruptible_wait(duration):
                        self._handle_sequence_stop_or_abort()
                        break

                elif action == 'verify_all_off':
                    if not self._verify_relays_off(step):
                        if self.sequence_running:
                            self._abort_sequence(f"步骤{step_num} 验证失败: 仍有继电器未关闭")
                        else:
                            self._handle_sequence_stop_or_abort()
                        break

                # 步骤后延时
                delay_after = step.get('delay_after', 0)
                if delay_after > 0 and not self._interruptible_wait(delay_after):
                    self._handle_sequence_stop_or_abort()
                    break

            if self._sequence_error:
                raise self._sequence_error

            if self.sequence_running:
                self.log_message.emit("=" * 50)
                self.log_message.emit(f"✓ 第 {self.current_round_number} 轮实验完成")
                self.sequence_completed.emit()

        except Exception as e:
            self.log_message.emit(f"✗ 时序执行错误: {e}")
            self.logger.error(f"时序执行错误: {e}")
            self._set_state(ExplosionExperimentState.ERROR)

        finally:
            self.sequence_running = False
            self._set_post_sequence_state()
            self._sequence_abort_reason = None
            self._sequence_error = None
    
    def stop_experiment(self):
        """
        停止实验
        
        Returns:
            bool: 停止是否成功
        """
        if not self.is_running and not self.sequence_running:
            return False
        
        # 检查状态转换是否合法
        if not self.current_state.can_stop():
            self.log_message.emit(f"✗ 当前状态不允许停止实验: {self.current_state.description()}")
            return False
        
        try:
            self.log_message.emit("停止实验...")

            # 停止时序
            self.sequence_running = False
            self._sequence_abort_reason = "用户主动停止实验"
            self._sequence_error = None

            # 关闭所有继电器
            relay_shutdown_failures = []
            if self.manager:
                relay_mapping = self.config.get('relay_mapping', {})
                for relay_name in relay_mapping.keys():
                    if not self.control_relay(relay_name, False):
                        relay_shutdown_failures.append(relay_name)

            if relay_shutdown_failures:
                failure_msg = f"停止时未能关闭继电器: {', '.join(relay_shutdown_failures)}"
                self.log_message.emit(f"⚠ {failure_msg}")
                self.logger.warning(failure_msg)

            # 停止设备管理器（但不关闭连接，因为可能还需要使用）
            # 注意：这里只停止运行，不关闭连接，真正的关闭在cleanup中处理

            # 注意：不要在这里结束数据库会话
            # 停止只是暂停当前轮次，会话应保持running状态
            # 会话只在用户主动"完成实验"时才结束

            # 更新状态：停止后回到SESSION_CREATED状态（可以继续实验）
            self.is_running = False
            if self.current_session_id:
                self._set_state(ExplosionExperimentState.SESSION_CREATED)
            else:
                self._set_state(ExplosionExperimentState.CONNECTED)

            self.experiment_stopped.emit()

            self.status_updated.emit(
                self.current_state.display_text(),
                f"font-weight: bold; font-size: 12pt; color: {self.current_state.color()};"
            )
            self.log_message.emit("✓ 实验已停止")
            self.logger.info("实验已停止")

            return not relay_shutdown_failures
        
        except Exception as e:
            self.log_message.emit(f"✗ 停止失败: {e}")
            self.logger.error(f"停止实验失败: {e}")
            return False
    
    def control_relay(self, relay_name: str, state: bool):
        """
        控制继电器
        
        Args:
            relay_name: 继电器名称
            state: 状态（True=导通, False=断开）
        
        Returns:
            bool: 控制是否成功
        """
        relay_mapping = self.config.get('relay_mapping', {})
        relay_num = relay_mapping.get(relay_name)
        
        if relay_num is None:
            self.log_message.emit(f"✗ 未知的继电器: {relay_name}")
            return False
        
        if not self.manager:
            self.log_message.emit("✗ 设备管理器未初始化")
            return False
        
        try:
            success = self.manager.send_control(
                device_name='爆炸性-继电器',
                control_data={
                    'set_relay': {
                        'relay': relay_num,
                        'state': state
                    }
                },
                priority='high'
            )
            
            state_str = "导通" if state else "断开"
            if success:
                if self._relay_settle_delay_ms > 0:
                    QTimer.singleShot(
                        self._relay_settle_delay_ms,
                        lambda relay_name=relay_name, state_str=state_str: self._schedule_relay_success_log(relay_name, state_str)
                    )
                else:
                    self._schedule_relay_success_log(relay_name, state_str)
                return True
            else:
                self.log_message.emit(f"  ✗ {relay_name} 控制失败")
                return False
        
        except Exception as e:
            self.log_message.emit(f"  ✗ 控制异常: {e}")
            self.logger.error(f"继电器控制异常: {e}")
            return False
    
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
            self.manager.send_control(
                device_name='爆炸性-温控仪表',
                control_data={'set_run_status': {'status': action}},
                priority='high'
            )
            self.log_message.emit(f"发送控制命令: {action}")
            self.logger.info(f"控制温控器: {action}")
            return True
        except Exception as e:
            self.log_message.emit(f"✗ 控制失败: {e}")
            self.logger.error(f"控制温控器失败: {e}")
            return False
    
    def _verify_relays_off(self, step_config):
        """验证继电器全部关闭"""
        retry_count = step_config.get('retry_count', 3)
        retry_interval = step_config.get('retry_interval', 1.0)

        for attempt in range(retry_count):
            all_off = True

            # 检查所有继电器状态
            data = self.get_latest_relay_data()
            if data:
                relays = data.get('relays', {})
                for relay_num, state in relays.items():
                    if state:
                        all_off = False
                        self.log_message.emit(f"  ⚠ 继电器{relay_num}仍处于导通状态")

            if all_off:
                self.log_message.emit("  ✓ 所有继电器已关闭")
                return True

            if attempt < retry_count - 1:
                self.log_message.emit(f"  等待{retry_interval}秒后重试...")
                if not self._interruptible_wait(retry_interval):
                    return False

        self.log_message.emit("  ✗ 验证失败：部分继电器未关闭")
        return False
    
    def get_latest_controller_data(self):
        """
        获取最新的温控器数据
        
        Returns:
            dict or None: 温控器数据
        """
        if not self.manager:
            return None
        return self.manager.get_latest_data('爆炸性-温控仪表')
    
    def get_latest_pressure_data(self):
        """
        获取最新的压力数据
        
        Returns:
            dict or None: 压力数据
        """
        if not self.manager:
            return None
        return self.manager.get_latest_data('爆炸性-压力仪表')
    
    def get_latest_relay_data(self):
        """
        获取最新的继电器数据
        
        Returns:
            dict or None: 继电器数据
        """
        if not self.manager:
            return None
        return self.manager.get_latest_data('爆炸性-继电器')
    
    def generate_experiment_id(self):
        """
        生成实验编号：EXP-YYYYMMDD-HHMMSS
        
        Returns:
            str: 实验编号
        """
        return f"EXP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def get_experiment_status(self):
        """
        获取实验状态
        
        Returns:
            dict: 实验状态信息
        """
        return {
            'is_running': self.is_running,
            'sequence_running': self.sequence_running,
            'session_id': self.current_session_id,
            'experiment_config': self.current_exp_config,
            'current_round': self.current_round_number,
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
                
                self.temp_controller_updated.emit({
                    'pv': pv,
                    'sv': sv,
                    'mv': mv,
                    'status': status
                })
            
            # 获取压力数据
            pressure_data = self.get_latest_pressure_data()
            if pressure_data:
                pressure = pressure_data.get('pressure', 0.0)
                if pressure is not None:
                    self.pressure_updated.emit(pressure)
                else:
                    # 即使压力为None，也发送信号显示默认值
                    self.pressure_updated.emit(0.0)
            else:
                # 如果没有压力数据，发送None值让UI显示默认状态
                self.pressure_updated.emit(0.0)
            
            # 获取继电器状态
            relay_data = self.get_latest_relay_data()
            if relay_data:
                relays = relay_data.get('relays', {})
                if relays:
                    # 将数字键转换为字符串键
                    relay_status = {str(k): v for k, v in relays.items()}
                    self.relay_status_updated.emit(relay_status)
                    
                    # 更新设备在线状态
                    self.device_status_changed.emit('继电器', True)
                else:
                    # 如果relays为空，发送空字典表示全部关闭
                    self.relay_status_updated.emit({})
            else:
                # 如果没有继电器数据，发送空字典表示全部关闭
                self.relay_status_updated.emit({})
            
        except Exception as e:
            self.logger.error(f"轮询设备数据失败: {e}")
    
    def _set_state(self, new_state: ExplosionExperimentState):
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
            "idle": ExplosionExperimentState.IDLE,
            "heating": ExplosionExperimentState.SEQUENCE_RUNNING,
            "completed": ExplosionExperimentState.COMPLETED
        }
        
        enum_state = state_map.get(new_state, self.current_state)
        self._set_state(enum_state)
    
    # ==================== 数据库代理方法 ====================
    # 避免视图层直接访问 self.controller.db，统一通过控制器方法访问数据库

    def sync_round_number(self, count: int):
        """同步实验轮次计数器（从数据库加载历史数据后调用）"""
        self.current_round_number = count

    def get_session_test_rounds(self, session_id: int):
        """获取某个会话的所有测试轮次"""
        return self.db.get_session_test_rounds(session_id)

    def add_test_round(self, session_id: int, round_number: int,
                       flame_length: float, max_flame_image_path: str = None):
        """添加一轮测试数据"""
        return self.db.add_test_round(session_id, round_number, flame_length, max_flame_image_path)

    def calculate_session_average(self, session_id: int):
        """计算某个会话的平均火焰长度"""
        return self.db.calculate_session_average(session_id)

    def classify_explosion_strength(self, avg_flame_length: float):
        """根据平均火焰长度分类爆炸性强弱"""
        return self.db.classify_explosion_strength(avg_flame_length)

    def finalize_experiment(self, session_id: int, status: str = 'completed'):
        """完成实验，计算平均值并保存结果"""
        return self.db.finalize_experiment(session_id, status)

    def cleanup(self):
        """
        清理资源：停止定时器、停止设备管理器、关闭数据库连接
        """
        try:
            self.logger.info("开始清理爆炸性控制器资源...")
            
            # 停止实验
            if self.is_running or self.sequence_running:
                self.stop_experiment()
            
            # 停止数据监控定时器
            if hasattr(self, 'data_monitor_timer'):
                self.data_monitor_timer.stop()
                self.logger.debug("数据监控定时器已停止")
            
            # 停止设备管理器
            if self.manager:
                try:
                    if hasattr(self.manager, 'stop'):
                        self.manager.stop()
                    if hasattr(self.manager, 'close'):
                        self.manager.close()
                    self.logger.debug("设备管理器已停止")
                except Exception as e:
                    self.logger.error(f"停止设备管理器失败: {e}")
                finally:
                    self.manager = None
            
            # 关闭数据库连接
            if self.db:
                try:
                    self.db.close()
                    self.logger.debug("数据库连接已关闭")
                except Exception as e:
                    self.logger.error(f"关闭数据库连接失败: {e}")
                finally:
                    self.db = None
            
            self.logger.info("爆炸性控制器资源清理完成")
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")

