#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据轮询器和控制执行器
实现数据采集轮询机制和控制优先级
"""

import time
import threading
import queue
from concurrent.futures import Future, TimeoutError, CancelledError
from contextlib import nullcontext
from copy import deepcopy
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
        self._stop_event = threading.Event()
        
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
        self._stop_event.clear()
        
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
        self._stop_event.set()
        
        # 等待所有线程结束
        for thread in self.device_threads.values():
            thread.join(timeout=2.0)
        
        stopped = not any(t.is_alive() for t in self.device_threads.values())
        if stopped:
            self.device_threads.clear()
        return stopped
    
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
                with getattr(device, "io_lock", nullcontext()):
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
            self._stop_event.wait(interval)
    
    def get_status(self) -> Dict[str, Any]:
        """获取轮询器状态"""
        return {
            'running': self.running,
            'active_threads': len([t for t in self.device_threads.values() if t.is_alive()]),
            'devices_count': len(self.devices),
            'enabled_devices': len([d for d in self.devices if d.enabled])
        }


class ControlExecutor:
    """One serial writer with completion results and a per-device safety barrier."""

    PRIORITY_HIGH = 1
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 10

    def __init__(self, devices: List, max_queue_size: int = 100):
        self.devices = {d.name: d for d in devices}
        self.control_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.running = False
        self.executor_thread = None
        self.result_callbacks = []
        self.counter = 0
        self._lock = threading.RLock()
        self._blocked_devices = set()
        self._safety_futures = {}

    def add_result_callback(self, callback):
        self.result_callbacks.append(callback)

    def start(self):
        with self._lock:
            if self.running:
                return
            if self.executor_thread and self.executor_thread.is_alive():
                raise RuntimeError("Previous control executor has not stopped")
            self.running = True
            self.executor_thread = threading.Thread(target=self._execute_loop,
                                                    daemon=True, name="ControlExecutor")
            self.executor_thread.start()

    def _cancel_pending(self, device_name=None):
        """Called under _lock, before placing the OFF barrier in the same queue."""
        keep = []
        while True:
            try:
                entry = self.control_queue.get_nowait()
            except queue.Empty:
                break
            item = entry[2]
            self.control_queue.task_done()
            if device_name is None or item['device_name'] == device_name:
                item['future'].cancel()
            else:
                keep.append(entry)
        for entry in keep:
            self.control_queue.put_nowait(entry)

    def stop(self, timeout=2.0):
        with self._lock:
            self.running = False
            self._cancel_pending()
        if self.executor_thread and self.executor_thread is not threading.current_thread():
            self.executor_thread.join(timeout)
        return not (self.executor_thread and self.executor_thread.is_alive())

    def _submit(self, device_name, control_data, priority, timeout, safety=False, verify_relays=False):
        with self._lock:
            if not self.running or device_name not in self.devices:
                return None
            if not safety and device_name in self._blocked_devices:
                return None
            future = Future()
            item = {'device_name': device_name, 'control_data': deepcopy(control_data),
                    'deadline': time.monotonic() + timeout, 'future': future,
                    'safety': safety, 'verify_relays': verify_relays, 'priority': priority}
            try:
                self.control_queue.put_nowait((priority, self.counter, item))
                self.counter += 1
                return future
            except queue.Full:
                return None

    def submit_control(self, device_name, control_data, priority=None, timeout=5.0):
        """Return queue admission only. Use submit_and_wait for execution results."""
        if priority is None:
            priority = self.PRIORITY_NORMAL
        return self._submit(device_name, control_data, priority, timeout) is not None

    def submit_high_priority(self, device_name, control_data):
        return self.submit_control(device_name, control_data, self.PRIORITY_HIGH)

    def submit_low_priority(self, device_name, control_data):
        return self.submit_control(device_name, control_data, self.PRIORITY_LOW)

    @staticmethod
    def _wait_result(future, timeout, cancel_on_timeout=True):
        if future is None:
            return False
        try:
            return bool(future.result(timeout=timeout)['success'])
        except (TimeoutError, CancelledError):
            # A running I/O cannot be canceled. The OFF barrier still executes
            # after it; callers must keep the executor alive on shutdown failure.
            if cancel_on_timeout:
                future.cancel()
            return False

    def submit_and_wait(self, device_name, control_data, timeout=5.0):
        future = self._submit(device_name, control_data, self.PRIORITY_HIGH, timeout)
        return self._wait_result(future, timeout)

    def shutdown_relays(self, device_name, timeout=5.0):
        return self.shutdown_control(device_name, {'set_all': {'states': [False] * 4}},
                                     timeout=timeout, verify_relays=True)

    def shutdown_control(self, device_name, control_data, timeout=5.0, verify_relays=False):
        with self._lock:
            self._blocked_devices.add(device_name)
            future = self._safety_futures.get(device_name)
            if future is None or future.done():
                self._cancel_pending(device_name)
                future = self._submit(device_name, control_data, 0, timeout,
                                      safety=True, verify_relays=verify_relays)
                self._safety_futures[device_name] = future
        return self._wait_result(future, timeout, cancel_on_timeout=False)

    def resume_controls(self, device_name):
        with self._lock:
            if not self.running or device_name not in self.devices:
                return False
            future = self._safety_futures.get(device_name)
            if device_name in self._blocked_devices:
                if future is None or not future.done() or future.cancelled():
                    return False
                if not future.result()['success']:
                    return False
            self._blocked_devices.discard(device_name)
            self._safety_futures.pop(device_name, None)
            return True

    def _execute_item(self, item):
        device = self.devices[item['device_name']]
        result = {'device_name': item['device_name'], 'control_data': item['control_data'],
                  'success': False, 'error': None, 'timestamp': datetime.now().isoformat(),
                  'priority': item['priority']}
        try:
            with getattr(device, 'io_lock', nullcontext()):
                if time.monotonic() > item['deadline'] and not item['safety']:
                    result['error'] = '控制命令超时'
                    return result
                success = bool(device.write_control(item['control_data']))
                if success and item['verify_relays']:
                    readback = device.read_data()
                    relays = readback.get('relays', {}) if readback else {}
                    success = all(relays.get(f'relay_{i}') is False for i in range(1, 5))
                    if success:
                        result['readback'] = readback
                    else:
                        result['error'] = '未确认全部继电器已关闭'
                result['success'] = success
                if not success and result['error'] is None:
                    result['error'] = device.last_error or '设备拒绝控制命令'
        except Exception as exc:
            result['error'] = str(exc)
        return result

    def _execute_loop(self):
        while self.running:
            try:
                _, _, item = self.control_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                with self._lock:
                    if not self.running or (item['device_name'] in self._blocked_devices and not item['safety']):
                        item['future'].cancel()
                    admitted = item['future'].set_running_or_notify_cancel()
                if not admitted:
                    continue
                result = self._execute_item(item)
                item['future'].set_result(result)
                self._notify_result(result)
            finally:
                self.control_queue.task_done()

    def _notify_result(self, result):
        for callback in self.result_callbacks:
            try:
                callback(result)
            except Exception as exc:
                print(f"结果回调错误: {exc}")

    def get_status(self):
        return {'running': self.running, 'queue_size': self.control_queue.qsize(),
                'devices_count': len(self.devices)}

    def get_queue_size(self):
        return self.control_queue.qsize()
