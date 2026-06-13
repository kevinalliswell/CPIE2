#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验条件验证器
负责检查实验条件（温度、压力）是否满足要求
"""


class ExperimentValidator:
    """实验条件验证器"""
    
    def __init__(self, config, manager):
        """
        初始化验证器
        
        Args:
            config: 配置字典
            manager: 设备管理器
        """
        self.config = config
        self.manager = manager
    
    def check_conditions(self):
        """
        检查实验条件是否满足
        
        Returns:
            tuple: (是否满足, 详细消息)
                - bool: 条件满足返回True，否则返回False
                - str: 详细的检查信息（包含当前状态和目标要求）
        """
        try:
            # 获取配置中的目标条件
            control_conditions = self.config.get('control_conditions', {})
            
            # 目标温度配置
            target_temp_config = control_conditions.get('target_temperature', {})
            target_temp = target_temp_config.get('value', 0.0)
            temp_tolerance = target_temp_config.get('tolerance', 0.0)
            temp_unit = target_temp_config.get('unit', '℃')
            
            # 目标压力配置
            target_pressure_config = control_conditions.get('target_pressure', {})
            target_pressure = target_pressure_config.get('value', 0.0)
            pressure_tolerance = target_pressure_config.get('tolerance', 0.0)
            pressure_unit = target_pressure_config.get('unit', 'kPa')
            
            # 获取当前温度PV值
            controller_data = self.manager.get_latest_data('爆炸性-温控仪表')
            if controller_data is None:
                return False, "无法获取温控仪表数据，请检查设备连接状态！"
            
            current_temp = controller_data.get('pv')
            if current_temp is None:
                return False, "无法获取当前温度值（PV），请检查温控仪表数据！"

            # 获取当前压力值
            pressure_data = self.manager.get_latest_data('爆炸性-压力表')
            if pressure_data is None:
                return False, "无法获取压力仪表数据，请检查设备连接状态！"

            current_pressure = pressure_data.get('pressure', 0.0)
            
            # 检查温度是否在范围内
            temp_min = target_temp - temp_tolerance
            temp_max = target_temp + temp_tolerance
            temp_ok = temp_min <= current_temp <= temp_max
            
            # 检查压力是否在范围内
            pressure_min = target_pressure - pressure_tolerance
            pressure_max = target_pressure + pressure_tolerance
            pressure_ok = pressure_min <= current_pressure <= pressure_max
            
            # 如果条件不满足，返回详细信息
            if not temp_ok or not pressure_ok:
                error_msg = "实验条件不满足，无法启动实验！\n\n"
                error_msg += "【当前状态】\n"
                error_msg += f"  温度: {current_temp:.1f} {temp_unit}\n"
                error_msg += f"  压力: {current_pressure:.1f} {pressure_unit}\n\n"
                error_msg += "【目标要求】\n"
                error_msg += f"  温度: {target_temp:.1f} ± {temp_tolerance:.1f} {temp_unit}\n"
                error_msg += f"  范围: [{temp_min:.1f}, {temp_max:.1f}] {temp_unit}\n"
                error_msg += f"  压力: {target_pressure:.1f} ± {pressure_tolerance:.1f} {pressure_unit}\n"
                error_msg += f"  范围: [{pressure_min:.1f}, {pressure_max:.1f}] {pressure_unit}\n\n"
                error_msg += "【检查结果】\n"
                error_msg += f"  温度: {'✓ 满足' if temp_ok else '✗ 不满足'}\n"
                error_msg += f"  压力: {'✓ 满足' if pressure_ok else '✗ 不满足'}"
                
                return False, error_msg
            
            # 条件满足，返回成功信息
            success_msg = f"实验条件检查通过\n"
            success_msg += f"  温度: {current_temp:.1f}{temp_unit} (目标: {target_temp:.1f}±{temp_tolerance:.1f}{temp_unit})\n"
            success_msg += f"  压力: {current_pressure:.1f}{pressure_unit} (目标: {target_pressure:.1f}±{pressure_tolerance:.1f}{pressure_unit})"
            
            return True, success_msg
            
        except Exception as e:
            return False, f"检查实验条件时发生异常: {e}"

