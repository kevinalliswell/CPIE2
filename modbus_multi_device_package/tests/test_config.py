#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器测试
测试 ConfigLoader 类的各项功能
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加包路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modbus_multi_device import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    """ConfigLoader 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_path = os.path.join(self.temp_dir, 'test_config.yaml')
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
        os.rmdir(self.temp_dir)
    
    def test_create_template(self):
        """测试创建配置模板"""
        ConfigLoader.create_template(self.test_config_path)
        
        # 验证文件已创建
        self.assertTrue(os.path.exists(self.test_config_path))
        
        # 验证可以加载
        loader = ConfigLoader(self.test_config_path)
        self.assertIsNotNone(loader.config)
    
    def test_load_config(self):
        """测试加载配置文件"""
        # 创建测试配置
        ConfigLoader.create_template(self.test_config_path)
        
        # 加载配置
        loader = ConfigLoader()
        config = loader.load(self.test_config_path)
        
        # 验证配置结构
        self.assertIn('serial', config)
        self.assertIn('devices', config)
        self.assertIn('polling', config)
        self.assertIn('logging', config)
    
    def test_get_serial_config(self):
        """测试获取串口配置"""
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        serial_config = loader.get_serial_config()
        
        # 验证必需字段
        self.assertIn('port', serial_config)
        self.assertIn('baudrate', serial_config)
        self.assertIn('timeout', serial_config)
    
    def test_get_devices_config(self):
        """测试获取设备配置"""
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        devices_config = loader.get_devices_config()
        
        # 验证是列表
        self.assertIsInstance(devices_config, list)
        self.assertGreater(len(devices_config), 0)
        
        # 验证第一个设备的必需字段
        first_device = devices_config[0]
        self.assertIn('name', first_device)
        self.assertIn('type', first_device)
        self.assertIn('address', first_device)
    
    def test_get_polling_config(self):
        """测试获取轮询配置"""
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        polling_config = loader.get_polling_config()
        
        # 验证字段
        self.assertIn('enabled', polling_config)
        self.assertIn('default_interval', polling_config)
    
    def test_get_logging_config(self):
        """测试获取日志配置"""
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        logging_config = loader.get_logging_config()
        
        # 验证字段
        self.assertIn('enabled', logging_config)
        self.assertIn('level', logging_config)
    
    def test_validate_valid_config(self):
        """测试验证有效配置"""
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        # 应该返回 True
        self.assertTrue(loader.validate())
    
    def test_validate_missing_serial(self):
        """测试验证缺少串口配置的配置"""
        loader = ConfigLoader()
        loader.config = {
            'devices': []
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('serial', str(context.exception))
    
    def test_validate_missing_devices(self):
        """测试验证缺少设备配置的配置"""
        loader = ConfigLoader()
        loader.config = {
            'serial': {'port': 'COM3'}
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('devices', str(context.exception))
    
    def test_validate_empty_devices(self):
        """测试验证设备列表为空的配置"""
        loader = ConfigLoader()
        loader.config = {
            'serial': {'port': 'COM3'},
            'devices': []
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('未配置任何设备', str(context.exception))
    
    def test_validate_device_missing_name(self):
        """测试验证设备缺少名称的配置"""
        loader = ConfigLoader()
        loader.config = {
            'serial': {'port': 'COM3'},
            'devices': [
                {'type': 'pressure_sensor', 'address': 1}
            ]
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('name', str(context.exception))
    
    def test_validate_device_missing_type(self):
        """测试验证设备缺少类型的配置"""
        loader = ConfigLoader()
        loader.config = {
            'serial': {'port': 'COM3'},
            'devices': [
                {'name': '设备1', 'address': 1}
            ]
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('type', str(context.exception))
    
    def test_validate_device_missing_address(self):
        """测试验证设备缺少地址的配置"""
        loader = ConfigLoader()
        loader.config = {
            'serial': {'port': 'COM3'},
            'devices': [
                {'name': '设备1', 'type': 'pressure_sensor'}
            ]
        }
        
        # 应该抛出异常
        with self.assertRaises(ValueError) as context:
            loader.validate()
        
        self.assertIn('address', str(context.exception))
    
    def test_save_config(self):
        """测试保存配置"""
        # 创建初始配置
        ConfigLoader.create_template(self.test_config_path)
        loader = ConfigLoader(self.test_config_path)
        
        # 修改配置
        loader.config['serial']['baudrate'] = 19200
        
        # 保存配置
        save_path = os.path.join(self.temp_dir, 'saved_config.yaml')
        loader.save(loader.config, save_path)
        
        # 验证文件已创建
        self.assertTrue(os.path.exists(save_path))
        
        # 验证可以重新加载
        new_loader = ConfigLoader(save_path)
        self.assertEqual(new_loader.config['serial']['baudrate'], 19200)
        
        # 清理
        os.remove(save_path)
    
    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        loader = ConfigLoader()
        
        # 应该抛出异常
        with self.assertRaises(Exception) as context:
            loader.load('nonexistent_file.yaml')
        
        self.assertIn('加载配置文件失败', str(context.exception))
    
    def test_init_with_path(self):
        """测试使用路径初始化"""
        ConfigLoader.create_template(self.test_config_path)
        
        # 使用路径初始化
        loader = ConfigLoader(self.test_config_path)
        
        # 验证配置已加载
        self.assertIsNotNone(loader.config)
        self.assertEqual(loader.config_path, self.test_config_path)
    
    def test_init_without_path(self):
        """测试不使用路径初始化"""
        loader = ConfigLoader()
        
        # 验证配置为空
        self.assertIsNone(loader.config)
        self.assertIsNone(loader.config_path)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigLoader)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

