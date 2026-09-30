#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轮次管理器
负责管理实验轮次、评估爆炸性等级、判断实验流程
"""

import math


class RoundManager:
    """轮次管理器"""
    
    def __init__(self, config):
        """
        初始化轮次管理器
        
        Args:
            config: 配置字典
        """
        # 从配置读取实验轮次设置
        test_rounds_config = config.get('test-rounds', {})
        self.max_rounds = test_rounds_config.get('max-rounds', 10)
        self.phase_rounds = test_rounds_config.get('phase-rounds', 5)
        self.phase_decision_threshold = test_rounds_config.get('phase-decision-threshold', 20.0)
        
        # 从配置读取爆炸性评估阈值
        thresholds_config = config.get('explosion-thresholds', {})
        self.threshold_no_explosion = thresholds_config.get('no-explosion', 25.0)
        self.threshold_weak_explosion = thresholds_config.get('weak-explosion', 400.0)
        self.threshold_strong_explosion = thresholds_config.get('strong-explosion', 800.0)

        if (not self.valid_positive_integer(self.max_rounds)
                or self.max_rounds > 10
                or not self.valid_positive_integer(self.phase_rounds)
                or self.phase_rounds > self.max_rounds):
            raise ValueError('实验轮次配置无效：需要 1 ≤ 阶段轮次 ≤ 最大轮次 ≤ 10')
        thresholds = (self.phase_decision_threshold, self.threshold_no_explosion,
                      self.threshold_weak_explosion, self.threshold_strong_explosion)
        if not all(self.valid_measurement(value) for value in thresholds):
            raise ValueError('实验阈值配置必须为有限非负数')
        if not (self.threshold_no_explosion < self.threshold_weak_explosion < self.threshold_strong_explosion):
            raise ValueError('爆炸性等级阈值配置必须严格递增')

    @staticmethod
    def valid_positive_integer(value):
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    @staticmethod
    def valid_measurement(value):
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value >= 0)

    def validate_records(self, round_records):
        """Only distinct, consecutive accepted rounds contribute to a decision."""
        if not isinstance(round_records, list) or len(round_records) > self.max_rounds:
            raise ValueError('轮次记录数量无效')
        for expected, record in enumerate(round_records, start=1):
            if (not isinstance(record, dict)
                    or not self.valid_positive_integer(record.get('round'))
                    or record['round'] != expected
                    or not self.valid_measurement(record.get('flame_length'))):
                raise ValueError('轮次记录必须从 1 连续编号，且火焰长度有效')

    def is_complete(self, round_records):
        """Completion of the configured procedure, not regulatory certification."""
        self.validate_records(round_records)
        if len(round_records) < self.phase_rounds:
            return False
        first_phase_average = self.calculate_average(round_records[:self.phase_rounds])
        return (len(round_records) == self.max_rounds
                or first_phase_average >= self.phase_decision_threshold)
    
    def evaluate_explosion_level(self, avg_flame_length: float):
        """
        根据平均火焰长度评估爆炸性强弱
        
        Args:
            avg_flame_length: 平均火焰长度(mm)
        
        Returns:
            tuple: (等级文本, 颜色代码)
        """
        if not self.valid_measurement(avg_flame_length):
            raise ValueError('火焰长度必须为有限非负数')
        if avg_flame_length < self.threshold_no_explosion:
            return ("无爆炸性", "#999999")
        elif self.threshold_no_explosion <= avg_flame_length < self.threshold_weak_explosion:
            return ("弱爆炸性", "#ff9800")
        elif self.threshold_weak_explosion <= avg_flame_length < self.threshold_strong_explosion:
            return ("强爆炸性", "#ff5722")
        else:  # >= threshold_strong_explosion
            return ("超强爆炸性", "#f44336")
    
    def should_continue_phase2(self, round_records: list):
        """
        判断是否需要进入第二阶段
        
        Args:
            round_records: 轮次记录列表
        
        Returns:
            tuple: (是否需要第二阶段, 原因说明)
        """
        self.validate_records(round_records)
        if len(round_records) < self.phase_rounds:
            return False, "未完成第一阶段"
        
        # 计算第一阶段平均值
        avg_length = self.calculate_average(round_records[:self.phase_rounds])
        
        if avg_length < self.phase_decision_threshold and len(round_records) < self.max_rounds:
            reason = f"前{self.phase_rounds}轮平均火焰长度为 {avg_length:.1f}mm，低于{self.phase_decision_threshold}mm阶段阈值，需要进行第二阶段（第{self.phase_rounds + 1}-{self.max_rounds}轮）测试"
            return True, reason
        else:
            reason = '已满足配置的轮次流程，可以结束测试'
            return False, reason
    
    def get_next_action(self, current_round: int, round_records: list):
        """
        获取下一步操作建议
        
        Args:
            current_round: 当前轮次
            round_records: 轮次记录列表
        
        Returns:
            dict: {
                'action': 'continue' | 'phase2' | 'complete',
                'message': str,
                'meets_standard': bool  # 兼容字段：配置流程是否完成，不代表标准认证
            }
        """
        self.validate_records(round_records)
        if not self.valid_positive_integer(current_round) or current_round != len(round_records):
            raise ValueError('当前轮次与已保存的连续记录不一致')

        # The maximum also wins for a single-phase custom configuration.
        if current_round == self.max_rounds:
            return {'action': 'complete', 'message': f'配置的实验轮次已完成（{self.max_rounds}轮）',
                    'meets_standard': True}

        if current_round == self.phase_rounds:
            avg_length = self.calculate_average(round_records)
            
            if avg_length < self.phase_decision_threshold:
                return {
                    'action': 'phase2',
                    'message': f'前{self.phase_rounds}轮实验完成！平均火焰长度: {avg_length:.1f} mm\n'
                               f'判断结果: 平均值低于配置的阶段阈值{self.phase_decision_threshold}mm\n'
                               f'配置流程尚未完成\n\n'
                               f'是否继续进行第二阶段（第{self.phase_rounds + 1}-{self.max_rounds}轮）实验？',
                    'meets_standard': False
                }
            else:
                level_text, _ = self.evaluate_explosion_level(avg_length)
                return {
                    'action': 'complete',
                    'message': f'前{self.phase_rounds}轮实验完成！平均火焰长度: {avg_length:.1f} mm\n'
                               f'实验结论: {level_text}\n'
                               f'✓ 已完成配置流程\n\n'
                               f'是否结束本次实验会话？',
                    'meets_standard': True
                }
        
        # 其他轮次，继续实验
        else:
            return {
                'action': 'continue',
                'message': f'第 {current_round} 轮实验完成！是否继续下一轮实验？',
                'meets_standard': None  # 中间轮次不判断
            }
    
    def calculate_average(self, round_records: list):
        """
        计算平均火焰长度
        
        Args:
            round_records: 轮次记录列表
        
        Returns:
            float: 平均火焰长度
        """
        if not round_records:
            return 0.0
        self.validate_records(round_records)
        average = sum(r['flame_length'] / len(round_records) for r in round_records)
        if not self.valid_measurement(average):
            raise ValueError('平均火焰长度无效')
        return average
    
    def get_progress_info(self, current_round: int):
        """
        获取当前进度信息
        
        Args:
            current_round: 当前轮次数
        
        Returns:
            tuple: (进度文本, 颜色代码)
        """
        if current_round == 0:
            return ("未开始", "#999999")
        elif current_round <= self.phase_rounds:
            return (f"第一阶段: {current_round}/{self.phase_rounds}", "#4a9eff")
        else:
            return (f"第二阶段: {current_round}/{self.max_rounds}", "#ff9800")
