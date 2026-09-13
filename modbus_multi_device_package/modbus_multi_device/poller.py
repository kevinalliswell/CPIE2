#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据轮询器和控制执行器
实现数据采集轮询机制和控制优先级
"""

import time
import threading
import queue
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime


class DataPoller:
    """数据轮询器 - 负责定时采集设备数据"""
    
    def __init__(self, devices: List, default_interval: float = 1.0):
        """
        初始化数据轮询器
        
        Args:
            devices: 设备列表
            default_interval: 默认轮询间隔（秒）
        """
        self.devices = devices
        self.default_interval = default_interval
        self.running = False
        self.threads = []
        self.data_callbacks = []
        self.error_callbacks = []
        
        # 为每个设备创建独立的轮询线程
        self.device_threads = {}
        
    def add_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加数据回调函数
        
        Args:
            callback: 回调函数，参数为设备数据字典
        """
        self.data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """
        添加错误回调函数
        
        Args:
            callback: 回调函数，参数为(设备名称, 异常对象)
        """
        self.error_callbacks.append(callback)
    
    def start(self):
        """启动轮询"""
        if self.running:
            return
        
        self.running = True
        
        # 为每个启用的设备创建轮询线程
        for device in self.devices:
            if device.enabled:
                interval = getattr(device, 'poll_interval', self.default_interval)
                thread = threading.Thread(
                    target=self._poll_device,
                    args=(device, interval),
                    daemon=True,
                    name=f"Poller-{device.name}"
                )
                thread.start()
                self.device_threads[device.name] = thread
    
    def stop(self):
        """停止轮询"""
        self.running = False
        
        # 等待所有线程结束
        for thread in self.device_threads.values():
            thread.join(timeout=2.0)
        
        self.device_threads.clear()
    
    def _poll_device(self, device, interval: float):
        """
        轮询单个设备
        
        Args:
            device: 设备对象
            interval: 轮询间隔
        """
        while self.running:
            try:
                # 读取设备数据
                data = device.read_data()
                
                if data:
                    # 调用数据回调
                    for callback in self.data_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"数据回调错误: {e}")
                else:
                    # 调用错误回调
                    for callback in self.error_callbacks:
                        try:
                            callback(device.name, Exception(device.last_error))
                        except Exception as e:
                            print(f"错误回调错误: {e}")
                
            except Exception as e:
                # 调用错误回调
                for callback in self.error_callbacks:
                    try:
                        callback(device.name, e)
                    except Exception as err:
                        print(f"错误回调错误: {err}")
            
            # 等待下一次轮询
            time.sleep(interval)
    
    def get_status(self) -> Dict[str, Any]:
        """获取轮询器状态"""
        return {
            'running': self.running,
            'active_threads': len([t for t in self.device_threads.values() if t.is_alive()]),
            'devices_count': len(self.devices),
            'enabled_devices': len([d for d in self.devices if d.enabled])
        }


class ControlExecutor:
    """控制执行器 - 负责执行控制命令（具有优先权）"""
    
    def __init__(self, devices: List, max_queue_size: int = 100):
        """
        初始化控制执行器
        
        Args:
            devices: 设备列表
            max_queue_size: 最大队列长度
        """
        self.devices = {d.name: d for d in devices}
        self.control_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.running = False
        self.executor_thread = None
        self.result_callbacks = []
        
        # 优先级定义
        self.PRIORITY_HIGH = 1
        self.PRIORITY_NORMAL = 5
        self.PRIORITY_LOW = 10
        
        # 计数器，用于优先队列中相同优先级的排序
        self.counter = 0
        self.counter_lock = threading.Lock()
    
    def add_result_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加结果回调函数
        
        Args:
            callback: 回调函数，参数为结果字典
        """
        self.result_callbacks.append(callback)
    
    def start(self):
        """启动控制执行器"""
        if self.running:
            return
        
        self.running = True
        self.executor_thread = threading.Thread(
            target=self._execute_loop,
            daemon=True,
            name="ControlExecutor"
        )
        self.executor_thread.start()
    
    def stop(self, flush_timeout: float = 3.0):
        """
        停止控制执行器

        停止前会在 flush_timeout 秒内等待队列中尚未执行的控制命令执行完毕
        （例如实验停止/程序退出时下发的"关闭全部继电器"命令），
        避免这些安全相关的命令被直接丢弃。

        Args:
            flush_timeout: 等待队列清空的最长时间（秒），<=0 表示不等待直接丢弃
        """
        if (flush_timeout > 0 and self.running and self.executor_thread
                and self.executor_thread.is_alive()):
            deadline = time.time() + flush_timeout
            while not self.control_queue.empty() and time.time() < deadline:
                time.sleep(0.01)
            if not self.control_queue.empty():
                print(f"控制执行器停止: 超时后仍有 {self.control_queue.qsize()} 条命令未执行，已丢弃")

        self.running = False

        # 清空残留队列
        while not self.control_queue.empty():
            try:
                self.control_queue.get_nowait()
            except queue.Empty:
                break

        if self.executor_thread:
            self.executor_thread.join(timeout=2.0)
    
    def submit_control(self, device_name: str, control_data: Dict[str, Any],
                      priority: int = None, timeout: float = 5.0) -> bool:
        """
        提交控制命令
        
        Args:
            device_name: 设备名称
            control_data: 控制数据
            priority: 优先级（数字越小优先级越高），None使用NORMAL
            timeout: 超时时间
            
        Returns:
            是否成功加入队列
        """
        if device_name not in self.devices:
            return False
        
        if priority is None:
            priority = self.PRIORITY_NORMAL
        
        control_item = {
            'device_name': device_name,
            'control_data': control_data,
            'timestamp': time.time(),
            'timeout': timeout
        }
        
        try:
            # 使用计数器确保相同优先级时按提交顺序排序
            with self.counter_lock:
                count = self.counter
                self.counter += 1
            
            self.control_queue.put((priority, count, control_item), block=False)
            return True
        except queue.Full:
            return False
    
    def submit_high_priority(self, device_name: str, control_data: Dict[str, Any]) -> bool:
        """提交高优先级控制命令"""
        return self.submit_control(device_name, control_data, 
                                   priority=self.PRIORITY_HIGH)
    
    def submit_low_priority(self, device_name: str, control_data: Dict[str, Any]) -> bool:
        """提交低优先级控制命令"""
        return self.submit_control(device_name, control_data,
                                   priority=self.PRIORITY_LOW)
    
    def _execute_loop(self):
        """控制执行循环"""
        while self.running:
            try:
                # 获取控制命令（带超时）- 解包三元组 (priority, count, control_item)
                priority, count, control_item = self.control_queue.get(timeout=0.5)
                
                device_name = control_item['device_name']
                control_data = control_item['control_data']
                submit_time = control_item['timestamp']
                timeout = control_item['timeout']
                
                # 检查超时
                if time.time() - submit_time > timeout:
                    result = {
                        'device_name': device_name,
                        'success': False,
                        'error': '控制命令超时',
                        'timestamp': datetime.now().isoformat()
                    }
                    self._notify_result(result)
                    continue
                
                # 执行控制
                device = self.devices.get(device_name)
                if device:
                    try:
                        success = device.write_control(control_data)
                        
                        result = {
                            'device_name': device_name,
                            'control_data': control_data,
                            'success': success,
                            'error': None if success else device.last_error,
                            'timestamp': datetime.now().isoformat(),
                            'priority': priority
                        }
                        
                        self._notify_result(result)
                        
                    except Exception as e:
                        result = {
                            'device_name': device_name,
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                        self._notify_result(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"控制执行器错误: {e}")
    
    def _notify_result(self, result: Dict[str, Any]):
        """通知结果回调"""
        for callback in self.result_callbacks:
            try:
                callback(result)
            except Exception as e:
                print(f"结果回调错误: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            'running': self.running,
            'queue_size': self.control_queue.qsize(),
            'devices_count': len(self.devices)
        }
    
    def get_queue_size(self) -> int:
        """获取队列长度"""
        return self.control_queue.qsize()
