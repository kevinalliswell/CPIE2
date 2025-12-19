#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验数据库模块测试脚本
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.explosion_database import ExplosionDatabase
import tempfile
import shutil


class TestExplosionDatabase:
    """爆炸性实验数据库测试类"""
    
    def __init__(self):
        self.test_db_path = "test_explosion_temp.db"
        self.db = None
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
    
    def setup(self):
        """测试前准备"""
        # 删除旧的测试数据库
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # 创建新的数据库实例
        self.db = ExplosionDatabase(self.test_db_path)
        print("✓ 测试环境准备完成\n")
    
    def teardown(self):
        """测试后清理"""
        if self.db:
            self.db.close()
        
        # 清理测试文件
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # 清理导出的 CSV 文件
        for file in ["test_export_all.csv", "test_export_session.csv"]:
            if os.path.exists(file):
                os.remove(file)
        
        print("\n✓ 测试环境清理完成")
    
    def assert_equal(self, actual, expected, test_name):
        """断言相等"""
        self.total_tests += 1
        if actual == expected:
            print(f"✓ {test_name}: 通过")
            self.passed_tests += 1
            return True
        else:
            print(f"✗ {test_name}: 失败 (期望: {expected}, 实际: {actual})")
            self.failed_tests += 1
            return False
    
    def assert_not_none(self, value, test_name):
        """断言不为空"""
        self.total_tests += 1
        if value is not None:
            print(f"✓ {test_name}: 通过")
            self.passed_tests += 1
            return True
        else:
            print(f"✗ {test_name}: 失败 (值为 None)")
            self.failed_tests += 1
            return False
    
    def assert_true(self, condition, test_name):
        """断言为真"""
        self.total_tests += 1
        if condition:
            print(f"✓ {test_name}: 通过")
            self.passed_tests += 1
            return True
        else:
            print(f"✗ {test_name}: 失败 (条件为假)")
            self.failed_tests += 1
            return False
    
    def test_create_session(self):
        """测试创建实验会话"""
        print("\n【测试 1: 创建实验会话】")
        session_id = self.db.start_experiment_session(
            experiment_name="测试实验1",
            sample_name="测试煤样A",
            description="这是一个测试"
        )
        
        self.assert_true(session_id > 0, "创建会话成功，返回有效ID")
        
        # 验证会话信息
        session = self.db.get_session_by_id(session_id)
        self.assert_not_none(session, "可以查询到创建的会话")
        self.assert_equal(session['experiment_name'], "测试实验1", "实验名称正确")
        self.assert_equal(session['sample_name'], "测试煤样A", "样品名称正确")
        self.assert_equal(session['status'], 'running', "会话状态为运行中")
        
        return session_id
    
    def test_add_test_rounds(self, session_id):
        """测试添加测试轮次"""
        print("\n【测试 2: 添加测试轮次】")
        
        # 单个添加
        round_id = self.db.add_test_round(
            session_id, 
            round_number=1, 
            flame_length=25.5,
            max_flame_image_path="test/image1.jpg"
        )
        self.assert_true(round_id > 0, "单个添加测试轮次成功")
        
        # 批量添加
        batch_data = [
            (2, 28.3, "test/image2.jpg"),
            (3, 26.7, "test/image3.jpg"),
            (4, 27.1, "test/image4.jpg"),
            (5, 29.0, "test/image5.jpg"),
        ]
        count = self.db.add_batch_test_rounds(session_id, batch_data)
        self.assert_equal(count, 4, "批量添加4轮测试数据成功")
        
        # 验证轮次数据
        rounds = self.db.get_session_test_rounds(session_id)
        self.assert_equal(len(rounds), 5, "共有5轮测试数据")
        self.assert_equal(rounds[0]['round_number'], 1, "轮次编号正确")
        self.assert_equal(rounds[0]['flame_length'], 25.5, "火焰长度正确")
    
    def test_calculate_average(self, session_id):
        """测试计算平均值"""
        print("\n【测试 3: 计算平均火焰长度】")
        
        avg = self.db.calculate_session_average(session_id)
        self.assert_not_none(avg, "计算平均值成功")
        
        # 手动计算验证: (25.5 + 28.3 + 26.7 + 27.1 + 29.0) / 5 = 27.32
        expected_avg = 27.32
        self.assert_equal(avg, expected_avg, f"平均值计算正确: {avg}mm")
    
    def test_explosion_classification(self):
        """测试爆炸性分类"""
        print("\n【测试 4: 爆炸性等级分类】")
        
        # 测试各个等级
        test_cases = [
            (10, "无爆炸性"),
            (19.9, "无爆炸性"),
            (20, "弱爆炸性"),
            (200, "弱爆炸性"),
            (399.9, "弱爆炸性"),
            (400, "强爆炸性"),
            (600, "强爆炸性"),
            (799.9, "强爆炸性"),
            (800, "超强爆炸性"),
            (1000, "超强爆炸性"),
        ]
        
        for flame_length, expected_level in test_cases:
            actual_level = self.db.classify_explosion_strength(flame_length)
            self.assert_equal(
                actual_level, 
                expected_level, 
                f"火焰长度 {flame_length}mm 分类为 {expected_level}"
            )
    
    def test_finalize_experiment(self, session_id):
        """测试完成实验"""
        print("\n【测试 5: 完成实验并保存结果】")
        
        success = self.db.finalize_experiment(session_id)
        self.assert_true(success, "完成实验成功")
        
        # 验证结果
        result = self.db.get_session_result(session_id)
        self.assert_not_none(result, "可以查询到实验结果")
        self.assert_equal(result['total_rounds'], 5, "测试轮次数正确")
        self.assert_equal(result['avg_flame_length'], 27.32, "平均火焰长度正确")
        self.assert_equal(result['explosion_level'], "弱爆炸性", "爆炸性等级分类正确")
        
        # 验证会话状态已更新
        session = self.db.get_session_by_id(session_id)
        self.assert_equal(session['status'], 'completed', "会话状态已更新为完成")
    
    def test_multiple_sessions(self):
        """测试多个实验会话"""
        print("\n【测试 6: 创建多个不同爆炸性等级的实验】")
        
        test_scenarios = [
            {
                'name': "无爆炸性样品",
                'sample': "煤样-无爆炸",
                'data': [(i, 15 + i*0.5, f"img{i}.jpg") for i in range(1, 6)],
                'expected_level': "无爆炸性"
            },
            {
                'name': "强爆炸性样品",
                'sample': "煤样-强爆炸",
                'data': [(i, 500 + i*10, f"img{i}.jpg") for i in range(1, 6)],
                'expected_level': "强爆炸性"
            },
            {
                'name': "超强爆炸性样品",
                'sample': "煤样-超强爆炸",
                'data': [(i, 850 + i*5, f"img{i}.jpg") for i in range(1, 6)],
                'expected_level': "超强爆炸性"
            },
        ]
        
        session_ids = []
        for scenario in test_scenarios:
            session_id = self.db.start_experiment_session(
                experiment_name=scenario['name'],
                sample_name=scenario['sample']
            )
            session_ids.append(session_id)
            
            self.db.add_batch_test_rounds(session_id, scenario['data'])
            self.db.finalize_experiment(session_id)
            
            result = self.db.get_session_result(session_id)
            self.assert_equal(
                result['explosion_level'], 
                scenario['expected_level'],
                f"{scenario['name']} 分类正确"
            )
        
        return session_ids
    
    def test_query_functions(self, session_ids):
        """测试查询功能"""
        print("\n【测试 7: 查询功能】")
        
        # 查询所有会话
        all_sessions = self.db.get_all_sessions()
        self.assert_true(
            len(all_sessions) >= 4, 
            f"查询到所有会话 (共{len(all_sessions)}个)"
        )
        
        # 按状态查询
        completed_sessions = self.db.get_all_sessions(status='completed')
        self.assert_true(
            len(completed_sessions) >= 4, 
            f"查询到已完成的会话 (共{len(completed_sessions)}个)"
        )
        
        # 查询所有结果
        all_results = self.db.get_all_results()
        self.assert_true(
            len(all_results) >= 4, 
            f"查询到所有实验结果 (共{len(all_results)}个)"
        )
        
        # 按爆炸性等级查询
        levels_to_test = ["无爆炸性", "弱爆炸性", "强爆炸性", "超强爆炸性"]
        for level in levels_to_test:
            results = self.db.get_results_by_explosion_level(level)
            if results:
                self.assert_true(
                    all(r['explosion_level'] == level for r in results),
                    f"查询 {level} 结果正确"
                )
    
    def test_statistics(self):
        """测试统计功能"""
        print("\n【测试 8: 统计信息】")
        
        stats = self.db.get_statistics()
        self.assert_not_none(stats, "获取统计信息成功")
        self.assert_true(stats['total_sessions'] >= 4, "总会话数统计正确")
        self.assert_true(
            'sessions_by_status' in stats, 
            "包含按状态统计的会话数"
        )
        self.assert_true(
            'results_by_level' in stats, 
            "包含按爆炸性等级统计的结果数"
        )
        self.assert_true(
            'flame_length_stats' in stats, 
            "包含火焰长度统计信息"
        )
        
        print(f"  总会话数: {stats['total_sessions']}")
        print(f"  各状态会话: {stats['sessions_by_status']}")
        print(f"  各爆炸性等级: {stats['results_by_level']}")
        if 'flame_length_stats' in stats:
            fls = stats['flame_length_stats']
            print(f"  火焰长度: 平均={fls['avg']}mm, 最小={fls['min']}mm, 最大={fls['max']}mm")
    
    def test_update_operations(self):
        """测试更新操作"""
        print("\n【测试 9: 更新操作】")
        
        # 创建测试会话
        session_id = self.db.start_experiment_session(
            experiment_name="待更新实验",
            sample_name="待更新样品"
        )
        
        # 更新会话信息
        success = self.db.update_session(
            session_id,
            experiment_name="已更新实验",
            sample_name="已更新样品",
            description="更新描述"
        )
        self.assert_true(success, "更新会话信息成功")
        
        # 验证更新
        session = self.db.get_session_by_id(session_id)
        self.assert_equal(session['experiment_name'], "已更新实验", "实验名称已更新")
        self.assert_equal(session['sample_name'], "已更新样品", "样品名称已更新")
        
        # 添加测试轮次并更新
        round_id = self.db.add_test_round(session_id, 1, 100.0, "old_path.jpg")
        success = self.db.update_test_round(
            round_id,
            flame_length=150.0,
            max_flame_image_path="new_path.jpg"
        )
        self.assert_true(success, "更新测试轮次成功")
        
        # 验证更新
        rounds = self.db.get_session_test_rounds(session_id)
        self.assert_equal(rounds[0]['flame_length'], 150.0, "火焰长度已更新")
        self.assert_equal(
            rounds[0]['max_flame_image_path'], 
            "new_path.jpg", 
            "图片路径已更新"
        )
    
    def test_delete_operations(self):
        """测试删除操作"""
        print("\n【测试 10: 删除操作】")
        
        # 创建测试会话
        session_id = self.db.start_experiment_session(
            experiment_name="待删除实验",
            sample_name="待删除样品"
        )
        
        # 添加测试轮次
        round_id = self.db.add_test_round(session_id, 1, 100.0, "test.jpg")
        
        # 删除单个测试轮次
        success = self.db.delete_test_round(round_id)
        self.assert_true(success, "删除单个测试轮次成功")
        
        # 验证删除
        rounds = self.db.get_session_test_rounds(session_id)
        self.assert_equal(len(rounds), 0, "测试轮次已被删除")
        
        # 删除会话（级联删除）
        success = self.db.delete_session(session_id)
        self.assert_true(success, "删除会话成功")
        
        # 验证删除
        session = self.db.get_session_by_id(session_id)
        self.assert_equal(session, None, "会话已被删除")
    
    def test_export_functions(self, session_id):
        """测试导出功能"""
        print("\n【测试 11: 导出功能】")
        
        # 导出所有结果
        success = self.db.export_to_csv("test_export_all.csv")
        self.assert_true(success, "导出所有结果成功")
        self.assert_true(
            os.path.exists("test_export_all.csv"), 
            "导出文件已创建"
        )
        
        # 导出特定会话
        success = self.db.export_to_csv("test_export_session.csv", session_id)
        self.assert_true(success, "导出特定会话成功")
        self.assert_true(
            os.path.exists("test_export_session.csv"), 
            "会话导出文件已创建"
        )
        
        # 验证文件内容（简单检查）
        with open("test_export_all.csv", 'r', encoding='utf-8-sig') as f:
            content = f.read()
            self.assert_true(
                "爆炸性等级" in content, 
                "导出文件包含中文表头"
            )
    
    def test_backup_function(self):
        """测试备份功能"""
        print("\n【测试 12: 数据库备份】")
        
        backup_path = "test_backup.db"
        success = self.db.backup(backup_path)
        self.assert_true(success, "数据库备份成功")
        self.assert_true(os.path.exists(backup_path), "备份文件已创建")
        
        # 验证备份文件大小
        original_size = os.path.getsize(self.test_db_path)
        backup_size = os.path.getsize(backup_path)
        self.assert_equal(original_size, backup_size, "备份文件大小与原文件一致")
        
        # 清理备份文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
    
    def test_edge_cases(self):
        """测试边界情况"""
        print("\n【测试 13: 边界情况】")
        
        # 测试空会话的平均值计算
        empty_session_id = self.db.start_experiment_session(
            experiment_name="空会话",
            sample_name="无数据"
        )
        avg = self.db.calculate_session_average(empty_session_id)
        self.assert_equal(avg, None, "空会话计算平均值返回 None")
        
        # 测试完成空会话
        success = self.db.finalize_experiment(empty_session_id)
        self.assert_equal(success, False, "完成空会话返回失败")
        
        # 测试查询不存在的ID
        session = self.db.get_session_by_id(99999)
        self.assert_equal(session, None, "查询不存在的会话返回 None")
        
        # 测试更新不存在的ID
        success = self.db.update_session(99999, experiment_name="不存在")
        self.assert_equal(success, False, "更新不存在的会话返回失败")
        
        # 测试删除不存在的ID
        success = self.db.delete_session(99999)
        self.assert_equal(success, False, "删除不存在的会话返回失败")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*70)
        print("爆炸性实验数据库模块 - 完整测试")
        print("="*70)
        
        try:
            self.setup()
            
            # 运行测试
            session_id = self.test_create_session()
            self.test_add_test_rounds(session_id)
            self.test_calculate_average(session_id)
            self.test_explosion_classification()
            self.test_finalize_experiment(session_id)
            session_ids = self.test_multiple_sessions()
            self.test_query_functions(session_ids)
            self.test_statistics()
            self.test_update_operations()
            self.test_delete_operations()
            self.test_export_functions(session_id)
            self.test_backup_function()
            self.test_edge_cases()
            
        finally:
            self.teardown()
        
        # 输出测试结果
        print("\n" + "="*70)
        print("测试结果汇总")
        print("="*70)
        print(f"总测试数: {self.total_tests}")
        print(f"✓ 通过: {self.passed_tests}")
        print(f"✗ 失败: {self.failed_tests}")
        print(f"通过率: {self.passed_tests/self.total_tests*100:.1f}%")
        print("="*70)
        
        if self.failed_tests == 0:
            print("\n🎉 所有测试通过！")
            return True
        else:
            print(f"\n⚠️  有 {self.failed_tests} 个测试失败")
            return False


def main():
    """主函数"""
    tester = TestExplosionDatabase()
    success = tester.run_all_tests()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

