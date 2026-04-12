#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pytest coverage for the explosion experiment database."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from models.explosion_database import ExplosionDatabase


@pytest.fixture
def database(tmp_path):
    db_path = tmp_path / "explosion_test.db"
    db = ExplosionDatabase(str(db_path))
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def completed_session(database):
    session_id = database.start_experiment_session(
        experiment_name="基础爆炸实验",
        sample_name="测试煤样A",
        description="pytest fixture"
    )
    assert session_id > 0

    rounds = [
        (1, 25.5, "images/round_1.jpg"),
        (2, 28.3, "images/round_2.jpg"),
        (3, 26.7, "images/round_3.jpg"),
        (4, 27.1, "images/round_4.jpg"),
        (5, 29.0, "images/round_5.jpg"),
    ]
    assert database.add_batch_test_rounds(session_id, rounds) == len(rounds)
    assert database.finalize_experiment(session_id)
    return session_id


def test_start_session_and_add_rounds(database):
    session_id = database.start_experiment_session(
        experiment_name="创建会话测试",
        sample_name="样品A",
        description="验证创建与轮次写入"
    )

    assert session_id > 0

    session = database.get_session_by_id(session_id)
    assert session is not None
    assert session["experiment_name"] == "创建会话测试"
    assert session["sample_name"] == "样品A"
    assert session["status"] == "running"

    round_id = database.add_test_round(session_id, 1, 25.5, "images/test_1.jpg")
    assert round_id > 0

    rounds = database.get_session_test_rounds(session_id)
    assert len(rounds) == 1
    assert rounds[0]["round_number"] == 1
    assert rounds[0]["flame_length"] == 25.5
    assert rounds[0]["max_flame_image_path"] == "images/test_1.jpg"


def test_finalize_experiment_creates_summary(database):
    session_id = database.start_experiment_session(
        experiment_name="完成实验测试",
        sample_name="样品B"
    )
    database.add_batch_test_rounds(
        session_id,
        [
            (1, 25.5, "img1.jpg"),
            (2, 28.3, "img2.jpg"),
            (3, 26.7, "img3.jpg"),
            (4, 27.1, "img4.jpg"),
            (5, 29.0, "img5.jpg"),
        ],
    )

    assert database.calculate_session_average(session_id) == 27.32
    assert database.finalize_experiment(session_id)

    result = database.get_session_result(session_id)
    assert result is not None
    assert result["total_rounds"] == 5
    assert result["avg_flame_length"] == 27.32
    assert result["explosion_level"] == "弱爆炸性"

    session = database.get_session_by_id(session_id)
    assert session["status"] == "completed"


def test_classify_explosion_strength_uses_threshold_bands(database):
    assert database.classify_explosion_strength(10) == "无爆炸性"
    assert database.classify_explosion_strength(25.0) == "弱爆炸性"
    assert database.classify_explosion_strength(399.9) == "弱爆炸性"
    assert database.classify_explosion_strength(400.0) == "强爆炸性"
    assert database.classify_explosion_strength(800.0) == "超强爆炸性"


def test_query_and_statistics_methods(database, completed_session):
    extra_session = database.start_experiment_session(
        experiment_name="第二个实验",
        sample_name="样品C"
    )
    database.add_batch_test_rounds(
        extra_session,
        [(1, 850.0, "img1.jpg"), (2, 860.0, "img2.jpg")],
    )
    assert database.finalize_experiment(extra_session)

    sessions = database.get_all_experiment_sessions()
    assert len(sessions) >= 2

    completed_sessions = database.get_all_experiment_sessions(status="completed")
    assert any(session["id"] == completed_session for session in completed_sessions)

    all_results = database.get_all_results()
    assert len(all_results) >= 2

    strong_results = database.get_results_by_explosion_level("超强爆炸性")
    assert strong_results
    assert all(result["explosion_level"] == "超强爆炸性" for result in strong_results)

    stats = database.get_statistics()
    assert stats is not None
    assert stats["total_sessions"] >= 2
    assert "sessions_by_status" in stats
    assert "results_by_level" in stats
    assert "flame_length_stats" in stats


def test_update_delete_export_and_backup(database, tmp_path):
    session_id = database.start_experiment_session(
        experiment_name="待更新实验",
        sample_name="待更新样品"
    )
    assert session_id > 0

    assert database.update_session(
        session_id,
        experiment_name="已更新实验",
        sample_name="已更新样品",
        description="更新后的描述",
    )

    session = database.get_session_by_id(session_id)
    assert session["experiment_name"] == "已更新实验"
    assert session["sample_name"] == "已更新样品"

    round_id = database.add_test_round(session_id, 1, 100.0, "old_path.jpg")
    assert round_id > 0
    assert database.update_test_round(
        round_id,
        flame_length=150.0,
        max_flame_image_path="new_path.jpg",
    )

    rounds = database.get_session_test_rounds(session_id)
    assert rounds[0]["flame_length"] == 150.0
    assert rounds[0]["max_flame_image_path"] == "new_path.jpg"

    export_all = tmp_path / "export_all.csv"
    export_session = tmp_path / "export_session.csv"
    backup_file = tmp_path / "backup.db"

    assert database.finalize_experiment(session_id)
    assert database.export_to_csv(str(export_all))
    assert export_all.exists()
    assert "爆炸性等级" in export_all.read_text(encoding="utf-8-sig")

    assert database.export_to_csv(str(export_session), session_id)
    assert export_session.exists()

    assert database.backup(str(backup_file))
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    assert database.delete_test_round(round_id)
    assert database.get_session_test_rounds(session_id) == []

    assert database.delete_session(session_id)
    assert database.get_session_by_id(session_id) is None


def test_edge_cases_return_safe_values(database):
    empty_session = database.start_experiment_session(
        experiment_name="空实验",
        sample_name="无数据样品"
    )

    assert database.calculate_session_average(empty_session) is None
    assert database.finalize_experiment(empty_session) is False
    assert database.get_session_by_id(99999) is None
    assert database.update_session(99999, experiment_name="不存在") is False
    assert database.delete_session(99999) is False
