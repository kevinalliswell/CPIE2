#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备驱动类
整合所有支持的Modbus设备
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import time
import threading


class BaseDevice(ABC):
    """设备基类"""
    
    def __init__(self, name: str, address: int, client: ModbusSerialClient, **kwargs):
        """
        初始化设备
        
        Args:
            name: 设备名称
            address: Modbus地址
            client: Modbus客户端
            **kwargs: 其他参数
        """
        self.name = name
        self.address = address
        self.client = client
        self.enabled = kwargs.get('enabled', True)
        self.last_error = None
        self.error_count = 0
        self.last_read_time = None
        self.last_data = None
        self.poll_interval = float(kwargs.get('poll_interval', 1.0))
        self.io_lock = kwargs.get('io_lock') or threading.RLock()

    def _request(self, method, *args, **kwargs):
        # All devices on the serial bus share this lock.
        with self.io_lock:
            return getattr(self.client, method)(*args, **kwargs)
    
    @abstractmethod
    def read_data(self) -> Optional[Dict[str, Any]]:
        """读取设备数据"""
        pass
    
    @abstractmethod
    def write_control(self, control_data: Dict[str, Any]) -> bool:
        """写入控制命令"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        return {
            'name': self.name,
            'address': self.address,
            'enabled': self.enabled,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'last_read_time': self.last_read_time
        }


class PressureSensorDevice(BaseDevice):
    """智能数显压力表设备"""
    
    UNIT_NAMES = {1: 'KPa', 2: 'MPa', 3: 'PSI', 4: 'KgF/cm²'}
    
    def __init__(self, name: str, address: int, client: ModbusSerialClient, **kwargs):
        super().__init__(name, address, client, **kwargs)
        self.current_unit = None
        self.decimal_point = None
        self._init_device_info()
    
    def _init_device_info(self):
        """初始化设备信息"""
        try:
            # 读取单位和小数点
            result = self._request("read_holding_registers",
                address=0x000C, count=1, slave=self.address)
            if not result.isError():
                self.current_unit = result.registers[0]
            
            result = self._request("read_holding_registers",
                address=0x0001, count=1, slave=self.address)
            if not result.isError():
                self.decimal_point = result.registers[0]
        except Exception:
            pass
    
    def read_data(self) -> Optional[Dict[str, Any]]:
        """读取压力数据"""
        try:
            # 读取PV和NDOT
            result = self._request("read_holding_registers",
                address=0x0000, count=2, slave=self.address)
            
            if result.isError():
                self.last_error = "读取失败"
                self.error_count += 1
                return None
            
            raw_value = result.registers[0]
            decimal_point = result.registers[1]
            
            # 计算实际压力值
            pressure = self._apply_decimal_point(raw_value, decimal_point)
            
            data = {
                'device': self.name,
                'type': 'pressure_sensor',
                'raw_value': raw_value,
                'pressure': pressure,
                'unit': self.UNIT_NAMES.get(self.current_unit, 'Unknown'),
                'decimal_point': decimal_point,
                'timestamp': time.time()
            }
            
            self.last_data = data
            self.last_read_time = time.time()
            self.error_count = 0
            self.last_error = None
            
            return data
            
        except Exception as e:
            self.last_error = str(e)
            self.error_count += 1
            return None
    
    def write_control(self, control_data: Dict[str, Any]) -> bool:
        """
        写入控制参数
        
        支持的控制:
        - set_alarm1: {'threshold': value, 'hysteresis': value}
        - set_alarm2: {'threshold': value, 'hysteresis': value}
        """
        try:
            if 'set_alarm1' in control_data:
                alarm = control_data['set_alarm1']
                threshold = alarm.get('threshold')
                hysteresis = alarm.get('hysteresis')
                
                if threshold is not None:
                    threshold_raw = self._reverse_decimal_point(
                        threshold, self.decimal_point or 0)
                    values = [threshold_raw]
                    
                    if hysteresis is not None:
                        hysteresis_raw = self._reverse_decimal_point(
                            hysteresis, self.decimal_point or 0)
                        values.append(hysteresis_raw)
                    
                    result = self._request("write_registers",
                        address=0x0002, values=values, slave=self.address)
                    
                    return not result.isError()
            
            if 'set_alarm2' in control_data:
                alarm = control_data['set_alarm2']
                threshold = alarm.get('threshold')
                hysteresis = alarm.get('hysteresis')
                
                if threshold is not None:
                    threshold_raw = self._reverse_decimal_point(
                        threshold, self.decimal_point or 0)
                    values = [threshold_raw]
                    
                    if hysteresis is not None:
                        hysteresis_raw = self._reverse_decimal_point(
                            hysteresis, self.decimal_point or 0)
                        values.append(hysteresis_raw)
                    
                    result = self._request("write_registers",
                        address=0x0004, values=values, slave=self.address)
                    
                    return not result.isError()
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
    
    @staticmethod
    def _apply_decimal_point(raw_value, decimal_point):
        """应用小数点"""
        if decimal_point == 0:
            return float(raw_value)
        elif decimal_point == 1:
            return raw_value / 10.0
        elif decimal_point == 2:
            return raw_value / 100.0
        elif decimal_point == 3:
            return raw_value / 1000.0
        return float(raw_value)
    
    @staticmethod
    def _reverse_decimal_point(value, decimal_point):
        """反向计算原始值"""
        if decimal_point == 0:
            return int(value)
        elif decimal_point == 1:
            return int(value * 10)
        elif decimal_point == 2:
            return int(value * 100)
        elif decimal_point == 3:
            return int(value * 1000)
        return int(value)


class RelayControllerDevice(BaseDevice):
    """继电器控制器设备"""
    
    def __init__(self, name: str, address: int, client: ModbusSerialClient, **kwargs):
        super().__init__(name, address, client, **kwargs)
        self.relay_states = {0x41: False, 0x42: False, 0x43: False, 0x44: False}
    
    def read_data(self) -> Optional[Dict[str, Any]]:
        """读取继电器状态（通过读取线圈状态）"""
        try:
            states = {}
            for addr in [0x41, 0x42, 0x43, 0x44]:
                result = self._request("read_coils",
                    address=addr, count=1, slave=self.address)
                
                if result.isError() or not result.bits:
                    self.last_error = f'继电器 {addr - 0x40} 状态读取失败'
                    self.error_count += 1
                    return None
                states[f'relay_{addr-0x40}'] = result.bits[0]
                self.relay_states[addr] = result.bits[0]
            
            data = {
                'device': self.name,
                'type': 'relay_controller',
                'relays': states,
                'timestamp': time.time()
            }
            
            self.last_data = data
            self.last_read_time = time.time()
            self.error_count = 0
            self.last_error = None
            
            return data
            
        except Exception as e:
            self.last_error = str(e)
            self.error_count += 1
            return None
    
    def write_control(self, control_data: Dict[str, Any]) -> bool:
        """
        写入继电器控制
        
        支持的控制:
        - set_relay: {'relay': 1-4, 'state': True/False}
        - set_all: {'states': [True, False, True, False]}
        """
        try:
            if 'set_relay' in control_data:
                relay = control_data['set_relay']
                relay_num = relay.get('relay')
                state = relay.get('state')
                
                if relay_num and 1 <= relay_num <= 4:
                    addr = 0x40 + relay_num
                    result = self._request("write_coil",
                        address=addr, value=state, slave=self.address)
                    
                    if not result.isError():
                        self.relay_states[addr] = state
                    
                    return not result.isError()
            
            if 'set_all' in control_data:
                states = control_data['set_all'].get('states', [])
                if len(states) == 4:
                    success = True
                    for i, state in enumerate(states):
                        addr = 0x41 + i
                        result = self._request("write_coil",
                            address=addr, value=state, slave=self.address)
                        if result.isError():
                            success = False
                        else:
                            self.relay_states[addr] = state
                    return success
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False


class TemperatureSensorDevice(BaseDevice):
    """温度采集模块设备"""
    
    TEMP_MIN = -40.0
    TEMP_MAX = 1300.0
    DATA_MAX = 65535
    
    def __init__(self, name: str, address: int, client: ModbusSerialClient, **kwargs):
        super().__init__(name, address, client, **kwargs)
        self.num_channels = kwargs.get('num_channels', 8)
    
    def read_data(self) -> Optional[Dict[str, Any]]:
        """读取温度数据"""
        try:
            # 读取所有通道
            result = self._request("read_input_registers",
                address=0x0000, count=self.num_channels, slave=self.address)
            
            if result.isError():
                self.last_error = "读取失败"
                self.error_count += 1
                return None
            
            channels = []
            for i, raw_value in enumerate(result.registers):
                temperature = self._raw_to_temperature(raw_value)
                channels.append({
                    'channel': i,
                    'raw_value': raw_value,
                    'temperature': temperature,
                    'unit': '°C'
                })
            
            data = {
                'device': self.name,
                'type': 'temperature_sensor',
                'channels': channels,
                'timestamp': time.time()
            }
            
            self.last_data = data
            self.last_read_time = time.time()
            self.error_count = 0
            self.last_error = None
            
            return data
            
        except Exception as e:
            self.last_error = str(e)
            self.error_count += 1
            return None
    
    def write_control(self, control_data: Dict[str, Any]) -> bool:
        """温度传感器不支持写入控制"""
        return True
    
    def _raw_to_temperature(self, raw_value):
        """原始值转温度"""
        if raw_value < 0 or raw_value > 65535:
            return None
        temp_range = self.TEMP_MAX - self.TEMP_MIN
        temperature = (raw_value / self.DATA_MAX) * temp_range + self.TEMP_MIN
        return round(temperature, 2)


class YudianControllerDevice(BaseDevice):
    """宇电温控仪表设备"""
    
    def __init__(self, name: str, address: int, client: ModbusSerialClient, **kwargs):
        super().__init__(name, address, client, **kwargs)
        self.decimal_point = None
        self.scale_factor = 1
        self._init_decimal_point()
    
    def _init_decimal_point(self):
        """初始化小数点"""
        try:
            result = self._request("read_holding_registers",
                address=0x0C, count=1, slave=self.address)
            if not result.isError():
                value = result.registers[0]
                if value >= 128:
                    self.scale_factor = 10
                    self.decimal_point = value - 128
                else:
                    self.scale_factor = 1
                    self.decimal_point = value
        except Exception:
            self.decimal_point = 1
    
    def read_data(self) -> Optional[Dict[str, Any]]:
        """读取测量值、给定值和输出值"""
        try:
            # 读取PV, SV, MV
            result = self._request("read_holding_registers",
                address=0x4A, count=3, slave=self.address)
            
            if result.isError():
                self.last_error = "读取失败"
                self.error_count += 1
                return None
            
            pv_raw = result.registers[0]
            sv_raw = result.registers[1]
            mv_raw = result.registers[2]
            
            # 转换有符号数
            pv_raw = pv_raw if pv_raw < 32768 else pv_raw - 65536
            sv_raw = sv_raw if sv_raw < 32768 else sv_raw - 65536
            
            # 转换实际值
            pv = self._convert_value(pv_raw)
            sv = self._convert_value(sv_raw)
            mv = mv_raw / 256.0  # 输出百分比
            
            data = {
                'device': self.name,
                'type': 'yudian_controller',
                'pv': pv,  # 测量值
                'sv': sv,  # 给定值
                'mv': mv,  # 输出值(%)
                'timestamp': time.time()
            }
            
            self.last_data = data
            self.last_read_time = time.time()
            self.error_count = 0
            self.last_error = None
            
            return data
            
        except Exception as e:
            self.last_error = str(e)
            self.error_count += 1
            return None
    
    def write_control(self, control_data: Dict[str, Any]) -> bool:
        """
        写入控制参数
        
        支持的控制:
        - set_setpoint: {'value': float}
        - set_run_status: {'status': 'run'/'StoP'/'HoLd'}
        - set_pid: {'P': float, 'I': int, 'D': float}
        - set_program_segments: {'segments': [[温度, 时间], ...]}
        """
        try:
            if 'set_setpoint' in control_data:
                value = control_data['set_setpoint']['value']
                int_value = int(self._convert_value(value, is_write=True))
                if int_value < 0:
                    int_value = 65536 + int_value
                
                result = self._request("write_register",
                    address=0x00, value=int_value, slave=self.address)
                
                if result.isError():
                    return False
            
            if 'set_run_status' in control_data:
                status_map = {'run': 0, 'StoP': 1, 'HoLd': 2}
                status = control_data['set_run_status']['status']
                if status in status_map:
                    result = self._request("write_register",
                        address=0x1B, value=status_map[status], 
                        slave=self.address)
                    
                    if result.isError():
                        return False
            
            if 'set_pid' in control_data:
                pid = control_data['set_pid']
                
                if 'P' in pid:
                    p_value = int(self._convert_value(pid['P'], is_write=True))
                    self._request("write_register",
                        address=0x07, value=p_value, slave=self.address)
                
                if 'I' in pid:
                    self._request("write_register",
                        address=0x08, value=int(pid['I']), slave=self.address)
                
                if 'D' in pid:
                    self._request("write_register",
                        address=0x09, value=int(pid['D']), slave=self.address)
            
            if 'set_program_segments' in control_data:
                segments = control_data['set_program_segments']['segments']
                # 1. 设置程序段数(Pno)到地址0x2B
                seg_count = len(segments)
                result = self._request("write_register",
                    address=0x2B, value=seg_count, slave=self.address)
                
                if result.isError():
                    print(f"✗ 写入程序段数量失败: address=0x2B, value={seg_count}")
                    return False
                
                print(f"✓ 程序段数量已写入: {seg_count}段")
                time.sleep(0.1)
                
                # 验证程序段数量
                verify_result = self._request("read_holding_registers",
                    address=0x2B, count=1, slave=self.address)
                if not verify_result.isError():
                    read_count = verify_result.registers[0]
                    if read_count == seg_count:
                        print(f"✓ 程序段数量验证成功: {read_count}")
                    else:
                        print(f"⚠ 程序段数量验证失败: 写入{seg_count}, 读取{read_count}")
                else:
                    print("⚠ 无法验证程序段数量")
                
                time.sleep(0.1)
                
                # 2. 写入每个程序段的温度和时间到0x50开始的地址
                for i, (sp, t) in enumerate(segments):
                    sp_value = int(self._convert_value(sp, is_write=True))
                    if sp_value < 0:
                        sp_value = 65536 + sp_value
                    
                    sp_addr = 0x50 + i * 2
                    t_addr = sp_addr + 1
                    
                    # 写入温度
                    result = self._request("write_register",
                        sp_addr, sp_value, slave=self.address)
                    if result.isError():
                        print(f"✗ 写入程序段{i+1}温度失败: address=0x{sp_addr:02X}, value={sp_value} ({sp}°C)")
                        return False
                    
                    time.sleep(0.02)
                    
                    # 验证温度
                    verify_sp = self._request("read_holding_registers",
                        address=sp_addr, count=1, slave=self.address)
                    if not verify_sp.isError():
                        read_sp = verify_sp.registers[0]
                        if read_sp >= 32768:
                            read_sp = read_sp - 65536
                        read_temp = self._convert_value(read_sp, is_write=False)
                        if abs(read_temp - sp) < 1.0:  # 允许小数点误差
                            print(f"  ✓ 程序段{i+1}温度验证成功: {read_temp}°C")
                        else:
                            print(f"  ⚠ 程序段{i+1}温度验证失败: 写入{sp}°C, 读取{read_temp}°C")
                    
                    time.sleep(0.02)
                    
                    # 写入时间
                    t_value = int(t) if t >= 0 else 65536 + int(t)
                    result = self._request("write_register",
                        t_addr, t_value, slave=self.address)
                    if result.isError():
                        print(f"✗ 写入程序段{i+1}时间失败: address=0x{t_addr:02X}, value={t_value} ({t}分钟)")
                        return False
                    
                    time.sleep(0.02)
                    
                    # 验证时间
                    verify_t = self._request("read_holding_registers",
                        address=t_addr, count=1, slave=self.address)
                    if not verify_t.isError():
                        read_t = verify_t.registers[0]
                        if read_t >= 32768:
                            read_t = read_t - 65536
                        if read_t == t:
                            print(f"  ✓ 程序段{i+1}时间验证成功: {read_t}分钟")
                        else:
                            print(f"  ⚠ 程序段{i+1}时间验证失败: 写入{t}分钟, 读取{read_t}分钟")
                    
                    print(f"✓ 程序段{i+1}已写入: 温度={sp}°C, 时间={t}分钟")
                    time.sleep(0.05)
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def _convert_value(self, value, is_write=False):
        """转换数值"""
        if self.decimal_point is None:
            return value
        
        if is_write:
            value = int(value * (10 ** self.decimal_point))
            value = int(value * self.scale_factor)
        else:
            value = value / self.scale_factor
            value = value / (10 ** self.decimal_point)
        return value


# 设备类型映射
DEVICE_TYPES = {
    'pressure_sensor': PressureSensorDevice,
    'relay_controller': RelayControllerDevice,
    'temperature_sensor': TemperatureSensorDevice,
    'yudian_controller': YudianControllerDevice
}
