#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装验证脚本
用于验证 modbus_multi_device 包是否正确安装
"""

import sys
import importlib


def check_import(module_name):
    """检查模块是否可以导入"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        return False


def main():
    """主验证函数"""
    print("=" * 60)
    print("Modbus Multi-Device 安装验证")
    print("=" * 60)
    
    success = True
    
    # 检查依赖包
    print("\n1. 检查依赖包:")
    dependencies = [
        'serial',      # pyserial
        'pymodbus',
        'yaml',        # PyYAML
    ]
    
    for dep in dependencies:
        if not check_import(dep):
            success = False
    
    # 检查主包
    print("\n2. 检查主包:")
    if not check_import('modbus_multi_device'):
        success = False
        print("\n✗ 主包导入失败!")
        print("请运行: pip install -e .")
        return False
    
    # 检查主要模块
    print("\n3. 检查主要模块:")
    modules = [
        'modbus_multi_device.manager',
        'modbus_multi_device.devices',
        'modbus_multi_device.config',
        'modbus_multi_device.poller',
    ]
    
    for module in modules:
        if not check_import(module):
            success = False
    
    # 检查主要类
    print("\n4. 检查主要类:")
    try:
        from modbus_multi_device import (
            ModbusDeviceManager,
            ConfigLoader,
            PressureSensorDevice,
            RelayControllerDevice,
            TemperatureSensorDevice,
            YudianControllerDevice,
            DataPoller,
            ControlExecutor
        )
        print("✓ 所有主要类可以导入")
    except ImportError as e:
        print(f"✗ 类导入失败: {e}")
        success = False
    
    # 检查版本
    print("\n5. 检查版本信息:")
    try:
        import modbus_multi_device
        version = modbus_multi_device.__version__
        author = modbus_multi_device.__author__
        print(f"✓ 版本: {version}")
        print(f"✓ 作者: {author}")
    except Exception as e:
        print(f"✗ 版本信息获取失败: {e}")
        success = False
    
    # 测试配置加载
    print("\n6. 测试配置加载器:")
    try:
        from modbus_multi_device import ConfigLoader
        import tempfile
        import os
        
        # 创建临时配置文件
        temp_file = os.path.join(tempfile.gettempdir(), 'test_config.yaml')
        ConfigLoader.create_template(temp_file)
        
        # 加载配置
        loader = ConfigLoader(temp_file)
        loader.validate()
        
        # 清理
        os.remove(temp_file)
        
        print("✓ 配置加载器工作正常")
    except Exception as e:
        print(f"✗ 配置加载器测试失败: {e}")
        success = False
    
    # 总结
    print("\n" + "=" * 60)
    if success:
        print("✓ 所有检查通过! 安装成功!")
        print("\n下一步:")
        print("1. 查看示例: python examples/example_usage.py")
        print("2. 运行测试: python tests/test_config.py")
        print("3. 阅读文档: readme.md 和 api_doc.md")
    else:
        print("✗ 部分检查失败! 请检查安装")
        print("\n请尝试:")
        print("1. pip install -r requirements.txt")
        print("2. pip install -e .")
    print("=" * 60)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

