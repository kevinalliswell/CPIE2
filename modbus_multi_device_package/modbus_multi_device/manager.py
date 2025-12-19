#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus设备管理器
统一管理多个Modbus设备的通信和控制
"""

import time
import logging
import os
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
        self.started = False
        
        # 数据存储
        self.latest_data = {}
        self.data_history = []
        self.max_history = 1000
        
        self.logger.info("Modbus设备管理器已初始化")
    
    def _init_logging(self):
        """初始化日志系统"""
        log_config = self.config_loader.get_logging_config()
        
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        self.logger = logging.getLogger('ModbusManager')
        self.logger.setLevel(log_level)
        
        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件输出
        if log_config.get('save_to_file', False):
            log_dir = log_config.get('log_dir', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(
                log_dir,
                f"modbus_{datetime.now().strftime('%Y%m%d')}.log"
            )
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def connect(self) -> bool:
        """
        连接到串口并初始化所有设备
        
        Returns:
            是否连接成功
        """
        if self.connected:
            self.logger.warning("已经连接，无需重复连接")
            return True
        
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
                timeout=float(serial_config.get('timeout', 1.0))
            )
            
            # 连接串口
            if not self.client.connect():
                self.logger.error("串口连接失败")
                return False
            
            self.logger.info(f"串口连接成功: {serial_config.get('port')}")
            
            # 初始化设备
            self._init_devices()
            
            # 验证设备是否在线
            if not self._verify_devices():
                self.logger.warning("串口已打开，但无法与设备通信（设备可能离线）")
                self.client.close()
                return False
            
            self.connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            return False
    
    def _init_devices(self):
        """初始化所有设备"""
        devices_config = self.config_loader.get_devices_config()
        
        for device_config in devices_config:
            try:
                device_name = device_config['name']
                device_type = device_config['type']
                device_address = int(device_config['address'])
                
                # 获取设备类
                device_class = DEVICE_TYPES.get(device_type)
                if not device_class:
                    self.logger.error(f"未知的设备类型: {device_type}")
                    continue
                
                # 创建设备实例
                device = device_class(
                    name=device_name,
                    address=device_address,
                    client=self.client,
                    **device_config.get('parameters', {}),
                    enabled=device_config.get('enabled', True),
                    poll_interval=float(device_config.get('poll_interval', 1.0))
                )
                
                self.devices[device_name] = device
                self.device_list.append(device)
                
                self.logger.info(f"设备已初始化: {device_name} ({device_type})")
                
            except Exception as e:
                self.logger.error(f"初始化设备失败: {e}")
    
    def _verify_devices(self) -> bool:
        """
        验证设备是否在线（尝试读取第一个启用的设备）
        
        Returns:
            至少有一个设备响应返回True，否则返回False
        """
        if not self.device_list:
            self.logger.warning("没有配置任何设备")
            return False
        
        # 尝试读取所有启用的设备
        success_count = 0
        enabled_count = 0
        
        for device in self.device_list:
            if not device.enabled:
                continue
                
            enabled_count += 1
            
            try:
                self.logger.debug(f"验证设备: {device.name}")
                data = device.read_data()
                
                if data is not None:
                    success_count += 1
                    self.logger.info(f"设备验证成功: {device.name}")
                else:
                    self.logger.warning(f"设备无响应: {device.name}")
                    
            except Exception as e:
                self.logger.warning(f"设备验证失败 [{device.name}]: {e}")
        
        # 至少有一个设备响应才算成功
        if success_count > 0:
            self.logger.info(f"设备验证完成: {success_count}/{enabled_count} 个设备在线")
            return True
        else:
            self.logger.error(f"所有设备均无响应 (0/{enabled_count})")
            return False
    
    def disconnect(self):
        """断开连接"""
        if not self.connected:
            return
        
        # 停止轮询和控制
        self.stop()
        
        # 关闭串口
        if self.client:
            self.client.close()
        
        self.connected = False
        self.logger.info("已断开连接")
    
    def start(self):
        """启动数据采集和控制"""
        if not self.connected:
            self.logger.error("未连接，无法启动")
            return False
        
        if self.started:
            self.logger.warning("已经启动")
            return True
        
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
        if not self.started:
            return
        
        if self.poller:
            self.poller.stop()
            self.logger.info("数据轮询已停止")
        
        if self.executor:
            self.executor.stop()
            self.logger.info("控制执行器已停止")
        
        self.started = False
    
    def _on_data_received(self, data: Dict[str, Any]):
        """数据接收回调"""
        device_name = data.get('device')
        
        # 更新最新数据
        self.latest_data[device_name] = data
        
        # 添加到历史记录
        self.data_history.append(data)
        
        # 限制历史记录长度
        if len(self.data_history) > self.max_history:
            self.data_history.pop(0)
        
        self.logger.debug(f"收到数据: {device_name}")
    
    def _on_error_occurred(self, device_name: str, error: Exception):
        """错误发生回调"""
        self.logger.error(f"设备错误 [{device_name}]: {error}")
    
    def _on_control_result(self, result: Dict[str, Any]):
        """控制结果回调"""
        device_name = result['device_name']
        success = result['success']
        
        if success:
            self.logger.info(f"控制成功 [{device_name}]")
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
        if priority == 'high':
            return self.executor.submit_high_priority(device_name, control_data)
        elif priority == 'low':
            return self.executor.submit_low_priority(device_name, control_data)
        else:
            return self.executor.submit_control(device_name, control_data)
    
    def get_latest_data(self, device_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取最新数据
        
        Args:
            device_name: 设备名称，None返回所有设备
            
        Returns:
            设备数据字典
        """
        if device_name:
            return self.latest_data.get(device_name)
        else:
            return self.latest_data.copy()
    
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
                return device.get_status()
            else:
                return None
        else:
            return {name: device.get_status() 
                   for name, device in self.devices.items()}
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'connected': self.connected,
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
