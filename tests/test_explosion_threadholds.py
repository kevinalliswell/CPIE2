#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试爆炸性阈值配置的适配情况
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.explosion_database import ExplosionDatabase

def test_threshold_loading():
    """测试阈值加载"""
    print("="*60)
    print("爆炸性阈值配置适配测试")
    print("="*60)
    
    # 创建数据库实例（使用测试数据库）
    db = ExplosionDatabase(db_path="test_thresholds.db")
    
    print("\n✓ 成功从配置文件加载爆炸性阈值")
    print("\n当前阈值配置：")
    print(f"  无爆炸性:   0 ~ {db.EXPLOSION_LEVELS['none']['max']} mm")
    print(f"  弱爆炸性:   {db.EXPLOSION_LEVELS['weak']['min']} ~ {db.EXPLOSION_LEVELS['weak']['max']} mm")
    print(f"  强爆炸性:   {db.EXPLOSION_LEVELS['strong']['min']} ~ {db.EXPLOSION_LEVELS['strong']['max']} mm")
    print(f"  超强爆炸性: {db.EXPLOSION_LEVELS['super']['min']} mm 以上")
    
    print("\n测试分类功能：")
    test_cases = [
        (15.0, "无爆炸性"),
        (24.9, "无爆炸性"),
        (25.0, "弱爆炸性"),
        (100.0, "弱爆炸性"),
        (399.9, "弱爆炸性"),
        (400.0, "强爆炸性"),
        (600.0, "强爆炸性"),
        (799.9, "强爆炸性"),
        (800.0, "超强爆炸性"),
        (1000.0, "超强爆炸性")
    ]
    
    all_passed = True
    for flame_length, expected in test_cases:
        result = db.classify_explosion_strength(flame_length)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} {flame_length:6.1f} mm -> {result:10s} (期望: {expected})")
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ 所有测试通过！阈值配置适配成功！")
    else:
        print("✗ 部分测试失败，请检查配置")
    print("="*60)
    
    # 清理测试数据库
    db.close()
    if os.path.exists("test_thresholds.db"):
        os.remove("test_thresholds.db")
        print("\n✓ 已清理测试数据库")

if __name__ == "__main__":
    test_threshold_loading()
