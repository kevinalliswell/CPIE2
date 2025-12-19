#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加载器
支持YAML格式的配置文件
"""

import yaml
import os
from typing import Dict, Any, List


class ConfigLoader:
    """YAML配置文件加载器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = None
        
        if config_path and os.path.exists(config_path):
            self.load(config_path)
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            self.config_path = config_path
            return self.config
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def save(self, config: Dict[str, Any], config_path: str = None):
        """
        保存配置到YAML文件
        
        Args:
            config: 配置字典
            config_path: 保存路径，None则使用当前路径
        """
        save_path = config_path or self.config_path
        if not save_path:
            raise ValueError("未指定保存路径")
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            self.config = config
            self.config_path = save_path
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")
    
    def get_serial_config(self) -> Dict[str, Any]:
        """获取串口配置"""
        if not self.config:
            raise ValueError("配置未加载")
        return self.config.get('serial', {})
    
    def get_devices_config(self) -> List[Dict[str, Any]]:
        """获取设备配置列表"""
        if not self.config:
            raise ValueError("配置未加载")
        return self.config.get('devices', [])
    
    def get_polling_config(self) -> Dict[str, Any]:
        """获取轮询配置"""
        if not self.config:
            raise ValueError("配置未加载")
        return self.config.get('polling', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        if not self.config:
            raise ValueError("配置未加载")
        return self.config.get('logging', {})
    
    def validate(self) -> bool:
        """
        验证配置完整性
        
        Returns:
            配置是否有效
        """
        if not self.config:
            return False
        
        # 检查必需字段
        required_fields = ['serial', 'devices']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置缺少必需字段: {field}")
        
        # 检查串口配置
        serial_config = self.config['serial']
        if 'port' not in serial_config:
            raise ValueError("串口配置缺少port字段")
        
        # 检查设备配置
        devices = self.config['devices']
        if not devices:
            raise ValueError("未配置任何设备")
        
        for i, device in enumerate(devices):
            if 'name' not in device:
                raise ValueError(f"设备{i}缺少name字段")
            if 'type' not in device:
                raise ValueError(f"设备{i}缺少type字段")
            if 'address' not in device:
                raise ValueError(f"设备{i}缺少address字段")
        
        return True
    
    @staticmethod
    def create_template(save_path: str):
        """
        创建配置文件模板
        
        Args:
            save_path: 保存路径
        """
        template = {
            'serial': {
                'port': 'COM3',
                'baudrate': 9600,
                'bytesize': 8,
                'parity': 'N',
                'stopbits': 1,
                'timeout': 1.0
            },
            'devices': [
                {
                    'name': '压力表1',
                    'type': 'pressure_sensor',
                    'address': 1,
                    'enabled': True,
                    'poll_interval': 1.0,
                    'parameters': {}
                },
                {
                    'name': '继电器模块',
                    'type': 'relay_controller',
                    'address': 3,
                    'enabled': True,
                    'poll_interval': 2.0,
                    'parameters': {}
                },
                {
                    'name': '温度采集模块',
                    'type': 'temperature_sensor',
                    'address': 2,
                    'enabled': True,
                    'poll_interval': 1.0,
                    'parameters': {
                        'num_channels': 8
                    }
                },
                {
                    'name': '温控仪表',
                    'type': 'yudian_controller',
                    'address': 4,
                    'enabled': True,
                    'poll_interval': 2.0,
                    'parameters': {
                        'stopbits': 2
                    }
                }
            ],
            'polling': {
                'enabled': True,
                'default_interval': 1.0,
                'error_retry_delay': 5.0,
                'max_retries': 3
            },
            'logging': {
                'enabled': True,
                'level': 'INFO',
                'save_to_file': True,
                'log_dir': 'logs',
                'max_file_size_mb': 10,
                'backup_count': 5
            }
        }
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False,
                         allow_unicode=True, sort_keys=False)
            print(f"✓ 配置模板已创建: {save_path}")
        except Exception as e:
            raise Exception(f"创建配置模板失败: {e}")
