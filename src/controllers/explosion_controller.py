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
from services.explosion.experiment_validator import ExperimentValidator
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
    
    def __init__(self, config=None, parent=None, camera_round_guard=None):
        """
        初始化控制器
        
        Args:
            config: 实验配置
            parent: 父对象
            camera_round_guard: 可选采集窗口检查，在时序线程中接收检查阶段并返回 bool
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
        self._sequence_thread = None
        self._connect_thread = None
        self._stop_requested = threading.Event()
        self._shutdown_lock = threading.Lock()
        self._closing = False
        self._shutdown_prepared = False
        self._control_timeout = float(self.config.get('control_timeout', 5.0))
        self.camera_round_guard = camera_round_guard

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
        """连接设备；保留线程引用，退出前必须等待连接结束。"""
        if self._closing or (self._connect_thread and self._connect_thread.is_alive()):
            return False
        self.log_message.emit("正在连接设备...")
        self._connect_thread = threading.Thread(target=self._execute_connect, daemon=True)
        self._connect_thread.start()
        return True

    def _execute_connect(self):
        """执行设备连接（后台线程）"""
        try:
            # Reuse a partially connected manager: replacing it would abandon
            # an open serial port that may still control energized outputs.
            if self.manager is None:
                self.manager = ModbusDeviceManager(config_dict=self.config)
            
            # 执行连接
            if self.manager.connect():
                if self._closing:
                    # Keep the newly opened port for prepare_shutdown: even
                    # pre-existing outputs must be confirmed OFF before close.
                    return
                if not self.manager.start():
                    self.manager.disconnect()
                    raise RuntimeError("无法启动设备管理器")
                
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
        if self._closing or self.current_session_id is not None:
            self.log_message.emit("✗ 请先完成当前会话；退出准备期间不能创建实验")
            return False
        if not self.current_state.can_create_experiment():
            return False
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
        # Do not replace a sequence thread until its OFF barrier has completed.
        if self._closing or (self._sequence_thread and self._sequence_thread.is_alive()):
            return False
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
        
        # A previous manual-clean operation may have left valves open. Establish
        # a known starting position, then recheck fresh conditions immediately
        # before admission (the UI confirmation may have been open for minutes).
        self._stop_requested.clear()
        if not self._shutdown_relays():
            self._set_state(ExplosionExperimentState.ERROR)
            return False
        valid, message = ExperimentValidator(self.config, self.manager).check_conditions()
        if not valid:
            self.log_message.emit(f"✗ 启动前检查失败: {message}")
            return False
        if self._closing or self._stop_requested.is_set():
            return False
        try:
            rounds = self.db.get_session_test_rounds(self.current_session_id)
            next_round = max((r['round_number'] for r in rounds), default=0) + 1
        except Exception as exc:
            self.log_message.emit(f"✗ 无法读取已保存轮次: {exc}")
            return False
        if not self.manager.resume_controls('爆炸性-继电器'):
            self.log_message.emit("✗ 尚未确认继电器安全关闭，不能启动新轮次")
            return False
        if self._closing or self._stop_requested.is_set():
            self._shutdown_relays()
            return False
        # Cancelled/failed attempts have no stored result and retry this number.
        self.current_round_number = next_round
        
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
        self._sequence_thread = threading.Thread(target=self._execute_sequence, daemon=True)
        self._sequence_thread.start()

    def _execute_relay_on(self, relay):
        """Every sequence spray, including grouped actions, uses the capture gate."""
        guard = self.camera_round_guard if relay == 'spray_valve' else None
        if relay == 'spray_valve':
            self.spray_valve_opened.emit()
            if guard is not None and not guard('before_spray'):
                raise RuntimeError('相机尚未开始有效采集，已中止喷吹')
        if not self.control_relay(relay, True):
            return False
        if guard is not None and not guard('after_spray'):
            raise RuntimeError('喷吹确认时相机采集窗口已结束，本轮无效')
        return True
    
    def _execute_sequence(self):
        """执行时序控制；每条指令等待实执行，所有结束路径先完成 OFF 收尾。"""
        completed = False
        try:
            steps = self.config.get('sequence_steps', [])

            for step in steps:
                if not self.sequence_running or self._stop_requested.is_set():
                    self._handle_sequence_interrupted()
                    break

                step_num = step['step']
                name = step['name']
                action = step['action']

                self.log_message.emit(f"[步骤{step_num}] {name}")

                if action == 'relay_on':
                    relay = step['relay']
                    if not self._execute_relay_on(relay):
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
                        if not self._execute_relay_on(relay):
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

                else:
                    raise ValueError(f"未知时序动作: {action}")

                # 步骤后延时
                delay_after = step.get('delay_after', 0)
                if delay_after > 0 and not self._interruptible_wait(delay_after):
                    self._handle_sequence_stop_or_abort()
                    break

            if self._sequence_error:
                raise self._sequence_error

            completed = self.sequence_running and not self._stop_requested.is_set()

        except Exception as e:
            self.log_message.emit(f"✗ 时序执行错误: {e}")
            self.logger.error(f"时序执行错误: {e}")
            self._set_state(ExplosionExperimentState.ERROR)

        finally:
            self.sequence_running = False
            self.is_running = False
            safe = self._shutdown_relays()
            if not safe:
                self._set_state(ExplosionExperimentState.ERROR)
            if self.current_state == ExplosionExperimentState.ERROR:
                self.experiment_stopped.emit()
            elif self._stop_requested.is_set() or not completed:
                if self.current_session_id:
                    self._set_state(ExplosionExperimentState.SESSION_CREATED)
                self.experiment_stopped.emit()
            else:
                self._set_state(ExplosionExperimentState.WAITING_ANALYSIS)
                self.log_message.emit(f"✓ 第 {self.current_round_number} 轮实验完成，继电器已确认关闭")
                self.sequence_completed.emit()
            self._emit_current_status()
            self._sequence_abort_reason = None
            self._sequence_error = None
    
    def stop_experiment(self):
        """Cancel work, confirm outputs OFF, and join the sequence before reuse."""
        self._stop_requested.set()
        self.sequence_running = False
        self._sequence_abort_reason = "用户主动停止实验"
        safe = self._shutdown_relays()
        thread = self._sequence_thread
        if thread and thread is not threading.current_thread():
            thread.join(self._control_timeout + 1.0)
            if thread.is_alive():
                safe = False
                self.log_message.emit("✗ 时序线程尚未结束，请重试停止")
        self.is_running = False
        if not safe:
            self._set_state(ExplosionExperimentState.ERROR)
        elif self.current_session_id:
            self._set_state(ExplosionExperimentState.SESSION_CREATED)
        self.experiment_stopped.emit()
        self._emit_current_status()
        return safe

    def _shutdown_relays(self):
        """Independent of the experiment state; failure keeps I/O available to retry."""
        with self._shutdown_lock:
            try:
                if self.manager is None:
                    return True
                if not self.manager.connected:
                    return not self.manager.started
                if not self.manager.started and not self.manager.start():
                    return False
                success = self.manager.shutdown_relays('爆炸性-继电器', timeout=self._control_timeout)
            except Exception as exc:
                self.logger.error(f"关断设备异常: {exc}")
                success = False
            if not success:
                self.log_message.emit("✗ 未确认全部继电器关闭；请检查设备并重试停止，必要时人工断电")
                self.logger.error("继电器安全关断未确认")
            return success

    def control_relay(self, relay_name: str, state: bool):
        """Wait for device execution; a submitted write is not an acknowledgement."""
        relay_num = self.config.get('relay_mapping', {}).get(relay_name)
        if relay_num is None or not self.manager:
            self.log_message.emit(f"✗ 无法控制继电器: {relay_name}")
            return False
        if state and (self._closing or self._stop_requested.is_set()):
            return False
        try:
            success = self.manager.send_control_and_wait(
                '爆炸性-继电器', {'set_relay': {'relay': relay_num, 'state': state}},
                timeout=self._control_timeout)
            if success:
                self._schedule_relay_success_log(relay_name, "导通" if state else "断开")
            else:
                self.log_message.emit(f"✗ {relay_name} 未确认控制成功")
            return success
        except Exception as exc:
            self.log_message.emit(f"✗ 继电器控制异常: {exc}")
            return False

    def set_auto_clean(self, enabled: bool) -> bool:
        """Run manual cleaning only after prior sequence work and OFF are confirmed."""
        thread = self._sequence_thread
        if (self._closing or self.sequence_running or self.is_running
                or (thread and thread.is_alive())):
            self.log_message.emit("✗ 时序运行或退出准备期间不能执行自清洁")
            return False
        if not self.manager or not self.manager.connected:
            self.log_message.emit("✗ 设备未连接，不能执行自清洁")
            return False
        if not enabled:
            return self._shutdown_relays()

        # Only this explicit, idle operation may reopen control admission.
        # Clearing once before OFF preserves any stop arriving during its wait.
        self._stop_requested.clear()
        if not self._shutdown_relays():
            return False
        if self._closing or self._stop_requested.is_set():
            return False
        if not self.manager.resume_controls('爆炸性-继电器'):
            return False
        for relay in ('spray_valve', 'purge_valve', 'vacuum_cleaner'):
            if not self.control_relay(relay, True):
                self._shutdown_relays()
                return False
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
            if self._closing:
                return False
            success = self.manager.send_control_and_wait(
                device_name='爆炸性-温控仪表',
                control_data={'set_run_status': {'status': action}},
                timeout=self._control_timeout
            )
            if not success:
                self.log_message.emit(f"✗ 温控器未确认执行: {action}")
                return False
            self.log_message.emit(f"温控器已确认执行: {action}")
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
            data = self.get_latest_relay_data()
            relays = data.get('relays', {}) if data else {}
            all_off = all(relays.get(f'relay_{i}') is False for i in range(1, 5))

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
        return self.manager.get_latest_data('爆炸性-压力表')
    
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
        """Publish online state separately; unavailable readings are never zero/OFF."""
        temp_data = self.get_latest_controller_data()
        pressure_data = self.get_latest_pressure_data()
        relay_data = self.get_latest_relay_data()
        self.device_status_changed.emit('温控器', bool(temp_data))
        self.device_status_changed.emit('压力表', bool(pressure_data))
        self.device_status_changed.emit('继电器', bool(relay_data))
        if temp_data:
            self.temp_controller_updated.emit({
                'pv': temp_data.get('pv'), 'sv': temp_data.get('sv'),
                'mv': temp_data.get('mv'), 'status': '在线'})
        if pressure_data and pressure_data.get('pressure') is not None:
            self.pressure_updated.emit(pressure_data['pressure'])
        if relay_data:
            self.relay_status_updated.emit(dict(relay_data.get('relays', {})))

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
        """Save first; only a committed result may clear the active session."""
        if (status != 'completed' or session_id != self.current_session_id
                or not self.current_state.can_finalize() or self._closing):
            return False
        thread = self._sequence_thread
        if self.sequence_running or (thread and thread.is_alive()):
            return False
        if not self._shutdown_relays():
            self._set_state(ExplosionExperimentState.ERROR)
            return False
        if (not self.current_state.can_transition_to(ExplosionExperimentState.COMPLETED)
                or not self.db or not self.db.finalize_experiment(session_id, 'completed')):
            return False
        self._set_state(ExplosionExperimentState.COMPLETED)
        self._clear_session()
        return True

    def _clear_session(self):
        self.current_session_id = None
        self.current_exp_config = None
        self.current_round_number = 0
        self.is_running = False
        self.sequence_running = False

    def prepare_shutdown(self):
        """First shutdown phase: stop hardware and persist the interrupted session."""
        if self._shutdown_prepared:
            return True
        self._closing = True
        self._stop_requested.set()
        connection = self._connect_thread
        if connection and connection is not threading.current_thread():
            connection.join(self._control_timeout)
            if connection.is_alive():
                self.log_message.emit("✗ 设备连接线程尚未结束，请稍后重试退出")
                return False
        was_error = self.current_state == ExplosionExperimentState.ERROR
        if not self.stop_experiment():
            return False
        # Stop the separate temperature program only at application shutdown.
        if self.manager and '爆炸性-温控仪表' in self.manager.devices:
            if not self.manager.shutdown_control(
                    '爆炸性-温控仪表', {'set_run_status': {'status': 'StoP'}},
                    timeout=self._control_timeout):
                self.log_message.emit("✗ 温控器停止未确认，请重试退出")
                return False
        if self.current_session_id is not None:
            status = 'error' if was_error else 'cancelled'
            if not self.db or not self.db.end_experiment_session(self.current_session_id, status=status):
                self.log_message.emit("✗ 会话结束状态保存失败，请重试退出")
                return False
            self._clear_session()
        self._shutdown_prepared = True
        return True

    def cleanup(self):
        """Commit resource closure only after the prepare phase succeeds."""
        try:
            if not self.prepare_shutdown():
                return False
            self.data_monitor_timer.stop()
            if self.manager:
                if not self.manager.disconnect():
                    return False
                self.manager = None
            if self.db:
                self.db.close()
                self.db = None
            return True
        except Exception as exc:
            self.logger.error(f"清理资源失败: {exc}")
            return False
