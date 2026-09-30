#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集服务
负责管理着火点实验的数据采集逻辑
"""


class DataCollectionService:
    """数据采集服务"""
    
    def __init__(self, config, controller):
        """
        初始化数据采集服务
        
        Args:
            config: 配置字典
            controller: 实验控制器实例
        """
        self.config = config
        self.controller = controller
        self._collect_logged = False  # 采集日志标志
    
    def should_collect(self, current_temp: float, is_running: bool):
        """
        判断是否应该采集数据
        
        Args:
            current_temp: 当前温度
            is_running: 实验是否正在运行
        
        Returns:
            bool: 是否应该采集数据
        """
        if not is_running:
            return False
        
        collect_start_temp = self.config.get('collect_start_temperature', 200.0)
        return current_temp >= collect_start_temp
    
    def collect_data(self):
        """
        采集数据到数据库
        
        Returns:
            tuple: (是否成功, 是否首次采集)
        """
        try:
            success = self.controller.collect_data()
            is_first_time = not self._collect_logged
            
            if success and is_first_time:
                self._collect_logged = True
            
            return success, is_first_time
            
        except Exception as e:
            return False, False
    
    def reset_collect_flag(self):
        """重置采集日志标志"""
        self._collect_logged = False
    
    def get_collect_start_temperature(self):
        """获取采集起始温度"""
        return self.config.get('collect_start_temperature', 200.0)

