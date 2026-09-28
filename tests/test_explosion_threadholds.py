#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试爆炸性阈值配置的适配情况
"""

import sys
import os

import pytest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.explosion_database import ExplosionDatabase


@pytest.mark.parametrize("flame_length, expected", [
    (15.0, "无爆炸性"),
    (24.9, "无爆炸性"),
    (25.0, "弱爆炸性"),
    (100.0, "弱爆炸性"),
    (399.9, "弱爆炸性"),
    (400.0, "强爆炸性"),
    (600.0, "强爆炸性"),
    (799.9, "强爆炸性"),
    (800.0, "超强爆炸性"),
    (1000.0, "超强爆炸性"),
])
def test_threshold_classification(tmp_path, flame_length, expected):
    """阈值分类必须与 configs/experiment_config.yaml 中的 explosion-thresholds 一致"""
    db = ExplosionDatabase(db_path=str(tmp_path / "test_thresholds.db"))
    try:
        assert db.classify_explosion_strength(flame_length) == expected, (
            f"{flame_length} mm -> {db.classify_explosion_strength(flame_length)}，期望 {expected}"
        )
    finally:
        db.close()


def test_threshold_levels_are_contiguous(tmp_path):
    """各等级区间必须首尾相接，不能有缝隙或重叠"""
    db = ExplosionDatabase(db_path=str(tmp_path / "test_thresholds.db"))
    try:
        levels = db.EXPLOSION_LEVELS
        assert levels['none']['max'] == levels['weak']['min']
        assert levels['weak']['max'] == levels['strong']['min']
        assert levels['strong']['max'] == levels['super']['min']
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
