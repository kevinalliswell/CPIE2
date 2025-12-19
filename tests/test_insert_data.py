#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：为着火点和爆炸性实验各插入3条完整的测试数据
"""

import os
import sys
import json
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.ignition_database import IgnitionDatabase
from models.explosion_database import ExplosionDatabase


def create_ignition_test_data():
    """创建着火点实验测试数据"""
    print("\n" + "="*60)
    print("创建着火点实验测试数据")
    print("="*60)
    
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    
    # 初始化数据库
    db = IgnitionDatabase(os.path.join("data", "ignition_experiment.db"))
    
    # 测试数据
    test_experiments = [
        {
            "experiment_id": "IGN-20241201-001",
            "experiment_name": "煤样A系列着火点测试",
            "sample_names": ["煤样A-1", "煤样A-2", "煤样A-3", "煤样A-4", "煤样A-5", "煤样A-6"],
            "client": "某某煤矿有限公司",
            "operator": "张三",
            "description": "煤样A系列着火点测试",
            "ignition_results": [
                (1, 285.5),
                (2, 290.3),
                (3, 278.9),
                (4, 292.1),
                (5, 287.6),
                (6, 289.4)
            ]
        },
        {
            "experiment_id": "IGN-20241201-002",
            "experiment_name": "煤样B系列着火点测试",
            "sample_names": ["煤样B-1", "煤样B-2", "煤样B-3", "煤样B-4", "煤样B-5", "煤样B-6"],
            "client": "另一煤业集团",
            "operator": "李四",
            "description": "煤样B系列着火点测试",
            "ignition_results": [
                (1, 310.2),
                (2, 315.8),
                (3, 308.5),
                (4, 312.9),
                (5, 314.3),
                (6, 313.5)  # 补充通道6的数据
            ]
        },
        {
            "experiment_id": "IGN-20241201-003",
            "experiment_name": "标准煤样对照实验",
            "sample_names": ["标准煤-1", "标准煤-2", "标准煤-3", "标准煤-4", "标准煤-5", "标准煤-6"],
            "client": "标准样品测试中心",
            "operator": "王五",
            "description": "标准煤样对照实验",
            "ignition_results": [
                (1, 295.7),
                (2, 298.2),
                (3, 293.5),
                (4, 296.8),
                (5, 297.1),
                (6, 294.9)
            ]
        }
    ]
    
    for idx, exp_data in enumerate(test_experiments, 1):
        print(f"\n{idx}. 创建实验: {exp_data['experiment_id']}")
        
        # 创建实验会话
        session_id = db.start_experiment_session(
            experiment_id=exp_data['experiment_id'],
            experiment_name=exp_data['experiment_name'],
            sample_names=json.dumps(exp_data['sample_names'], ensure_ascii=False),
            client=exp_data['client'],
            operator=exp_data['operator'],
            description=exp_data['description']
        )
        
        if session_id > 0:
            print(f"   会话ID: {session_id}")
            print(f"   样品数: {len(exp_data['sample_names'])}")
            
            # 更新会话状态为运行中
            db.update_session(session_id, status='running')
            
            # 添加着火点检测结果
            for channel, temp in exp_data['ignition_results']:
                db.record_ignition_detection(session_id, channel, temp)
                print(f"   通道{channel}: {temp}°C")
            
            # 结束实验
            db.end_experiment_session(session_id, status='completed')
            print("   ✓ 实验完成")
        else:
            print("   ✗ 创建实验失败")
    
    db.close()
    print("\n" + "="*60)
    print("着火点实验数据创建完成")
    print("="*60)


def create_explosion_test_data():
    """创建爆炸性实验测试数据"""
    print("\n" + "="*60)
    print("创建爆炸性实验测试数据")
    print("="*60)
    
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    
    # 初始化数据库
    db = ExplosionDatabase(os.path.join("data", "explosion_experiment.db"))
    
    # 测试数据
    test_experiments = [
        {
            "experiment_id": "EXP-20241201-001",
            "experiment_name": "粉尘样品A爆炸性测试",
            "sample_name": "粉尘样品A",
            "client": "某某矿业集团",
            "operator": "赵六",
            "description": "粉尘样品A爆炸性测试",
            "test_rounds": [
                (1, 15.5, "images/exp1_round1.jpg"),
                (2, 18.2, "images/exp1_round2.jpg"),
                (3, 16.8, "images/exp1_round3.jpg"),
                (4, 17.5, "images/exp1_round4.jpg"),
                (5, 19.0, "images/exp1_round5.jpg"),
            ]
        },
        {
            "experiment_id": "EXP-20241201-002",
            "experiment_name": "粉尘样品B爆炸性测试",
            "sample_name": "粉尘样品B",
            "client": "北京科技大学",
            "operator": "孙七",
            "description": "粉尘样品B爆炸性测试",
            "test_rounds": [
                (1, 520.5, "images/exp2_round1.jpg"),
                (2, 580.2, "images/exp2_round2.jpg"),
                (3, 550.8, "images/exp2_round3.jpg"),
                (4, 600.5, "images/exp2_round4.jpg"),
                (5, 590.0, "images/exp2_round5.jpg"),
            ]
        },
        {
            "experiment_id": "EXP-20241201-003",
            "experiment_name": "粉尘样品C爆炸性测试 - 10轮完整测试",
            "sample_name": "粉尘样品C",
            "client": "安全检测中心",
            "operator": "周八",
            "description": "粉尘样品C爆炸性测试 - 10轮完整测试",
            "test_rounds": [
                (1, 22.5, "images/exp3_round1.jpg"),
                (2, 25.0, "images/exp3_round2.jpg"),
                (3, 23.8, "images/exp3_round3.jpg"),
                (4, 24.2, "images/exp3_round4.jpg"),
                (5, 26.5, "images/exp3_round5.jpg"),
                (6, 350.5, "images/exp3_round6.jpg"),
                (7, 380.2, "images/exp3_round7.jpg"),
                (8, 365.8, "images/exp3_round8.jpg"),
                (9, 375.3, "images/exp3_round9.jpg"),
                (10, 390.1, "images/exp3_round10.jpg"),
            ]
        }
    ]
    
    for idx, exp_data in enumerate(test_experiments, 1):
        print(f"\n{idx}. 创建实验: {exp_data['experiment_id']}")
        
        # 创建实验会话
        session_id = db.start_experiment_session(
            experiment_id=exp_data['experiment_id'],
            experiment_name=exp_data['experiment_name'],
            sample_name=exp_data['sample_name'],
            client=exp_data['client'],
            operator=exp_data['operator'],
            description=exp_data['description']
        )
        
        if session_id > 0:
            print(f"   会话ID: {session_id}")
            print(f"   样品: {exp_data['sample_name']}")
            print(f"   委托单位: {exp_data['client']}")
            print(f"   操作员: {exp_data['operator']}")
            
            # 添加测试轮次数据
            for round_num, flame_len, img_path in exp_data['test_rounds']:
                db.add_test_round(session_id, round_num, flame_len, img_path)
                print(f"   第{round_num}轮: {flame_len}mm")
            
            # 完成实验（自动计算平均值和爆炸性等级）
            db.finalize_experiment(session_id, status='completed')
            
            # 获取结果
            result = db.get_session_result(session_id)
            if result:
                print("   ✓ 实验完成")
                print(f"   平均火焰长度: {result['avg_flame_length']}mm")
                print(f"   爆炸性等级: {result['explosion_level']}")
        else:
            print("   ✗ 创建实验失败")
    
    db.close()
    print("\n" + "="*60)
    print("爆炸性实验数据创建完成")
    print("="*60)


def verify_data():
    """验证插入的数据"""
    print("\n" + "="*60)
    print("验证数据")
    print("="*60)
    
    # 验证着火点数据
    print("\n1. 着火点实验数据:")
    ignition_db = IgnitionDatabase(os.path.join("data", "ignition_experiment.db"))
    ignition_sessions = ignition_db.get_all_experiment_sessions()
    print(f"   共 {len(ignition_sessions)} 条记录")
    for session in ignition_sessions[-3:]:  # 显示最后3条
        exp_id = session.get('experiment_id') or session.get('experiment_name', 'N/A')
        print(f"   - {exp_id} ({session['status']})")
    ignition_db.close()
    
    # 验证爆炸性数据
    print("\n2. 爆炸性实验数据:")
    explosion_db = ExplosionDatabase(os.path.join("data", "explosion_experiment.db"))
    explosion_sessions = explosion_db.get_all_experiment_sessions()
    print(f"   共 {len(explosion_sessions)} 条记录")
    for session in explosion_sessions[-3:]:  # 显示最后3条
        exp_id = session.get('experiment_id') or session.get('experiment_name', 'N/A')
        print(f"   - {exp_id} ({session['status']})")
    explosion_db.close()
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("\n🚀 开始插入测试数据...")
    
    try:
        # 创建着火点实验数据
        create_ignition_test_data()
        
        # 创建爆炸性实验数据
        create_explosion_test_data()
        
        # 验证数据
        verify_data()
        
        print("\n✅ 所有测试数据插入成功！")
        print("\n提示：现在可以运行主程序查看历史查询页面了。")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

