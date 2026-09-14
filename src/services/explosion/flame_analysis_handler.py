#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰分析处理器
负责处理火焰分析结果，管理数据保存和实验流程判断
"""

from pathlib import Path

from utils.path_manager import PathManager


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
    
    @staticmethod
    def _failure(message):
        return {'success': False, 'db_saved': False, 'log_messages': [f'✗ {message}']}

    def process_analysis_results(self, results: dict, session_id: int, round_number: int, round_records: list):
        """Accept a round only after validating its identity, measurements and commit.

        Failure never returns a record/action or consumes images. The caller can
        keep the analysis and retry after a database failure.
        """
        try:
            if not isinstance(results, dict) or not results:
                return self._failure('未接收到有效分析结果')
            measurements = [results.get(key) for key in
                            ('min_flame_size', 'average_flame_size', 'max_flame_size')]
            if not all(self.round_manager.valid_measurement(value) for value in measurements):
                return self._failure('火焰分析数值必须为有限非负数，且不能缺失')
            minimum, average, maximum = measurements
            if not minimum <= average <= maximum:
                return self._failure('火焰最小值、平均值和最大值不一致')
            total, failed = results.get('total_images'), results.get('failed_images')
            if (not isinstance(total, int) or isinstance(total, bool) or total <= 0
                    or not isinstance(failed, int) or isinstance(failed, bool)
                    or not 0 <= failed <= total):
                return self._failure('没有成功分析的图像，或图像数量无效')
            if failed:
                return self._failure('存在分析失败的图像，无法确认完整火焰峰值；请保留图像并重试分析')
            if not self.round_manager.valid_positive_integer(session_id):
                return self._failure('没有有效的实验会话')
            session = self.database.get_session_by_id(session_id)
            if (not session or session.get('end_time') is not None
                    or session.get('status') not in ('running', 'prepared')):
                return self._failure('实验会话不存在或已经结束，不能接收分析结果')

            self.round_manager.validate_records(round_records)
            saved = self.database.get_session_test_rounds(session_id)
            saved_records = [
                {'round': row['round_number'], 'flame_length': row['flame_length']}
                for row in saved
            ]
            self.round_manager.validate_records(saved_records)
            if [(r['round'], r['flame_length']) for r in round_records] != [
                    (r['round'], r['flame_length']) for r in saved_records]:
                return self._failure('页面轮次与数据库不一致，请核对已保存记录后重试')
            if (not self.round_manager.valid_positive_integer(round_number)
                    or round_number != len(saved_records) + 1):
                return self._failure('分析轮次重复或不连续，不能覆盖已保存记录')

            image_path = results.get('max_flame_saved_path', '')
            if not isinstance(image_path, str) or not image_path.strip():
                return self._failure('最大火焰图片尚未成功保存，请保留图像并重试')
            image = Path(image_path).resolve()
            if not image.is_file() or image.stat().st_size == 0:
                return self._failure('最大火焰图片缺失或为空，请保留图像并重试保存')
            transient_roots = (PathManager.get_flame_temp_path(), PathManager.get_flame_results_path())
            if any(image.is_relative_to(Path(root).resolve()) for root in transient_roots):
                return self._failure('最大火焰图片仍在待清理的临时目录，请先保存到永久目录')
            image_path = str(image)
            record = {'round': round_number, 'flame_length': maximum, 'image_path': image_path}
            # Check the full decision before committing, so validation failures
            # cannot leave a saved round that the UI believes failed.
            next_action = self.round_manager.get_next_action(round_number, saved_records + [record])
            round_id = self.database.add_test_round(
                session_id=session_id, round_number=round_number,
                flame_length=maximum, max_flame_image_path=image_path)
            if not isinstance(round_id, int) or isinstance(round_id, bool) or round_id <= 0:
                return self._failure(f'第 {round_number} 轮保存失败；分析图像和结果已保留，请重试')

            return {
                'success': True, 'db_saved': True, 'record': record,
                'max_flame_length': maximum, 'max_flame_image_path': image_path,
                'next_action': next_action,
                'log_messages': [
                    '✓ 火焰分析完成',
                    f'最大火焰长度: {maximum:g} mm；最小值: {minimum:g} mm；平均值: {average:g} mm',
                    f'图像数: {total}；失败数: {failed}',
                    f'✓ 第 {round_number} 轮数据已保存到数据库',
                ],
            }
        except Exception as exc:
            return self._failure(f'处理分析结果失败，已保留分析数据：{exc}')

    def build_conclusion_message(self, round_records: list, meets_standard: bool = None):
        """
        构建实验结论消息
        
        Args:
            round_records: 轮次记录列表
            meets_standard: 兼容参数，配置流程是否完成（None表示自动判断）
        
        Returns:
            tuple: (消息文本, meets_standard判断结果)
        """
        if not round_records:
            return "", False
        
        # 计算平均值
        avg_length = self.round_manager.calculate_average(round_records)
        level_text, _ = self.round_manager.evaluate_explosion_level(avg_length)
        phase_threshold = self.round_manager.phase_decision_threshold
        # Keep the public argument for callers, but a True flag cannot make
        # missing/insufficient rounds into a completed configured procedure.
        meets_standard = self.round_manager.is_complete(round_records) and meets_standard is not False

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
        
        # Report the configured procedure; this is not a certification claim.
        if not meets_standard:
            msg += f"\n配置流程未完成（需前{self.round_manager.phase_rounds}轮平均值≥{phase_threshold:g}mm，或完成{self.round_manager.max_rounds}轮）\n"
        else:
            msg += "\n✓ 已完成配置流程\n"
        
        msg += "\n" + "=" * 50 + "\n\n"
        msg += "是否结束本次实验会话？"
        
        return msg, meets_standard
    
    def build_conclusion_logs(self, round_records: list, meets_standard: bool):
        """
        构建实验结论日志消息列表
        
        Args:
            round_records: 轮次记录列表
            meets_standard: 兼容参数，配置流程是否完成
        
        Returns:
            list[str]: 日志消息列表
        """
        if not round_records:
            return []
        
        avg_length = self.round_manager.calculate_average(round_records)
        level_text, _ = self.round_manager.evaluate_explosion_level(avg_length)
        phase_threshold = self.round_manager.phase_decision_threshold
        meets_standard = self.round_manager.is_complete(round_records) and meets_standard is not False

        logs = []
        logs.append("=" * 50)
        logs.append("实验结论")
        logs.append("=" * 50)
        logs.append(f"总轮次: {len(round_records)} 轮")
        
        for record in round_records:
            logs.append(f"  第 {record['round']} 轮: {record['flame_length']:.1f} mm")
        
        logs.append(f"平均火焰长度: {avg_length:.1f} mm")
        logs.append(f"实验结论: {level_text}")
        
        # 记录配置流程完成情况
        if not meets_standard:
            logs.append(f"配置流程未完成（需前{self.round_manager.phase_rounds}轮平均值≥{phase_threshold:g}mm，或完成{self.round_manager.max_rounds}轮）")
        else:
            logs.append("✓ 已完成配置流程")
        
        logs.append("=" * 50)
        
        return logs
