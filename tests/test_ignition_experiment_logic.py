#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pytest coverage for ignition experiment controller logic."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def ignition_database(tmp_path):
    module = pytest.importorskip("models.ignition_database")
    db = module.IgnitionDatabase(str(tmp_path / "ignition_logic.db"))
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def ignition_state():
    module = pytest.importorskip("models.experiment_states")
    return module.IgnitionExperimentState


@pytest.fixture
def controller(ignition_database, tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    # 控制器构造时会按 PathManager 的项目根目录创建默认数据库，重定向到临时目录，避免写入仓库的 data/
    path_module = pytest.importorskip("utils.path_manager")
    monkeypatch.setattr(path_module.PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))
    controller_module = pytest.importorskip("controllers.ignition_controller")
    controller = controller_module.IgnitionController(
        config={
            "collect_start_temperature": 200.0,
            "collect_end_temperature": 500.0,
        }
    )
    controller.db.close()
    controller.db = ignition_database
    return controller


@pytest.fixture
def experiment_config():
    return {
        "experiment_id": "IGN-20260410-120000",
        "experiment_name": "测试实验",
        "sample_names": [f"样品{i}" for i in range(1, 7)],
        "client": "测试单位",
        "operator": "测试员",
        "description": "pytest ignition logic",
    }


def test_state_transitions_follow_rules(controller, ignition_state):
    assert controller.current_state == ignition_state.IDLE

    controller._set_state(ignition_state.CONNECTED)
    assert controller.current_state == ignition_state.CONNECTED

    controller._set_state(ignition_state.PREPARED)
    assert controller.current_state == ignition_state.PREPARED

    controller._set_state(ignition_state.RUNNING)
    assert controller.current_state == ignition_state.RUNNING

    controller._set_state(ignition_state.STOPPED)
    assert controller.current_state == ignition_state.STOPPED

    controller._set_state(ignition_state.COMPLETED)
    assert controller.current_state == ignition_state.COMPLETED

    controller._set_state(ignition_state.CONNECTED)
    assert controller.current_state == ignition_state.CONNECTED

    controller._set_state(ignition_state.RUNNING)
    assert controller.current_state == ignition_state.CONNECTED


def test_create_experiment_and_reset_session(controller, ignition_state, experiment_config):
    controller._set_state(ignition_state.CONNECTED)

    assert controller.create_experiment(experiment_config) is True
    assert controller.current_session_id is not None
    assert controller.current_state == ignition_state.PREPARED

    sessions = controller.db.get_all_experiment_sessions()
    session = next(item for item in sessions if item["id"] == controller.current_session_id)
    assert json.loads(session["sample_names"]) == experiment_config["sample_names"]
    assert session["status"] == "prepared"

    controller.reset_session()
    assert controller.current_session_id is None
    assert controller.current_experiment_config is None
    assert controller.is_running is False
    assert controller.ignited_samples == [False] * 6


def test_collect_data_respects_temperature_gates(controller, ignition_state, experiment_config):
    controller._set_state(ignition_state.CONNECTED)
    assert controller.create_experiment(experiment_config) is True
    assert controller.start_experiment() is False

    controller.manager = MagicMock()
    controller.is_running = True
    controller.current_state = ignition_state.RUNNING
    controller.start_experiment = MagicMock(return_value=True)

    controller.manager.get_latest_data.side_effect = lambda device_name: {
        "着火点-温控仪表": {"pv": 150.0},
        "着火点-温度模块": {
            "channels": [{"temperature": 100.0} for _ in range(6)]
        },
    }.get(device_name)
    assert controller.collect_data() is False

    controller.manager.get_latest_data.side_effect = lambda device_name: {
        "着火点-温控仪表": {"pv": 300.0},
        "着火点-温度模块": {
            "channels": [{"temperature": 250.0 + index} for index in range(6)]
        },
    }.get(device_name)
    assert controller.collect_data() is True

    controller.manager.get_latest_data.side_effect = lambda device_name: {
        "着火点-温控仪表": {"pv": 510.0},
        "着火点-温度模块": {
            "channels": [{"temperature": 500.0} for _ in range(6)]
        },
    }.get(device_name)
    assert controller.collect_data() is False
    assert controller.is_running is False
    assert controller.current_state == ignition_state.STOPPED


def test_collect_end_temperature_defaults_to_500_when_missing(ignition_database, ignition_state, experiment_config, tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    path_module = pytest.importorskip("utils.path_manager")
    monkeypatch.setattr(path_module.PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))
    controller_module = pytest.importorskip("controllers.ignition_controller")
    controller = controller_module.IgnitionController(config={"collect_start_temperature": 200.0})
    controller.db.close()
    controller.db = ignition_database
    controller._set_state(ignition_state.CONNECTED)

    assert controller.create_experiment(experiment_config) is True
    controller.manager = MagicMock()
    controller.is_running = True
    controller.current_state = ignition_state.RUNNING
    controller.manager.get_latest_data.side_effect = lambda device_name: {
        "着火点-温控仪表": {"pv": 510.0},
        "着火点-温度模块": {
            "channels": [{"temperature": 500.0} for _ in range(6)]
        },
    }.get(device_name)

    assert controller.collect_data() is False
    assert controller.is_running is False
    assert controller.current_state == ignition_state.STOPPED


def test_database_operations_store_session_and_runtime_data(ignition_database):
    session_id = ignition_database.start_experiment_session(
        experiment_id="IGN-20260410-0001",
        experiment_name="数据库测试",
        sample_names=json.dumps([f"样品{i}" for i in range(1, 7)]),
        client="测试单位",
        operator="测试员",
        description="验证数据库写入",
    )

    assert session_id > 0

    sessions = ignition_database.get_all_experiment_sessions()
    session = next(item for item in sessions if item["id"] == session_id)
    assert session["status"] == "prepared"

    record_id = ignition_database.insert_ignition_data(
        pv=300.0,
        ch1=250.0,
        ch2=251.0,
        ch3=252.0,
        ch4=253.0,
        ch5=254.0,
        ch6=255.0,
        session_id=session_id,
    )
    assert record_id > 0

    assert ignition_database.end_experiment_session(session_id, status="completed") is True
    sessions = ignition_database.get_all_experiment_sessions()
    session = next(item for item in sessions if item["id"] == session_id)
    assert session["status"] == "completed"


def test_ignition_state_helpers_match_expected_behavior(ignition_state):
    assert ignition_state.PREPARED.can_start() is True
    assert ignition_state.STOPPED.can_start() is False
    assert ignition_state.RUNNING.can_stop() is True
    assert ignition_state.PREPARED.can_stop() is False
    assert ignition_state.CONNECTED.can_create_experiment() is True
    assert ignition_state.COMPLETED.can_create_experiment() is True
    assert ignition_state.STOPPED.can_create_experiment() is False
    assert ignition_state.STOPPED.can_finalize() is True
    assert ignition_state.RUNNING.can_finalize() is True
