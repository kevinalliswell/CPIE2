#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus设备管理器
统一管理多个Modbus设备的通信和控制
"""

import time
import logging
import os
import threading
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pymodbus.client import ModbusSerialClient

from .config import ConfigLoader
from .devices import DEVICE_TYPES
from .poller import DataPoller, ControlExecutor


class ModbusDeviceManager:
    """Modbus多设备管理器"""
    
    def __init__(self, config_path: str = None, config_dict: Dict[str, Any] = None):
        """
        初始化设备管理器
        
        Args:
            config_path: 配置文件路径
            config_dict: 配置字典（与config_path二选一）
        """
        # 加载配置
        if config_path:
            self.config_loader = ConfigLoader(config_path)
            self.config_loader.validate()
        elif config_dict:
            self.config_loader = ConfigLoader()
            self.config_loader.config = config_dict
        else:
            raise ValueError("必须提供config_path或config_dict")
        
        # 初始化日志
        self._init_logging()
        
        # 串口客户端
        self.client = None
        self.devices = {}
        self.device_list = []
        
        # 轮询器和控制执行器
        self.poller = None
        self.executor = None
        
        # 状态
        self.connected = False
        # An open transport must remain available for safety commands even when
        # only some required devices answer the connection verification.
        self.ready = False
        self.started = False
        # Never clear contact/control evidence on cache invalidation or reconnect.
        self._device_activity = threading.Event()
        self._devices_initialized = False
        self._probe_complete = False
        
        # 数据存储
        self.latest_data = {}
        self.data_history = []
        self.max_history = 1000
        self._data_lock = threading.RLock()
        self._io_lock = threading.RLock()
        self._received_at = {}
        self._sample_id = 0
        
        self.logger.info("Modbus设备管理器已初始化")
    
    def _init_logging(self):
        """初始化日志系统"""
        log_config = self.config_loader.get_logging_config()
        
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        self.logger = logging.getLogger('ModbusManager')
        self.logger.setLevel(log_level)
        
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = next((h for h in self.logger.handlers
                                if getattr(h, '_cpie_modbus_kind', None) == 'console'), None)
        if console_handler is None:
            console_handler = logging.StreamHandler()
            console_handler._cpie_modbus_kind = 'console'
            self.logger.addHandler(console_handler)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        if log_config.get('save_to_file', False):
            log_dir = log_config.get('log_dir', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.abspath(os.path.join(
                log_dir, f"modbus_{datetime.now().strftime('%Y%m%d')}.log"))
            file_handler = next((h for h in self.logger.handlers
                                 if getattr(h, '_cpie_modbus_kind', None) == 'file'
                                 and h.baseFilename == log_file), None)
            if file_handler is None:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler._cpie_modbus_kind = 'file'
                self.logger.addHandler(file_handler)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)

    def connect(self) -> bool:
        """
        连接串口并验证全部必需设备；部分失败时保留串口用于安全关断。
        
        Returns:
            全部必需设备是否就绪。connected 单独表示串口已打开。
        """
        if self.connected:
            self.ready = self._verify_devices()
            return self.ready
        
        try:
            # 获取串口配置
            serial_config = self.config_loader.get_serial_config()
            
            # 创建Modbus客户端
            self.client = ModbusSerialClient(
                port=serial_config.get('port'),
                baudrate=int(serial_config.get('baudrate', 9600)),
                bytesize=int(serial_config.get('bytesize', 8)),
                parity=serial_config.get('parity', 'N'),
                stopbits=int(serial_config.get('stopbits', 1)),
                timeout=float(serial_config.get('timeout', 1.0)),
                retries=0,
            )
            
            # 连接串口
            if not self.client.connect():
                self.logger.error("串口连接失败")
                return False
            
            self.logger.info(f"串口连接成功: {serial_config.get('port')}")
            self.connected = True
            self.ready = False
            
            # 初始化设备
            self._init_devices()
            
            # 验证设备是否在线
            self.ready = self._verify_devices()
            if not self.ready:
                self.logger.warning("部分必需设备离线；保留串口用于安全关断和重试连接")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.ready = False
            if self.client and not self.connected:
                self.client.close()
            return False
    
    def _init_devices(self):
        """初始化所有设备"""
        self._devices_initialized = False
        self._probe_complete = False
        devices_config = self.config_loader.get_devices_config()
        self.devices.clear()
        self.device_list.clear()
        initialization_complete = True
        
        for device_config in devices_config:
            try:
                device_name = device_config['name']
                device_type = device_config['type']
                device_address = int(device_config['address'])
                
                # 获取设备类
                device_class = DEVICE_TYPES.get(device_type)
                if not device_class:
                    self.logger.error(f"未知的设备类型: {device_type}")
                    initialization_complete = False
                    continue
                
                # 创建设备实例
                device = device_class(
                    name=device_name,
                    address=device_address,
                    client=self.client,
                    io_lock=self._io_lock,
                    activity_event=self._device_activity,
                    **device_config.get('parameters', {}),
                    enabled=device_config.get('enabled', True),
                    poll_interval=float(device_config.get('poll_interval', 1.0))
                )
                
                self.devices[device_name] = device
                self.device_list.append(device)
                
                self.logger.info(f"设备已初始化: {device_name} ({device_type})")
                
            except Exception as e:
                initialization_complete = False
                self.logger.error(f"初始化设备失败: {e}")
        self._devices_initialized = initialization_complete
    
    def _verify_devices(self) -> bool:
        """
        验证全部启用的设备是否在线。
        
        Returns:
            至少配置一个启用设备，且所有启用设备均响应时返回 True。
        """
        self._probe_complete = False
        if not self.device_list:
            self.logger.warning("没有配置任何设备")
            return False
        
        # 尝试读取所有启用的设备
        success_count = 0
        enabled_count = 0
        probe_complete = True
        
        for device in self.device_list:
            if not device.enabled:
                continue
                
            enabled_count += 1
            
            try:
                self.logger.debug(f"验证设备: {device.name}")
                data = device.read_data()
                
                if data is not None:
                    success_count += 1
                    self._on_data_received(data)
                    self.logger.info(f"设备验证成功: {device.name}")
                else:
                    self.logger.warning(f"设备无响应: {device.name}")
                    
            except Exception as e:
                probe_complete = False
                self.logger.warning(f"设备验证失败 [{device.name}]: {e}")

        self._probe_complete = bool(
            self._devices_initialized and probe_complete and enabled_count > 0
        )
        
        # Every configured, enabled device is required by the experiment.
        if enabled_count > 0 and success_count == enabled_count:
            self.logger.info(f"设备验证完成: {success_count}/{enabled_count} 个设备在线")
            return True
        else:
            self.logger.error(f"必需设备未全部在线 ({success_count}/{enabled_count})")
            return False

    def can_close_without_device_shutdown(self) -> bool:
        """Allow only a completed, untouched probe that found no device responses."""
        return bool(
            self._probe_complete and not self._device_activity.is_set()
            and not self.started and self.poller is None and self.executor is None
        )
    
    def disconnect(self):
        """断开连接"""
        # 停止轮询和控制
        if not self.stop():
            self.logger.error("设备线程尚未停止，保留串口以便重试关断")
            return False
        
        # 关闭串口
        if self.client:
            self.client.close()
        
        self.connected = False
        self.ready = False
        self._invalidate_data()
        self.logger.info("已断开连接")
        return True
    
    def start(self):
        """启动数据采集和控制"""
        if not self.connected:
            self.logger.error("未连接，无法启动")
            return False
        
        if self.started:
            self.logger.warning("已经启动")
            return True

        # stop() is bounded and may return while an I/O is still unwinding.
        # Never lose its executor/poller references by starting replacement workers.
        old_writer = self.executor.executor_thread if self.executor else None
        old_readers = self.poller.device_threads.values() if self.poller else ()
        if (old_writer and old_writer.is_alive()) or any(t.is_alive() for t in old_readers):
            self.logger.error("旧设备线程尚未停止，不能重启设备管理器")
            return False
        
        try:
            # 获取轮询配置
            polling_config = self.config_loader.get_polling_config()
            
            # 创建数据轮询器
            self.poller = DataPoller(
                devices=self.device_list,
                default_interval=float(polling_config.get('default_interval', 1.0))
            )
            
            # 添加数据回调
            self.poller.add_data_callback(self._on_data_received)
            self.poller.add_error_callback(self._on_error_occurred)
            
            # 创建控制执行器
            self.executor = ControlExecutor(devices=self.device_list)
            self.executor.add_result_callback(self._on_control_result)
            
            # 启动
            if polling_config.get('enabled', True):
                self.poller.start()
                self.logger.info("数据轮询已启动")
            
            self.executor.start()
            self.logger.info("控制执行器已启动")
            
            self.started = True
            return True
            
        except Exception as e:
            self.logger.error(f"启动失败: {e}")
            return False
    
    def stop(self):
        """停止数据采集和控制"""
        self.started = False
        self._invalidate_data()
        
        stopped = True
        if self.poller:
            stopped = self.poller.stop() and stopped
            self.logger.info("数据轮询已停止")
        
        if self.executor:
            stopped = self.executor.stop() and stopped
            self.logger.info("控制执行器已停止")
        
        self._invalidate_data()
        return stopped

    def _invalidate_data(self):
        with self._data_lock:
            self.latest_data.clear()
            self._received_at.clear()
    
    def _on_data_received(self, data: Dict[str, Any]):
        """数据接收回调"""
        self._device_activity.set()
        device_name = data.get('device')
        
        with self._data_lock:
            self._sample_id += 1
            snapshot = deepcopy(data)
            snapshot['sample_id'] = self._sample_id
            self.latest_data[device_name] = snapshot
            self._received_at[device_name] = time.monotonic()
            self.data_history.append(snapshot)
            if len(self.data_history) > self.max_history:
                self.data_history.pop(0)
        
        self.logger.debug(f"收到数据: {device_name}")
    
    def _on_error_occurred(self, device_name: str, error: Exception):
        """错误发生回调"""
        self.logger.error(f"设备错误 [{device_name}]: {error}")
        with self._data_lock:
            self.latest_data.pop(device_name, None)
            self._received_at.pop(device_name, None)
    
    def _on_control_result(self, result: Dict[str, Any]):
        """控制结果回调"""
        device_name = result['device_name']
        success = result['success']
        
        if success:
            self.logger.info(f"控制成功 [{device_name}]")
            if result.get('readback'):
                self._on_data_received(result['readback'])
        else:
            self.logger.error(f"控制失败 [{device_name}]: {result.get('error')}")
    
    def send_control(self, device_name: str, control_data: Dict[str, Any],
                    priority: str = 'normal') -> bool:
        """
        发送控制命令
        
        Args:
            device_name: 设备名称
            control_data: 控制数据
            priority: 优先级 ('high', 'normal', 'low')
            
        Returns:
            是否成功加入队列
        """
        if not self.started:
            self.logger.error("未启动，无法发送控制命令")
            return False
        
        if device_name not in self.devices:
            self.logger.error(f"设备不存在: {device_name}")
            return False
        
        # 根据优先级提交控制
        self._device_activity.set()
        if priority == 'high':
            return self.executor.submit_high_priority(device_name, control_data)
        elif priority == 'low':
            return self.executor.submit_low_priority(device_name, control_data)
        else:
            return self.executor.submit_control(device_name, control_data)
    
    def send_control_and_wait(self, device_name, control_data, timeout=5.0):
        """Return the actual write result, never just queue admission."""
        if not self.started or not self.executor:
            return False
        self._device_activity.set()
        return self.executor.submit_and_wait(device_name, control_data, timeout=timeout)

    def shutdown_relays(self, device_name, timeout=5.0):
        """Block ordinary commands and confirm all four coils OFF by fresh readback."""
        if not self.started or not self.executor:
            return False
        self._device_activity.set()
        return self.executor.shutdown_relays(device_name, timeout=timeout)

    def shutdown_control(self, device_name, control_data, timeout=5.0):
        """Cancel pending commands and await a final stop command, blocking later writes."""
        if not self.started or not self.executor:
            return False
        self._device_activity.set()
        return self.executor.shutdown_control(device_name, control_data, timeout=timeout)

    def resume_controls(self, device_name):
        """Explicitly admit commands again after a confirmed safe shutdown."""
        return bool(self.started and self.executor and self.executor.resume_controls(device_name))

    def get_latest_data(self, device_name: str = None, max_age=None) -> Optional[Dict[str, Any]]:
        """
        获取最新数据
        
        Args:
            device_name: 设备名称，None返回所有设备
            
        Returns:
            设备数据字典
        """
        if not self.started:
            return None if device_name else {}
        polling = self.config_loader.get_polling_config()
        with self._data_lock:
            now = time.monotonic()
            fresh = {}
            for name, data in self.latest_data.items():
                device = self.devices.get(name)
                interval = getattr(device, 'poll_interval', polling.get('default_interval', 1.0))
                limit = max_age if max_age is not None else polling.get('max_data_age', max(3.0, 3 * interval))
                age = now - self._received_at.get(name, float('-inf'))
                if 0 <= age <= float(limit):
                    fresh[name] = deepcopy(data)
            return fresh.get(device_name) if device_name else fresh
    
    def get_data_history(self, device_name: str = None, 
                        count: int = None) -> List[Dict[str, Any]]:
        """
        获取历史数据
        
        Args:
            device_name: 设备名称，None返回所有设备
            count: 返回数量，None返回全部
            
        Returns:
            数据列表
        """
        if device_name:
            history = [d for d in self.data_history if d.get('device') == device_name]
        else:
            history = self.data_history.copy()
        
        if count:
            return history[-count:]
        else:
            return history
    
    def get_device_status(self, device_name: str = None) -> Dict[str, Any]:
        """
        获取设备状态
        
        Args:
            device_name: 设备名称，None返回所有设备
            
        Returns:
            状态字典
        """
        if device_name:
            device = self.devices.get(device_name)
            if device:
                status = device.get_status()
                status['online'] = self.get_latest_data(device_name) is not None
                return status
            else:
                return None
        else:
            return {name: self.get_device_status(name) for name in self.devices}
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'connected': self.connected,
            'ready': self.ready,
            'started': self.started,
            'devices_count': len(self.devices),
            'enabled_devices': len([d for d in self.device_list if d.enabled]),
            'latest_data_count': len(self.latest_data),
            'history_count': len(self.data_history)
        }
        
        if self.poller:
            status['poller'] = self.poller.get_status()
        
        if self.executor:
            status['executor'] = self.executor.get_status()
        
        return status
    
    def add_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加自定义数据回调
        
        Args:
            callback: 回调函数
        """
        if self.poller:
            self.poller.add_data_callback(callback)
    
    def add_control_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加自定义控制结果回调
        
        Args:
            callback: 回调函数
        """
        if self.executor:
            self.executor.add_result_callback(callback)
