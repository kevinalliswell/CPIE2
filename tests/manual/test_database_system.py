#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库系统测试脚本
对 explosion_experiment.db 和 ignition_experiment.db 进行全面的功能测试
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from models.explosion_database import ExplosionDatabase
from models.ignition_database import IgnitionDatabase


class DatabaseSystemTester:
    """数据库系统测试类"""
    
    def __init__(self):
        """初始化测试器"""
        self.data_dir = Path("data")
        self.explosion_db_path = self.data_dir / "explosion_experiment.db"
        self.ignition_db_path = self.data_dir / "ignition_experiment.db"
        
        self.test_results = {
            'explosion': {'passed': 0, 'failed': 0, 'errors': []},
            'ignition': {'passed': 0, 'failed': 0, 'errors': []}
        }
        
    def print_header(self, title: str):
        """打印测试标题"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
    
    def print_test(self, test_name: str):
        """打印测试项"""
        print(f"\n[测试] {test_name}")
    
    def print_success(self, message: str = ""):
        """打印成功信息"""
        print(f"  ✓ 通过 {message}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        print(f"  ✗ 失败: {message}")
    
    def record_result(self, db_type: str, success: bool, error_msg: str = ""):
        """记录测试结果"""
        if success:
            self.test_results[db_type]['passed'] += 1
        else:
            self.test_results[db_type]['failed'] += 1
            if error_msg:
                self.test_results[db_type]['errors'].append(error_msg)
    
    # ==================== 爆炸性数据库测试 ====================
    
    def test_explosion_database(self):
        """测试爆炸性数据库"""
        self.print_header("爆炸性实验数据库系统测试")
        
        try:
            db = ExplosionDatabase(str(self.explosion_db_path))
            print(f"数据库路径: {self.explosion_db_path}")
            
            # 1. 连接测试
            self.print_test("1. 数据库连接")
            assert db.conn is not None, "数据库连接失败"
            self.print_success("数据库连接正常")
            self.record_result('explosion', True)
            
            # 2. 创建实验会话
            self.print_test("2. 创建实验会话")
            session_id = db.start_experiment_session(
                experiment_id="TEST-EXP-001",
                experiment_name="测试爆炸性实验",
                sample_name="测试样品A",
                client="测试单位",
                operator="测试操作员",
                description="系统测试用实验"
            )
            assert session_id > 0, f"创建会话失败，返回ID: {session_id}"
            self.print_success(f"会话ID: {session_id}")
            self.record_result('explosion', True)
            
            # 3. 添加测试轮次（单条）
            self.print_test("3. 添加测试轮次（单条）")
            round_id1 = db.add_test_round(session_id, 1, 15.5, "test_images/round1.jpg")
            assert round_id1 > 0, "添加测试轮次失败"
            self.print_success(f"轮次1已添加，ID: {round_id1}")
            self.record_result('explosion', True)
            
            # 4. 添加测试轮次（批量）
            self.print_test("4. 添加测试轮次（批量）")
            batch_data = [
                (2, 18.2, "test_images/round2.jpg"),
                (3, 16.8, "test_images/round3.jpg"),
                (4, 17.5, "test_images/round4.jpg"),
                (5, 19.0, "test_images/round5.jpg"),
            ]
            count = db.add_batch_test_rounds(session_id, batch_data)
            assert count == len(batch_data), f"批量添加失败，期望{len(batch_data)}条，实际{count}条"
            self.print_success(f"批量添加{count}条记录")
            self.record_result('explosion', True)
            
            # 5. 查询会话信息
            self.print_test("5. 查询会话信息")
            session = db.get_session_by_id(session_id)
            assert session is not None, "查询会话失败"
            assert session['experiment_name'] == "测试爆炸性实验", "会话信息不匹配"
            self.print_success(f"会话名称: {session['experiment_name']}")
            self.record_result('explosion', True)
            
            # 6. 查询测试轮次
            self.print_test("6. 查询测试轮次")
            rounds = db.get_session_test_rounds(session_id)
            assert len(rounds) == 5, f"查询轮次数量不匹配，期望5条，实际{len(rounds)}条"
            self.print_success(f"查询到{len(rounds)}轮测试数据")
            self.record_result('explosion', True)
            
            # 7. 计算平均值
            self.print_test("7. 计算平均火焰长度")
            avg_length = db.calculate_session_average(session_id)
            assert avg_length is not None, "计算平均值失败"
            assert avg_length > 0, "平均值应该大于0"
            self.print_success(f"平均火焰长度: {avg_length}mm")
            self.record_result('explosion', True)
            
            # 8. 爆炸性等级分类
            self.print_test("8. 爆炸性等级分类")
            level1 = db.classify_explosion_strength(15.0)  # 无爆炸性
            level2 = db.classify_explosion_strength(250.0)  # 弱爆炸性
            level3 = db.classify_explosion_strength(550.0)  # 强爆炸性
            level4 = db.classify_explosion_strength(900.0)  # 超强爆炸性
            assert level1 == "无爆炸性", f"等级分类错误: {level1}"
            assert level2 == "弱爆炸性", f"等级分类错误: {level2}"
            assert level3 == "强爆炸性", f"等级分类错误: {level3}"
            assert level4 == "超强爆炸性", f"等级分类错误: {level4}"
            self.print_success(f"15mm→{level1}, 250mm→{level2}, 550mm→{level3}, 900mm→{level4}")
            self.record_result('explosion', True)
            
            # 9. 完成实验
            self.print_test("9. 完成实验")
            success = db.finalize_experiment(session_id)
            assert success, "完成实验失败"
            self.print_success("实验已完成")
            self.record_result('explosion', True)
            
            # 10. 查询实验结果
            self.print_test("10. 查询实验结果")
            result = db.get_session_result(session_id)
            assert result is not None, "查询结果失败"
            assert result['total_rounds'] == 5, "测试轮次数不匹配"
            assert result['avg_flame_length'] > 0, "平均火焰长度应该大于0"
            self.print_success(f"测试轮次: {result['total_rounds']}, "
                             f"平均火焰长度: {result['avg_flame_length']}mm, "
                             f"爆炸性等级: {result['explosion_level']}")
            self.record_result('explosion', True)
            
            # 11. 更新测试轮次
            self.print_test("11. 更新测试轮次")
            success = db.update_test_round(round_id1, flame_length=20.0)
            assert success, "更新测试轮次失败"
            updated_round = db.get_session_test_rounds(session_id)[0]
            assert updated_round['flame_length'] == 20.0, "更新后的值不匹配"
            self.print_success(f"轮次1火焰长度已更新为: {updated_round['flame_length']}mm")
            self.record_result('explosion', True)
            
            # 12. 更新会话信息
            self.print_test("12. 更新会话信息")
            success = db.update_session(session_id, description="更新后的描述")
            assert success, "更新会话失败"
            updated_session = db.get_session_by_id(session_id)
            assert updated_session['description'] == "更新后的描述", "更新后的描述不匹配"
            self.print_success("会话信息已更新")
            self.record_result('explosion', True)
            
            # 13. 查询所有会话
            self.print_test("13. 查询所有会话")
            all_sessions = db.get_all_experiment_sessions()
            assert len(all_sessions) > 0, "查询会话列表失败"
            test_session_found = any(s['id'] == session_id for s in all_sessions)
            assert test_session_found, "测试会话未在列表中"
            self.print_success(f"查询到{len(all_sessions)}个会话")
            self.record_result('explosion', True)
            
            # 14. 查询所有结果
            self.print_test("14. 查询所有结果")
            all_results = db.get_all_results()
            assert len(all_results) > 0, "查询结果列表失败"
            test_result_found = any(r['session_id'] == session_id for r in all_results)
            assert test_result_found, "测试结果未在列表中"
            self.print_success(f"查询到{len(all_results)}个结果")
            self.record_result('explosion', True)
            
            # 15. 按爆炸性等级查询
            self.print_test("15. 按爆炸性等级查询")
            weak_results = db.get_results_by_explosion_level("无爆炸性")
            assert isinstance(weak_results, list), "查询结果类型错误"
            self.print_success(f"查询到{len(weak_results)}个无爆炸性结果")
            self.record_result('explosion', True)
            
            # 16. 统计信息
            self.print_test("16. 获取统计信息")
            stats = db.get_statistics()
            assert stats is not None, "获取统计信息失败"
            assert 'total_sessions' in stats, "统计信息缺少total_sessions"
            assert 'sessions_by_status' in stats, "统计信息缺少sessions_by_status"
            self.print_success(f"总会话数: {stats['total_sessions']}, "
                             f"状态分布: {stats.get('sessions_by_status', {})}")
            self.record_result('explosion', True)
            
            # 17. 导出CSV
            self.print_test("17. 导出CSV数据")
            csv_file = "test_explosion_export.csv"
            success = db.export_to_csv(csv_file, session_id=session_id)
            assert success, "导出CSV失败"
            assert os.path.exists(csv_file), "CSV文件不存在"
            self.print_success(f"数据已导出到: {csv_file}")
            # 清理测试文件
            if os.path.exists(csv_file):
                os.remove(csv_file)
            self.record_result('explosion', True)
            
            # 18. 备份数据库
            self.print_test("18. 备份数据库")
            backup_path = "test_explosion_backup.db"
            success = db.backup(backup_path)
            assert success, "备份数据库失败"
            assert os.path.exists(backup_path), "备份文件不存在"
            self.print_success(f"数据库已备份到: {backup_path}")
            # 清理测试文件
            if os.path.exists(backup_path):
                os.remove(backup_path)
            self.record_result('explosion', True)
            
            # 19. 边界条件测试 - 无效会话ID
            self.print_test("19. 边界条件测试 - 无效会话ID")
            invalid_session = db.get_session_by_id(-1)
            assert invalid_session is None, "应该返回None"
            invalid_rounds = db.get_session_test_rounds(-1)
            assert len(invalid_rounds) == 0, "应该返回空列表"
            self.print_success("无效会话ID处理正确")
            self.record_result('explosion', True)
            
            # 20. 边界条件测试 - 无效轮次编号
            self.print_test("20. 边界条件测试 - 无效轮次编号")
            invalid_round_id = db.add_test_round(session_id, 0, 10.0)  # 轮次0无效
            assert invalid_round_id == -1, "应该返回-1"
            invalid_round_id2 = db.add_test_round(session_id, 11, 10.0)  # 轮次11无效
            assert invalid_round_id2 == -1, "应该返回-1"
            self.print_success("无效轮次编号处理正确")
            self.record_result('explosion', True)
            
            # 21. 创建第二个会话（强爆炸性）
            self.print_test("21. 创建第二个会话（强爆炸性）")
            session_id2 = db.start_experiment_session(
                experiment_id="TEST-EXP-002",
                experiment_name="测试强爆炸性实验",
                sample_name="测试样品B",
                client="测试单位",
                operator="测试操作员"
            )
            strong_data = [
                (1, 520.5, "test_images/strong1.jpg"),
                (2, 580.2, "test_images/strong2.jpg"),
                (3, 550.8, "test_images/strong3.jpg"),
                (4, 600.5, "test_images/strong4.jpg"),
                (5, 590.0, "test_images/strong5.jpg"),
            ]
            db.add_batch_test_rounds(session_id2, strong_data)
            db.finalize_experiment(session_id2)
            result2 = db.get_session_result(session_id2)
            assert result2['explosion_level'] == "强爆炸性", "爆炸性等级分类错误"
            self.print_success(f"强爆炸性实验完成，等级: {result2['explosion_level']}")
            self.record_result('explosion', True)
            
            # 22. 删除测试轮次
            self.print_test("22. 删除测试轮次")
            rounds_before = len(db.get_session_test_rounds(session_id))
            success = db.delete_test_round(round_id1)
            assert success, "删除测试轮次失败"
            rounds_after = len(db.get_session_test_rounds(session_id))
            assert rounds_after == rounds_before - 1, "删除后数量不匹配"
            self.print_success("测试轮次已删除")
            self.record_result('explosion', True)
            
            # 23. 删除会话
            self.print_test("23. 删除会话")
            success = db.delete_session(session_id2)
            assert success, "删除会话失败"
            deleted_session = db.get_session_by_id(session_id2)
            assert deleted_session is None, "会话应该已被删除"
            self.print_success("会话已删除")
            self.record_result('explosion', True)
            
            # 关闭数据库
            db.close()
            
        except Exception as e:
            self.print_error(str(e))
            import traceback
            self.record_result('explosion', False, f"{str(e)}\n{traceback.format_exc()}")
    
    # ==================== 着火点数据库测试 ====================
    
    def test_ignition_database(self):
        """测试着火点数据库"""
        self.print_header("着火点实验数据库系统测试")
        
        try:
            db = IgnitionDatabase(str(self.ignition_db_path))
            print(f"数据库路径: {self.ignition_db_path}")
            
            # 1. 连接测试
            self.print_test("1. 数据库连接")
            assert db.conn is not None, "数据库连接失败"
            self.print_success("数据库连接正常")
            self.record_result('ignition', True)
            
            # 2. 创建实验会话
            self.print_test("2. 创建实验会话")
            sample_names_json = json.dumps(["样品1", "样品2", "样品3", "样品4", "样品5", "样品6"])
            session_id = db.start_experiment_session(
                experiment_id="TEST-IGN-001",
                experiment_name="测试着火点实验",
                sample_names=sample_names_json,
                client="测试单位",
                operator="测试操作员",
                description="系统测试用实验"
            )
            assert session_id > 0, f"创建会话失败，返回ID: {session_id}"
            self.print_success(f"会话ID: {session_id}")
            self.record_result('ignition', True)
            
            # 3. 插入单条温度数据
            self.print_test("3. 插入单条温度数据")
            record_id = db.insert_ignition_data(
                pv=150.5, ch1=25.3, ch2=26.1, ch3=24.8,
                ch4=25.9, ch5=26.5, ch6=25.1,
                session_id=session_id
            )
            assert record_id > 0, "插入数据失败"
            self.print_success(f"数据已插入，ID: {record_id}")
            self.record_result('ignition', True)
            
            # 4. 批量插入温度数据
            self.print_test("4. 批量插入温度数据")
            batch_data = [
                (151.2, 26.0, 26.5, 25.3, 26.2, 27.0, 25.8),
                (152.0, 26.8, 27.2, 26.0, 26.9, 27.5, 26.3),
                (153.5, 27.5, 28.0, 26.8, 27.6, 28.2, 27.0),
                (155.0, 28.5, 29.0, 27.5, 28.5, 29.5, 28.0),
            ]
            count = db.insert_batch_data(batch_data, session_id=session_id)
            assert count == len(batch_data), f"批量插入失败，期望{len(batch_data)}条，实际{count}条"
            self.print_success(f"批量插入{count}条记录")
            self.record_result('ignition', True)
            
            # 5. 查询会话信息
            self.print_test("5. 查询会话信息")
            sessions = db.get_all_experiment_sessions()
            test_session = next((s for s in sessions if s['id'] == session_id), None)
            assert test_session is not None, "查询会话失败"
            assert test_session['experiment_name'] == "测试着火点实验", "会话信息不匹配"
            self.print_success(f"会话名称: {test_session['experiment_name']}")
            self.record_result('ignition', True)
            
            # 6. 查询单条数据
            self.print_test("6. 查询单条数据")
            data = db.get_data_by_id(record_id)
            assert data is not None, "查询数据失败"
            assert data['pv'] == 150.5, "数据不匹配"
            self.print_success(f"查询到数据，炉膛温度: {data['pv']}°C")
            self.record_result('ignition', True)
            
            # 7. 查询最新数据
            self.print_test("7. 查询最新数据")
            latest = db.get_latest_data(limit=3)
            assert len(latest) == 3, f"查询最新数据失败，期望3条，实际{len(latest)}条"
            self.print_success(f"查询到{len(latest)}条最新数据")
            self.record_result('ignition', True)
            
            # 8. 查询会话温度数据
            self.print_test("8. 查询会话温度数据")
            session_data = db.get_session_temperature_data(session_id)
            assert len(session_data) == 5, f"查询会话数据失败，期望5条，实际{len(session_data)}条"
            assert 'elapsed_seconds' in session_data[0], "缺少elapsed_seconds字段"
            assert 'furnace_temperature' in session_data[0], "缺少furnace_temperature字段"
            self.print_success(f"查询到{len(session_data)}条会话数据")
            self.record_result('ignition', True)
            
            # 9. 时间范围查询
            self.print_test("9. 时间范围查询")
            from datetime import timedelta
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            time_range_data = db.get_data_by_time_range(
                start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            assert isinstance(time_range_data, list), "查询结果类型错误"
            self.print_success(f"时间范围查询到{len(time_range_data)}条数据")
            self.record_result('ignition', True)
            
            # 10. 统计信息
            self.print_test("10. 获取统计信息")
            stats = db.get_statistics('pv')
            assert stats is not None, "获取统计信息失败"
            assert 'max' in stats, "统计信息缺少max"
            assert 'min' in stats, "统计信息缺少min"
            assert 'avg' in stats, "统计信息缺少avg"
            self.print_success(f"炉膛温度统计 - 最大: {stats['max']}°C, "
                             f"最小: {stats['min']}°C, 平均: {stats['avg']:.2f}°C")
            self.record_result('ignition', True)
            
            # 11. 数据总数
            self.print_test("11. 获取数据总数")
            total = db.get_data_count()
            assert total >= 5, f"数据总数不正确，期望至少5条，实际{total}条"
            self.print_success(f"数据总数: {total}条")
            self.record_result('ignition', True)
            
            # 12. 记录着火点检测（实时方法）
            self.print_test("12. 记录着火点检测（实时方法）")
            detection_id = db.record_ignition_detection(
                session_id=session_id,
                channel=1,
                ignition_temperature=180.5,
                detection_method='realtime'
            )
            assert detection_id > 0, "记录着火点检测失败"
            self.print_success(f"着火点检测已记录，ID: {detection_id}, 通道1, 温度180.5°C")
            self.record_result('ignition', True)
            
            # 13. 记录着火点检测（切线方法）
            self.print_test("13. 记录着火点检测（切线方法）")
            success = db.upsert_ignition_detection(
                session_id=session_id,
                channel=2,
                ignition_temperature=185.0,
                detection_method='tangent',
                image_path="test_images/tangent_ch2.jpg"
            )
            assert success, "记录切线法检测失败"
            self.print_success("切线法检测已记录，通道2")
            self.record_result('ignition', True)
            
            # 14. 查询着火点检测记录
            self.print_test("14. 查询着火点检测记录")
            detections = db.get_ignition_detections(session_id=session_id)
            assert len(detections) >= 2, f"查询检测记录失败，期望至少2条，实际{len(detections)}条"
            self.print_success(f"查询到{len(detections)}条检测记录")
            self.record_result('ignition', True)
            
            # 15. 更新数据
            self.print_test("15. 更新数据")
            success = db.update_data_by_id(record_id, pv=155.0, ch1=28.0)
            assert success, "更新数据失败"
            updated_data = db.get_data_by_id(record_id)
            assert updated_data['pv'] == 155.0, "更新后的值不匹配"
            assert updated_data['ch1'] == 28.0, "更新后的值不匹配"
            self.print_success("数据已更新")
            self.record_result('ignition', True)
            
            # 16. 更新会话信息
            self.print_test("16. 更新会话信息")
            success = db.update_session(session_id, description="更新后的描述")
            assert success, "更新会话失败"
            sessions = db.get_all_experiment_sessions()
            updated_session = next((s for s in sessions if s['id'] == session_id), None)
            assert updated_session['description'] == "更新后的描述", "更新后的描述不匹配"
            self.print_success("会话信息已更新")
            self.record_result('ignition', True)
            
            # 17. 结束实验会话
            self.print_test("17. 结束实验会话")
            success = db.end_experiment_session(session_id, status='completed')
            assert success, "结束会话失败"
            sessions = db.get_all_experiment_sessions()
            ended_session = next((s for s in sessions if s['id'] == session_id), None)
            assert ended_session['status'] == 'completed', "会话状态不匹配"
            assert ended_session['end_time'] is not None, "结束时间未设置"
            self.print_success("实验会话已结束")
            self.record_result('ignition', True)
            
            # 18. 导出CSV
            self.print_test("18. 导出CSV数据")
            csv_file = "test_ignition_export.csv"
            success = db.export_to_csv(csv_file)
            assert success, "导出CSV失败"
            assert os.path.exists(csv_file), "CSV文件不存在"
            self.print_success(f"数据已导出到: {csv_file}")
            # 清理测试文件
            if os.path.exists(csv_file):
                os.remove(csv_file)
            self.record_result('ignition', True)
            
            # 19. 备份数据库
            self.print_test("19. 备份数据库")
            backup_path = "test_ignition_backup.db"
            success = db.backup(backup_path)
            assert success, "备份数据库失败"
            assert os.path.exists(backup_path), "备份文件不存在"
            self.print_success(f"数据库已备份到: {backup_path}")
            # 清理测试文件
            if os.path.exists(backup_path):
                os.remove(backup_path)
            self.record_result('ignition', True)
            
            # 20. 边界条件测试 - 无效会话ID
            self.print_test("20. 边界条件测试 - 无效会话ID")
            invalid_data = db.get_session_temperature_data(-1)
            assert len(invalid_data) == 0, "应该返回空列表"
            self.print_success("无效会话ID处理正确")
            self.record_result('ignition', True)
            
            # 21. 边界条件测试 - 无效记录ID
            self.print_test("21. 边界条件测试 - 无效记录ID")
            invalid_record = db.get_data_by_id(-1)
            assert invalid_record is None, "应该返回None"
            success = db.update_data_by_id(-1, pv=100.0)
            assert not success, "更新无效记录应该失败"
            self.print_success("无效记录ID处理正确")
            self.record_result('ignition', True)
            
            # 22. 创建第二个会话
            self.print_test("22. 创建第二个会话")
            session_id2 = db.start_experiment_session(
                experiment_id="TEST-IGN-002",
                experiment_name="测试着火点实验2",
                sample_names=sample_names_json,
                client="测试单位",
                operator="测试操作员"
            )
            # 添加一些数据
            db.insert_batch_data([
                (200.0, 50.0, 51.0, 49.0, 52.0, 50.5, 49.5),
                (210.0, 55.0, 56.0, 54.0, 57.0, 55.5, 54.5),
            ], session_id=session_id2)
            # 记录着火点
            db.record_ignition_detection(session_id2, channel=3, ignition_temperature=200.0)
            db.end_experiment_session(session_id2, status='completed')
            self.print_success(f"第二个会话已创建并完成，ID: {session_id2}")
            self.record_result('ignition', True)
            
            # 23. 删除数据
            self.print_test("23. 删除单条数据")
            data_count_before = db.get_data_count()
            success = db.delete_data_by_id(record_id)
            assert success, "删除数据失败"
            data_count_after = db.get_data_count()
            assert data_count_after == data_count_before - 1, "删除后数量不匹配"
            self.print_success("数据已删除")
            self.record_result('ignition', True)
            
            # 24. 删除会话
            self.print_test("24. 删除会话")
            success = db.delete_session(session_id2)
            assert success, "删除会话失败"
            sessions = db.get_all_experiment_sessions()
            deleted_session = next((s for s in sessions if s['id'] == session_id2), None)
            assert deleted_session is None, "会话应该已被删除"
            self.print_success("会话已删除")
            self.record_result('ignition', True)
            
            # 关闭数据库
            db.close()
            
        except Exception as e:
            self.print_error(str(e))
            import traceback
            self.record_result('ignition', False, f"{str(e)}\n{traceback.format_exc()}")
    
    # ==================== 测试报告 ====================
    
    def print_summary(self):
        """打印测试总结"""
        self.print_header("测试总结")
        
        print("\n爆炸性数据库测试结果:")
        explosion = self.test_results['explosion']
        print(f"  通过: {explosion['passed']}")
        print(f"  失败: {explosion['failed']}")
        if explosion['errors']:
            print(f"  错误详情:")
            for i, error in enumerate(explosion['errors'], 1):
                print(f"    {i}. {error[:100]}...")  # 只显示前100个字符
        
        print("\n着火点数据库测试结果:")
        ignition = self.test_results['ignition']
        print(f"  通过: {ignition['passed']}")
        print(f"  失败: {ignition['failed']}")
        if ignition['errors']:
            print(f"  错误详情:")
            for i, error in enumerate(ignition['errors'], 1):
                print(f"    {i}. {error[:100]}...")  # 只显示前100个字符
        
        total_passed = explosion['passed'] + ignition['passed']
        total_failed = explosion['failed'] + ignition['failed']
        total_tests = total_passed + total_failed
        
        print(f"\n总计:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {total_passed}")
        print(f"  失败: {total_failed}")
        print(f"  通过率: {total_passed/total_tests*100:.1f}%" if total_tests > 0 else "  通过率: N/A")
        
        if total_failed == 0:
            print("\n✓ 所有测试通过！")
        else:
            print(f"\n✗ 有 {total_failed} 个测试失败，请检查错误详情")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*80)
        print("  数据库系统测试")
        print("="*80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 运行测试
        self.test_explosion_database()
        self.test_ignition_database()
        
        # 打印总结
        self.print_summary()


if __name__ == "__main__":
    tester = DatabaseSystemTester()
    tester.run_all_tests()
