#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰分析处理器
负责处理火焰分析结果，管理数据保存和实验流程判断
"""


class FlameAnalysisHandler:
    """火焰分析处理器"""
    
    def __init__(self, round_manager, database):
        """
        初始化火焰分析处理器
        
        Args:
            round_manager: 轮次管理器实例
            database: 数据库实例
        """
        self.round_manager = round_manager
        self.database = database
    
    def process_analysis_results(self, results: dict, session_id: int, round_number: int, round_records: list):
        """
        处理火焰分析结果
        
        Args:
            results: 分析结果字典，包含：
                - max_flame_size: 最大火焰长度 (mm)
                - min_flame_size: 最小火焰长度 (mm)
                - average_flame_size: 平均火焰长度 (mm)
                - max_flame_image_path: 最大火焰图片路径
                - max_flame_saved_path: 保存的最大火焰图片路径
                - total_images: 总图像数
                - failed_images: 失败图像数
            session_id: 实验会话ID
            round_number: 当前轮次
            round_records: 轮次记录列表（用于流程判断）
        
        Returns:
            dict: {
                'success': bool,  # 是否处理成功
                'max_flame_length': float,  # 最大火焰长度
                'max_flame_image_path': str,  # 最大火焰图片路径
                'db_saved': bool,  # 是否保存到数据库
                'record': dict,  # 轮次记录
                'next_action': dict,  # 下一步操作（来自round_manager）
                'log_messages': list[str]  # 日志消息列表
            }
        """
        log_messages = []
        
        if not results:
            return {
                'success': False,
                'log_messages': ["⚠ 未接收到分析结果"]
            }
        
        # 提取结果
        max_flame_length = results.get('max_flame_size', 0.0)
        max_flame_image_path = results.get('max_flame_saved_path', '')
        
        # 记录日志
        log_messages.append("=" * 50)
        log_messages.append("✓ 火焰分析完成")
        log_messages.append(f"✓ 最大火焰长度: {max_flame_length} mm")
        log_messages.append(f"✓ 最小火焰长度: {results.get('min_flame_size', 0.0)} mm")
        log_messages.append(f"✓ 平均火焰长度: {results.get('average_flame_size', 0.0)} mm")
        log_messages.append(f"✓ 总图像数: {results.get('total_images', 0)}")
        log_messages.append(f"✓ 失败图像数: {results.get('failed_images', 0)}")
        
        if max_flame_image_path:
            log_messages.append(f"✓ 最大火焰图片已保存到: {max_flame_image_path}")
        
        log_messages.append("=" * 50)
        
        # 保存到数据库
        db_saved = False
        if session_id:
            db_result = self.database.add_test_round(
                session_id=session_id,
                round_number=round_number,
                flame_length=max_flame_length,
                max_flame_image_path=max_flame_image_path
            )
            if db_result > 0:
                log_messages.append(f"✓ 第 {round_number} 轮数据已保存到数据库")
                db_saved = True
            else:
                log_messages.append(f"✗ 第 {round_number} 轮数据保存到数据库失败")
        
        # 创建轮次记录
        record = {
            'round': round_number,
            'flame_length': max_flame_length,
            'image_path': max_flame_image_path
        }
        log_messages.append(f"✓ 已记录第 {round_number} 轮实验数据")
        
        # 更新round_records（在UI层完成）
        # 这里只返回记录，由调用方添加到列表
        
        # 获取下一步操作建议
        # 注意：需要包含当前轮次的记录
        updated_records = round_records + [record]
        next_action = self.round_manager.get_next_action(round_number, updated_records)
        
        return {
            'success': True,
            'max_flame_length': max_flame_length,
            'max_flame_image_path': max_flame_image_path,
            'db_saved': db_saved,
            'record': record,
            'next_action': next_action,
            'log_messages': log_messages
        }
    
    def build_conclusion_message(self, round_records: list, meets_standard: bool = None):
        """
        构建实验结论消息
        
        Args:
            round_records: 轮次记录列表
            meets_standard: 是否满足检测标准（None表示自动判断）
        
        Returns:
            tuple: (消息文本, meets_standard判断结果)
        """
        if not round_records:
            return "", False
        
        # 计算平均值
        avg_length = self.round_manager.calculate_average(round_records)
        level_text, _ = self.round_manager.evaluate_explosion_level(avg_length)
        # 检测标准阈值来自配置 test-rounds.phase-decision-threshold（与 RoundManager 的阶段判定一致）
        standard_threshold = self.round_manager.phase_decision_threshold

        # 如果没有指定meets_standard，则自动判断
        if meets_standard is None:
            phase_rounds = self.round_manager.phase_rounds
            max_rounds = self.round_manager.max_rounds

            # 如果只完成了前5轮且平均值低于阈值，则不满足标准
            if len(round_records) == phase_rounds and avg_length < standard_threshold:
                meets_standard = False
            # 如果完成了10轮，则无论结果如何都算完成了完整测试
            elif len(round_records) == max_rounds:
                meets_standard = True
            # 其他情况（如满足标准后提前结束），根据平均值判断
            else:
                meets_standard = avg_length >= standard_threshold
        
        # 构建结论信息
        msg = "=" * 50 + "\n"
        msg += "实验结论\n"
        msg += "=" * 50 + "\n\n"
        msg += f"总轮次: {len(round_records)} 轮\n\n"
        msg += "各轮火焰长度:\n"
        
        for record in round_records:
            msg += f"  第 {record['round']} 轮: {record['flame_length']:.1f} mm\n"
        
        msg += f"\n平均火焰长度: {avg_length:.1f} mm\n"
        msg += f"实验结论: {level_text}\n"
        
        # 添加标准符合性提示
        if not meets_standard:
            msg += f"\n⚠ 检测标准: 不满足（需要平均值≥{standard_threshold:g}mm或完成10轮测试）\n"
        else:
            msg += "\n✓ 检测标准: 满足\n"
        
        msg += "\n" + "=" * 50 + "\n\n"
        msg += "是否结束本次实验会话？"
        
        return msg, meets_standard
    
    def build_conclusion_logs(self, round_records: list, meets_standard: bool):
        """
        构建实验结论日志消息列表
        
        Args:
            round_records: 轮次记录列表
            meets_standard: 是否满足检测标准
        
        Returns:
            list[str]: 日志消息列表
        """
        if not round_records:
            return []
        
        avg_length = self.round_manager.calculate_average(round_records)
        level_text, _ = self.round_manager.evaluate_explosion_level(avg_length)
        standard_threshold = self.round_manager.phase_decision_threshold

        logs = []
        logs.append("=" * 50)
        logs.append("实验结论")
        logs.append("=" * 50)
        logs.append(f"总轮次: {len(round_records)} 轮")
        
        for record in round_records:
            logs.append(f"  第 {record['round']} 轮: {record['flame_length']:.1f} mm")
        
        logs.append(f"平均火焰长度: {avg_length:.1f} mm")
        logs.append(f"实验结论: {level_text}")
        
        # 记录标准符合性
        if not meets_standard:
            logs.append(f"⚠ 检测标准: 不满足（需要平均值≥{standard_threshold:g}mm或完成10轮测试）")
        else:
            logs.append("✓ 检测标准: 满足")
        
        logs.append("=" * 50)
        
        return logs

