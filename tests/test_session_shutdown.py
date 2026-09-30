"""Regression coverage for acquisition identity and durable session completion."""
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from controllers.ignition_controller import IgnitionController
from models.experiment_states import ExplosionExperimentState, IgnitionExperimentState
from utils.path_manager import PathManager


@pytest.fixture
def session_controller(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(PathManager, "get_data_path", lambda name=None: str(tmp_path / name) if name else str(tmp_path))
    controller = IgnitionController()
    controller.current_state = IgnitionExperimentState.CONNECTED
    assert controller.create_experiment({
        "experiment_id": "IGN-audit", "experiment_name": "shutdown test",
        "sample_names": ["sample"] * 6, "client": "", "operator": "", "description": "",
    })
    controller.current_state = IgnitionExperimentState.RUNNING
    controller.is_running = True
    session_id = controller.current_session_id
    controller.db.update_session(session_id, status="running")
    yield controller, session_id, tmp_path / "ignition_experiment.db"
    if controller.db is not None:
        controller.db.close()
    controller.data_monitor_timer.stop()


def samples(controller, pv=300.0, temperature=250.0, sample_id=1):
    controller.manager = SimpleNamespace(get_latest_data=lambda name: {
        "着火点-温控仪表": {"pv": pv, "sample_id": sample_id},
        "着火点-温度模块": {"channels": [{"temperature": temperature}] * 6, "sample_id": sample_id},
    }.get(name))


def test_same_source_sample_is_not_written_twice(session_controller):
    controller, session_id, _ = session_controller
    samples(controller)
    assert controller.collect_data()
    assert not controller.collect_data()
    assert controller.is_running
    rows = controller.db.conn.execute("SELECT COUNT(*) FROM ignition_realtime_data WHERE session_id=?", (session_id,)).fetchone()[0]
    assert rows == 1
    samples(controller, sample_id=2)
    assert controller.collect_data()


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "invalid"])
def test_invalid_temperature_stops_acquisition_without_synthetic_values(session_controller, value):
    controller, _, _ = session_controller
    samples(controller, temperature=value)
    assert not controller.collect_data()
    assert not controller.is_running
    assert controller.current_state == IgnitionExperimentState.ERROR
    assert controller.db.conn.execute("SELECT COUNT(*) FROM ignition_realtime_data").fetchone()[0] == 0


def test_unavailable_device_stops_collection(session_controller):
    controller, _, _ = session_controller
    controller.manager = SimpleNamespace(get_latest_data=lambda name: None)
    assert not controller.collect_data()
    assert not controller.is_running


def test_shutdown_ends_active_session_without_claiming_completion(session_controller):
    controller, session_id, path = session_controller
    assert controller.prepare_shutdown()
    assert controller.db is not None  # final cleanup has not closed resources yet
    with sqlite3.connect(path) as db:
        status, end = db.execute("SELECT status,end_time FROM experiment_sessions WHERE id=?", (session_id,)).fetchone()
    assert status == "cancelled"
    assert end is not None
    assert controller.current_session_id is None
    assert controller.cleanup()


def test_failed_finalization_preserves_session_for_retry(session_controller, monkeypatch):
    controller, session_id, _ = session_controller
    controller.stop_experiment()
    monkeypatch.setattr(controller.db, "end_experiment_session", lambda *args, **kwargs: False)
    assert not controller.finalize_experiment()
    assert controller.current_session_id == session_id
    assert controller.current_state == IgnitionExperimentState.STOPPED


def test_successful_finalization_clears_session_after_database_write(session_controller):
    controller, session_id, path = session_controller
    controller.stop_experiment()
    assert controller.finalize_experiment()
    assert controller.current_state == IgnitionExperimentState.COMPLETED
    assert controller.current_session_id is None
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status FROM experiment_sessions WHERE id=?", (session_id,)).fetchone()[0] == "completed"


def test_shutdown_failure_keeps_resources_open_for_retry(session_controller, monkeypatch):
    controller, session_id, _ = session_controller
    monkeypatch.setattr(controller.db, "end_experiment_session", lambda *args, **kwargs: False)
    assert not controller.cleanup()
    assert controller.db is not None
    assert controller.current_session_id == session_id


def test_shutdown_confirms_heater_stop_before_disconnect(session_controller):
    controller, _, _ = session_controller
    manager = Mock(started=True)
    manager.shutdown_control.return_value = False
    controller.manager = manager
    assert not controller.prepare_shutdown()
    manager.stop.assert_not_called()
    assert controller.current_session_id is not None


def test_between_round_completion_matches_state_contract():
    state = ExplosionExperimentState.SESSION_CREATED
    assert state.can_finalize()
    assert state.can_transition_to(ExplosionExperimentState.COMPLETED)


def test_window_prepares_all_devices_before_closing_any_resource():
    from views.main_window import MainWindow
    calls = []
    pages = [SimpleNamespace(
        prepare_shutdown=lambda i=i: calls.append(("prepare", i)) or (i != 0),
        cleanup=lambda i=i: calls.append(("cleanup", i)) or True,
    ) for i in range(2)]
    window = SimpleNamespace(logger=Mock(), stacked_widget=SimpleNamespace(
        count=lambda: len(pages), widget=lambda i: pages[i],
    ))
    assert MainWindow._on_stop_all_experiments(window) is False
    assert calls == [("prepare", 0), ("prepare", 1)]


def test_close_during_connection_keeps_executor_available_for_heater_stop(session_controller, monkeypatch):
    controller, _, _ = session_controller
    controller.reset_session()
    controller.current_state = IgnitionExperimentState.IDLE
    manager = Mock(started=False)
    def connect():
        controller._closing = True
        return True
    manager.connect.side_effect = connect
    manager.start.side_effect = lambda: setattr(manager, "started", True)
    manager.shutdown_control.return_value = True
    monkeypatch.setattr("controllers.ignition_controller.ModbusDeviceManager", lambda **kwargs: manager)
    controller._execute_connect()
    manager.disconnect.assert_not_called()
    assert controller.prepare_shutdown()
    manager.shutdown_control.assert_called_once()


def test_normal_heater_commands_match_real_manager_signature(session_controller):
    from unittest.mock import create_autospec
    from modbus_multi_device import ModbusDeviceManager
    controller, _, _ = session_controller
    manager = create_autospec(ModbusDeviceManager, instance=True)
    manager.started = True
    manager.send_control_and_wait.return_value = True
    controller.manager = manager
    assert controller.control_temperature_controller("run")
    assert controller.set_temperature_program([[100, 1], [200, 2]])
    assert manager.send_control_and_wait.call_count == 2


def test_error_session_can_end_and_create_next_without_claiming_success(session_controller):
    controller, session_id, path = session_controller
    config = controller.current_experiment_config.copy()
    controller._fail_acquisition("sensor offline")
    assert controller.current_state.can_finalize()
    assert controller.finalize_experiment()
    assert controller.current_session_id is None
    assert controller.current_state == IgnitionExperimentState.CANCELLED
    with sqlite3.connect(path) as db:
        status, end = db.execute("SELECT status,end_time FROM experiment_sessions WHERE id=?", (session_id,)).fetchone()
    assert status == "error" and end
    assert controller.current_state.can_create_experiment()
    assert controller.create_experiment(config)
    assert controller.current_state == IgnitionExperimentState.PREPARED


def test_partially_connected_heater_gets_stop_before_resource_close(session_controller):
    controller, _, _ = session_controller
    manager = Mock(started=False, connected=True)
    manager.start.side_effect = lambda: setattr(manager, "started", True) or True
    manager.shutdown_control.return_value = False
    controller.manager = manager
    assert not controller.cleanup()
    manager.start.assert_called_once()
    manager.shutdown_control.assert_called_once()
    manager.disconnect.assert_not_called()
    assert controller.db is not None


def test_connection_retry_keeps_existing_open_manager(session_controller, monkeypatch):
    controller, _, _ = session_controller
    controller.reset_session()
    controller.current_state = IgnitionExperimentState.IDLE
    manager = Mock(started=False, connected=True, ready=False)
    manager.connect.return_value = False
    controller.manager = manager
    constructor = Mock()
    monkeypatch.setattr("controllers.ignition_controller.ModbusDeviceManager", constructor)
    controller._execute_connect()
    constructor.assert_not_called()
    manager.connect.assert_called_once()


def test_finalization_retains_session_until_heater_stop_confirmed(session_controller):
    controller, session_id, _ = session_controller
    controller.stop_experiment()
    manager = Mock(started=True)
    manager.shutdown_control.return_value = False
    controller.manager = manager
    assert not controller.finalize_experiment()
    assert controller.current_session_id == session_id
    assert controller.current_state == IgnitionExperimentState.STOPPED


def test_disconnect_failure_is_reported_without_discarding_resources(session_controller):
    controller, _, _ = session_controller
    manager = Mock(started=True)
    manager.shutdown_control.return_value = True
    manager.disconnect.return_value = False
    controller.manager = manager
    assert not controller.cleanup()
    assert controller.manager is manager
    assert controller.db is not None
