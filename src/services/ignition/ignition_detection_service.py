#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点检测服务
负责检测煤样的着火温度，支持多种检测方法
"""

import time


class IgnitionDetectionService:
    """着火点检测服务"""
    
    def __init__(self, config, tangent_detector=None):
        """
        初始化检测服务
        
        Args:
            config: 配置字典
            tangent_detector: 切线法检测器实例（可选）
        """
        self.config = config
        self.tangent_detector = tangent_detector
        self.last_check_time = time.time()
    
    def check_ignition(self, temp_history: dict, ignition_flags: list, check_interval: float, start_temperature: float = 150.0):
        """
        检测着火点
        
        Args:
            temp_history: 温度历史数据字典 {channel_index: deque}
            ignition_flags: 着火点检测标志列表
            check_interval: 检测间隔（秒）
            start_temperature: 起始温度阈值（只有温度大于此值才开始检测）
        
        Returns:
            list: 检测结果列表 [(channel, temperature, method), ...]
        """
        if not self.config['ignition_detection']['enabled']:
            return []
        
        current_time = time.time()
        
        # 检测间隔控制
        if current_time - self.last_check_time < check_interval:
            return []
        
        self.last_check_time = current_time
        
        criteria = self.config['ignition_detection']['criteria']
        results = []
        
        for i in range(len(ignition_flags)):
            # 跳过已检测到的通道
            if ignition_flags[i]:
                continue
            
            # 确保有足够的数据点
            if not temp_history[i] or len(temp_history[i]) < 5:
                continue
            
            current_temp = temp_history[i][-1]
            
            # 温度阈值检查：只有温度大于起始温度才开始检测
            if current_temp < start_temperature:
                continue
            
            # 方法1: 绝对温度法（可选，默认禁用）
            if criteria.get('absolute_temperature', {}).get('enabled', False):
                threshold = criteria['absolute_temperature']['threshold']
                if current_temp >= threshold:
                    results.append((i, current_temp, "绝对温度"))
                    continue
            
            # 方法2: 温度突升法
            if criteria.get('temperature_rise', {}).get('enabled', False):
                if len(temp_history[i]) >= 10:
                    threshold = criteria['temperature_rise']['threshold']
                    time_window = criteria['temperature_rise']['time_window']
                    
                    # 计算时间窗口内的温升
                    window_size = int(time_window / check_interval)
                    if len(temp_history[i]) >= window_size:
                        temp_rise = current_temp - temp_history[i][-window_size]
                        if temp_rise >= threshold:
                            results.append((i, current_temp, "温度突升"))
                            continue
            
            # 方法3: 温升速率法
            if criteria.get('rise_rate', {}).get('enabled', False):
                if len(temp_history[i]) >= 6:
                    threshold = criteria['rise_rate']['threshold']
                    
                    # 计算温升速率 (最近6个点)
                    time_diff = check_interval * 5
                    temp_diff = current_temp - temp_history[i][-6]
                    rise_rate = temp_diff / time_diff
                    
                    if rise_rate >= threshold:
                        results.append((i, current_temp, "温升速率"))
                        continue
        
        return results
    
    def create_ignition_mark_info(self, channel: int, temperature: float, method: str):
        """
        创建着火点标记信息
        
        Args:
            channel: 通道号
            temperature: 着火温度
            method: 检测方法
        
        Returns:
            dict: 着火点标记信息
        """
        return {
            'channel': channel,
            'temperature': temperature,
            'method': method,
            'label_text': f"着火点: {temperature:.1f}°C ({method})",
            'log_message': f"✓ CH{channel+1} 检测到着火点: {temperature:.1f}°C (方法: {method})"
        }

