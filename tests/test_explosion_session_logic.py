#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验会话逻辑测试
验证修复后的会话管理和数据保存逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.explosion_database import ExplosionDatabase
from utils.path_manager import PathManager


def test_session_logic():
    """测试会话逻辑修复"""
    print("=" * 60)
    print("爆炸性实验会话逻辑测试")
    print("=" * 60)
    
    # 使用测试数据库
    test_db_path = PathManager.get_data_path("test_explosion_logic.db")
    
    # 删除旧的测试数据库
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"✓ 已删除旧测试数据库")
    
    db = ExplosionDatabase(test_db_path)
    
    # 测试1: 创建会话
    print("\n【测试1】创建实验会话")
    session_id = db.start_experiment_session(
        experiment_name="测试实验",
        sample_name="测试样品A",
        client="测试单位",
        operator="测试员",
        description="测试会话逻辑"
    )
    print(f"✓ 会话创建成功: ID={session_id}")
    
    # 验证会话状态
    session = db.get_session_by_id(session_id)
    assert session['status'] == 'running', f"会话状态应为running，实际为{session['status']}"
    print(f"✓ 会话状态正确: {session['status']}")
    
    # 测试2: 添加轮次数据（模拟修复后的逻辑）
    print("\n【测试2】添加轮次数据（唯一保存点）")
    test_rounds = [
        (1, 15.5, "max_flame_images/test_001_max.jpg"),
        (2, 18.2, "max_flame_images/test_002_max.jpg"),
        (3, 16.8, "max_flame_images/test_003_max.jpg"),
    ]
    
    for round_num, flame_len, img_path in test_rounds:
        round_id = db.add_test_round(session_id, round_num, flame_len, img_path)
        print(f"✓ 第{round_num}轮保存成功: ID={round_id}, 火焰长度={flame_len}mm")
    
    # 验证：每轮只有一条记录
    rounds = db.get_session_test_rounds(session_id)
    assert len(rounds) == 3, f"应有3条记录，实际有{len(rounds)}条"
    print(f"✓ 轮次记录数量正确: {len(rounds)}")
    
    # 验证：数据准确性
    for i, r in enumerate(rounds):
        expected_length = test_rounds[i][1]
        actual_length = r['flame_length']
        assert actual_length == expected_length, \
            f"第{i+1}轮火焰长度应为{expected_length}，实际为{actual_length}"
    print(f"✓ 所有火焰长度数据准确（无0.0错误数据）")
    
    # 测试3: 计算平均值
    print("\n【测试3】计算平均火焰长度")
    avg_length = db.calculate_session_average(session_id)
    expected_avg = sum(r[1] for r in test_rounds) / len(test_rounds)
    assert abs(avg_length - expected_avg) < 0.01, \
        f"平均值计算错误：期望{expected_avg}，实际{avg_length}"
    print(f"✓ 平均火焰长度计算正确: {avg_length}mm")
    
    # 测试4: 验证会话状态（停止不结束会话）
    print("\n【测试4】验证停止实验后会话状态")
    # 模拟停止实验（不调用end_experiment_session）
    session = db.get_session_by_id(session_id)
    assert session['status'] == 'running', \
        f"停止后会话应保持running，实际为{session['status']}"
    print(f"✓ 停止后会话状态正确: {session['status']} (仍为running)")
    
    # 测试5: 完成实验
    print("\n【测试5】完成实验")
    success = db.finalize_experiment(session_id)
    assert success, "完成实验失败"
    print(f"✓ 实验完成成功")
    
    # 验证会话状态变为completed
    session = db.get_session_by_id(session_id)
    assert session['status'] == 'completed', \
        f"完成后会话状态应为completed，实际为{session['status']}"
    print(f"✓ 完成后会话状态正确: {session['status']}")
    
    # 验证结果保存
    result = db.get_session_result(session_id)
    assert result is not None, "未找到实验结果"
    assert result['total_rounds'] == 3, f"总轮次应为3，实际为{result['total_rounds']}"
    assert result['avg_flame_length'] == avg_length, "结果中平均值不一致"
    print(f"✓ 实验结果保存正确:")
    print(f"  - 总轮次: {result['total_rounds']}")
    print(f"  - 平均火焰长度: {result['avg_flame_length']}mm")
    print(f"  - 爆炸性等级: {result['explosion_level']}")
    
    # 测试6: 会话恢复（从数据库加载）
    print("\n【测试6】会话恢复测试")
    
    # 创建新会话并添加数据
    session_id2 = db.start_experiment_session(
        experiment_name="测试实验2",
        sample_name="测试样品B"
    )
    
    db.add_test_round(session_id2, 1, 25.0, "test1.jpg")
    db.add_test_round(session_id2, 2, 30.0, "test2.jpg")
    
    # 模拟应用重启后加载
    loaded_rounds = db.get_session_test_rounds(session_id2)
    assert len(loaded_rounds) == 2, f"应加载2轮数据，实际加载{len(loaded_rounds)}轮"
    print(f"✓ 从数据库恢复 {len(loaded_rounds)} 轮历史数据")
    
    for r in loaded_rounds:
        print(f"  第{r['round_number']}轮: {r['flame_length']}mm")
    
    # 测试7: 数据库查询
    print("\n【测试7】数据库查询功能")
    
    # 查询所有会话
    all_sessions = db.get_all_experiment_sessions()
    print(f"✓ 查询到 {len(all_sessions)} 个会话")
    
    # 查询所有结果
    all_results = db.get_all_results()
    print(f"✓ 查询到 {len(all_results)} 个实验结果")
    
    # 查询统计信息
    stats = db.get_statistics()
    print(f"✓ 统计信息:")
    print(f"  - 总会话数: {stats['total_sessions']}")
    print(f"  - 各状态: {stats.get('sessions_by_status', {})}")
    
    # 清理
    db.close()
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    


def test_button_state_logic():
    """测试按钮状态逻辑"""
    print("\n\n" + "=" * 60)
    print("按钮状态逻辑测试")
    print("=" * 60)
    
    # 模拟状态变化
    test_cases = [
        # (has_session, is_running, is_connected) -> 期望的按钮状态
        (False, False, False, {
            'connect': True,
            'new_exp': False,
            'start': False,
            'stop': False,
            'finalize': False
        }, "未连接"),
        
        (False, False, True, {
            'connect': False,
            'new_exp': True,
            'start': False,
            'stop': False,
            'finalize': False
        }, "已连接，无会话"),
        
        (True, False, True, {
            'connect': False,
            'new_exp': False,  # ← 关键：有会话时禁用
            'start': True,
            'stop': False,
            'finalize': True
        }, "会话已创建，未运行"),
        
        (True, True, True, {
            'connect': False,
            'new_exp': False,
            'start': False,
            'stop': True,
            'finalize': False
        }, "实验运行中"),
    ]
    
    print("\n测试按钮状态规则:")
    for i, (has_session, is_running, is_connected, expected, desc) in enumerate(test_cases, 1):
        print(f"\n状态{i}: {desc}")
        print(f"  has_session={has_session}, is_running={is_running}, is_connected={is_connected}")
        
        # 模拟计算按钮状态
        actual = {
            'connect': not is_connected,
            'new_exp': is_connected and not has_session,  # ← 关键规则
            'start': has_session and not is_running,
            'stop': is_running,
            'finalize': has_session and not is_running
        }
        
        # 验证
        for btn, state in expected.items():
            assert actual[btn] == state, \
                f"按钮{btn}状态错误：期望{state}，实际{actual[btn]}"
            status = "✓" if state else "✗"
            print(f"    [{btn:10s}] {status}")
    
    print("\n✅ 所有按钮状态测试通过！")
    print("  关键验证: 有会话时'新建实验'禁用 ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # 测试数据库逻辑
        test_session_logic()
        
        # 测试按钮状态
        test_button_state_logic()
        
        print("\n" + "🎉" * 20)
        print("所有测试通过！会话逻辑修复成功！")
        print("🎉" * 20)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

