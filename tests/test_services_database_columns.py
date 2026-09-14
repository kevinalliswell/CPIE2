"""
services.database.ExperimentDatabase 在旧库结构上的读取测试

旧版本数据库的 experiments 表没有 analysis_results_json 列，升级时通过 ALTER TABLE 追加到
created_at 之后；按固定下标读取 SELECT * 会把 created_at 当作分析结果。
"""

import json
import sqlite3

import pytest

from services.database import ExperimentData, ExperimentDatabase

LEGACY_SCHEMA = """
    CREATE TABLE experiments (
        experiment_id TEXT PRIMARY KEY,
        experiment_name TEXT NOT NULL,
        sample_name TEXT NOT NULL,
        sample_weight REAL NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        description TEXT,
        operator TEXT,
        experiment_type TEXT,
        created_at TEXT NOT NULL
    )
"""


@pytest.fixture(params=["legacy", "fresh"])
def database(tmp_path, request):
    db_path = tmp_path / "experiments.db"
    if request.param == "legacy":
        with sqlite3.connect(db_path) as conn:
            conn.execute(LEGACY_SCHEMA)
    return ExperimentDatabase(str(db_path))


def _experiment(experiment_id="exp-1"):
    return ExperimentData(
        experiment_id=experiment_id,
        experiment_name="测试实验",
        sample_name="煤样A",
        sample_weight=1.5,
        start_time="2024-01-01T10:00:00",
        end_time="2024-01-01T11:00:00",
        description="desc",
        operator="op",
        experiment_type="explosion",
    )


def test_analysis_results_are_read_from_the_right_column(database):
    assert database.create_experiment(_experiment())
    analysis = {"max_flame_length_mm": 123.4, "level": "弱爆炸性"}
    assert database.update_experiment_analysis_results("exp-1", analysis)

    loaded = database.get_experiment("exp-1")

    assert loaded is not None
    assert loaded.experiment_id == "exp-1"
    assert loaded.experiment_type == "explosion"
    assert loaded.operator == "op"
    assert json.loads(loaded.analysis_results_json) == analysis

    all_experiments = database.get_all_experiments()
    assert [e.experiment_id for e in all_experiments] == ["exp-1"]
    assert json.loads(all_experiments[0].analysis_results_json) == analysis


def test_experiment_without_analysis_has_none(database):
    assert database.create_experiment(_experiment("exp-2"))

    loaded = database.get_experiment("exp-2")

    assert loaded.analysis_results_json is None
    assert database.get_experiment("missing") is None
