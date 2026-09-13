#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温度条件验证器
负责检查着火点实验的温度条件是否满足要求
"""


import math


class TemperatureConditionValidator:
    """温度条件验证器"""
    
    def __init__(self, config, manager):
        """
        初始化验证器
        
        Args:
            config: 配置字典
            manager: 设备管理器
        """
        self.config = config
        self.manager = manager
    
    def check_start_condition(self):
        """
        检查启动实验的温度条件
        
        Returns:
            tuple: (是否满足, 详细消息)
                - bool: 条件满足返回True，否则返回False
                - str: 详细的检查信息
        """
        try:
            if not self.manager:
                return False, "无法获取设备数据，请检查设备连接状态！"
            
            # 获取当前温度PV值
            controller_data = self.manager.get_latest_data('着火点-温控仪表')
            if controller_data is None:
                return False, "无法获取温控仪表数据，请检查设备连接状态！"
            
            current_pv = controller_data.get('pv')
            if not isinstance(current_pv, (int, float)) or isinstance(current_pv, bool) or not math.isfinite(current_pv):
                return False, "温度数据无效，请检查设备连接状态！"
            
            # 检查温度是否小于采集起始温度
            collect_start_temp = self.config.get('collect_start_temperature', 200.0)
            if current_pv >= collect_start_temp:
                error_msg = f"当前炉温: {current_pv:.1f}°C\n\n"
                error_msg += f"启动实验要求: 炉温必须小于 {collect_start_temp}°C\n\n"
                error_msg += f"请等待炉温降至要求温度后再启动实验。"
                return False, error_msg
            
            # 条件满足
            success_msg = f"温度条件检查通过：当前温度 {current_pv:.1f}°C"
            return True, success_msg
            
        except Exception as e:
            return False, f"检查温度条件时发生异常: {e}"

