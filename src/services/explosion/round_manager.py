#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轮次管理器
负责管理实验轮次、评估爆炸性等级、判断实验流程
"""


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
        self.max_rounds = test_rounds_config.get('max-rounds', 10)  # 默认10轮（国标要求）
        self.phase_rounds = test_rounds_config.get('phase-rounds', 5)  # 默认5轮（国标要求）
        
        # 从配置读取爆炸性评估阈值
        thresholds_config = config.get('explosion-thresholds', {})
        self.threshold_no_explosion = thresholds_config.get('no-explosion', 25.0)
        self.threshold_weak_explosion = thresholds_config.get('weak-explosion', 400.0)
        self.threshold_strong_explosion = thresholds_config.get('strong-explosion', 800.0)

        # 第一阶段结束后的判定阈值：前 phase_rounds 轮平均火焰长度低于该值时需继续第二阶段。
        # 配置键为 test-rounds.phase-decision-threshold；未配置时沿用无爆炸性上限。
        phase_threshold = test_rounds_config.get('phase-decision-threshold', self.threshold_no_explosion)
        try:
            self.phase_decision_threshold = float(phase_threshold)
        except (TypeError, ValueError):
            self.phase_decision_threshold = float(self.threshold_no_explosion)
    
    def evaluate_explosion_level(self, avg_flame_length: float):
        """
        根据平均火焰长度评估爆炸性强弱
        
        Args:
            avg_flame_length: 平均火焰长度(mm)
        
        Returns:
            tuple: (等级文本, 颜色代码)
        """
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
        if len(round_records) < self.phase_rounds:
            return False, "未完成第一阶段"
        
        # 计算第一阶段平均值
        avg_length = sum(r['flame_length'] for r in round_records[:self.phase_rounds]) / self.phase_rounds
        
        threshold = self.phase_decision_threshold
        if avg_length < threshold:
            reason = f"前{self.phase_rounds}轮平均火焰长度为 {avg_length:.1f}mm，低于{threshold:g}mm阈值，需要进行第二阶段（第{self.phase_rounds + 1}-{self.max_rounds}轮）测试"
            return True, reason
        else:
            reason = f"前{self.phase_rounds}轮平均火焰长度为 {avg_length:.1f}mm，达到{threshold:g}mm阈值，可以结束测试"
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
                'meets_standard': bool  # 是否满足检测标准
            }
        """
        # 第一阶段完成
        if current_round == self.phase_rounds:
            avg_length = sum(r['flame_length'] for r in round_records) / len(round_records)
            threshold = self.phase_decision_threshold

            if avg_length < threshold:
                return {
                    'action': 'phase2',
                    'message': f'前{self.phase_rounds}轮实验完成！平均火焰长度: {avg_length:.1f} mm\n'
                               f'判断结果: 平均值低于{threshold:g}mm\n'
                               f'⚠ 不满足检测标准要求（需≥{threshold:g}mm）\n\n'
                               f'是否继续进行第二阶段（第{self.phase_rounds + 1}-{self.max_rounds}轮）实验？',
                    'meets_standard': False
                }
            else:
                level_text, _ = self.evaluate_explosion_level(avg_length)
                return {
                    'action': 'complete',
                    'message': f'前{self.phase_rounds}轮实验完成！平均火焰长度: {avg_length:.1f} mm\n'
                               f'实验结论: {level_text}\n'
                               f'✓ 满足检测标准要求\n\n'
                               f'是否结束本次实验会话？',
                    'meets_standard': True
                }
        
        # 所有轮次完成
        elif current_round == self.max_rounds:
            return {
                'action': 'complete',
                'message': f'所有实验轮次完成（{self.max_rounds}轮）',
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
        return sum(r['flame_length'] for r in round_records) / len(round_records)
    
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

