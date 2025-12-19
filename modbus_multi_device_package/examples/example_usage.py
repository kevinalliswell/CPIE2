#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus Multi-Device 使用示例
演示如何使用包进行多设备通信
"""

import time
import sys
from pathlib import Path

# 添加包路径（如果未安装）
sys.path.insert(0, str(Path(__file__).parent.parent))

from modbus_multi_device import ModbusDeviceManager


def on_data_received(data):
    """数据接收回调函数"""
    device_name = data.get('device_name', 'Unknown')
    device_type = data.get('type', 'Unknown')
    
    print(f"\n[数据回调] 设备: {device_name} ({device_type})")
    
    if device_type == 'pressure_sensor':
        pressure = data.get('pressure', 0)
        print(f"  压力值: {pressure:.2f} kPa")
        
        # 压力超限报警
        if pressure > 900:
            print(f"  ⚠️  警告: 压力超限! ({pressure:.2f} > 900)")
            
    elif device_type == 'temperature_sensor':
        temperatures = data.get('temperatures', {})
        print(f"  温度通道: {len(temperatures)} 个")
        for ch, temp in temperatures.items():
            if temp is not None:
                print(f"    CH{ch}: {temp:.1f}°C")
                
    elif device_type == 'relay_controller':
        relays = data.get('relays', {})
        print(f"  继电器状态: {relays}")
        
    elif device_type == 'yudian_controller':
        pv = data.get('process_value', 0)
        sv = data.get('setpoint', 0)
        print(f"  当前温度: {pv:.1f}°C, 设定值: {sv:.1f}°C")


def on_control_result(result):
    """控制结果回调函数"""
    device_name = result.get('device_name', 'Unknown')
    success = result.get('success', False)
    
    status = "✓ 成功" if success else "✗ 失败"
    print(f"\n[控制回调] 设备: {device_name} - {status}")
    
    if not success:
        error = result.get('error', 'Unknown error')
        print(f"  错误: {error}")


def basic_example():
    """基础示例：数据采集"""
    print("=" * 60)
    print("示例 1: 基础数据采集")
    print("=" * 60)
    
    # 获取配置文件路径
    config_path = Path(__file__).parent / 'example_config.yaml'
    
    # 创建管理器
    manager = ModbusDeviceManager(config_path=str(config_path))
    
    # 添加数据回调
    manager.add_data_callback(on_data_received)
    
    try:
        # 连接设备
        print("\n正在连接设备...")
        if not manager.connect():
            print("✗ 连接失败!")
            return
        
        print("✓ 连接成功!")
        
        # 启动数据采集
        print("\n启动数据采集...")
        manager.start()
        print("✓ 采集已启动，运行 10 秒...")
        
        # 运行一段时间
        time.sleep(10)
        
        # 获取所有设备的最新数据
        print("\n" + "=" * 60)
        print("获取所有设备的最新数据:")
        print("=" * 60)
        all_data = manager.get_latest_data()
        
        for device_name, data in all_data.items():
            print(f"\n设备: {device_name}")
            for key, value in data.items():
                print(f"  {key}: {value}")
        
    finally:
        # 停止并断开
        print("\n正在停止...")
        manager.stop()
        manager.disconnect()
        print("✓ 已停止")


def control_example():
    """控制示例：发送控制命令"""
    print("\n\n" + "=" * 60)
    print("示例 2: 设备控制")
    print("=" * 60)
    
    config_path = Path(__file__).parent / 'example_config.yaml'
    manager = ModbusDeviceManager(config_path=str(config_path))
    
    # 添加控制结果回调
    manager.add_control_callback(on_control_result)
    
    try:
        if not manager.connect():
            print("✗ 连接失败!")
            return
        
        print("✓ 连接成功!")
        manager.start()
        
        # 等待设备初始化
        time.sleep(2)
        
        # 示例1: 控制继电器
        print("\n控制继电器模块 - 开启继电器1...")
        manager.send_control(
            device_name='继电器模块',
            control_data={
                'set_relay': {
                    'relay': 1,
                    'state': True
                }
            },
            priority='high'
        )
        
        time.sleep(2)
        
        # 示例2: 设置压力表报警
        print("\n设置压力表报警阈值...")
        manager.send_control(
            device_name='压力表1',
            control_data={
                'set_alarm1': {
                    'threshold': 500.0,
                    'hysteresis': 10.0
                }
            }
        )
        
        time.sleep(2)
        
        # 示例3: 设置温控仪表
        print("\n设置温控仪表目标温度...")
        manager.send_control(
            device_name='温控仪表',
            control_data={
                'set_setpoint': {
                    'value': 100.0
                }
            }
        )
        
        # 等待控制完成
        time.sleep(3)
        
    finally:
        manager.stop()
        manager.disconnect()
        print("\n✓ 已停止")


def history_example():
    """历史数据示例"""
    print("\n\n" + "=" * 60)
    print("示例 3: 历史数据查询")
    print("=" * 60)
    
    config_path = Path(__file__).parent / 'example_config.yaml'
    manager = ModbusDeviceManager(config_path=str(config_path))
    
    try:
        if not manager.connect():
            print("✗ 连接失败!")
            return
        
        manager.start()
        print("采集数据中，请等待 5 秒...")
        time.sleep(5)
        
        # 获取压力表历史数据
        print("\n查询压力表历史数据（最近5条）:")
        history = manager.get_data_history('压力表1', count=5)
        
        if history:
            for i, data in enumerate(history, 1):
                pressure = data.get('pressure', 0)
                timestamp = data.get('timestamp', 'N/A')
                print(f"  {i}. 时间: {timestamp}, 压力: {pressure:.2f} kPa")
            
            # 计算平均值
            pressures = [d.get('pressure', 0) for d in history]
            avg_pressure = sum(pressures) / len(pressures)
            print(f"\n平均压力: {avg_pressure:.2f} kPa")
        else:
            print("  暂无历史数据")
        
    finally:
        manager.stop()
        manager.disconnect()
        print("\n✓ 已停止")


def main():
    """主函数"""
    print("\nModbus Multi-Device 使用示例")
    print("请确保:")
    print("1. 已正确配置 example_config.yaml")
    print("2. 设备已连接并上电")
    print("3. 串口号和波特率正确")
    print()
    
    try:
        # 运行示例
        basic_example()
        
        # 如果需要测试控制功能，取消下面的注释
        # control_example()
        
        # 如果需要测试历史数据，取消下面的注释
        # history_example()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

