#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus Multi-Device Communication Package
多设备Modbus通信管理包

支持设备类型:
- 智能数显压力表 (PressureSensor)
- DAM-3944A 继电器模块 (RelayController)
- DAM-3138 温度采集模块 (TemperatureSensor)
- 宇电AI系列温控仪表 (YudianController)
"""

__version__ = '1.0.1'
__author__ = 'Kevin'

from .manager import ModbusDeviceManager
from .devices import (
    PressureSensorDevice,
    RelayControllerDevice,
    TemperatureSensorDevice,
    YudianControllerDevice
)
from .config import ConfigLoader
from .poller import DataPoller, ControlExecutor

__all__ = [
    'ModbusDeviceManager',
    'PressureSensorDevice',
    'RelayControllerDevice',
    'TemperatureSensorDevice',
    'YudianControllerDevice',
    'ConfigLoader',
    'DataPoller',
    'ControlExecutor'
]
