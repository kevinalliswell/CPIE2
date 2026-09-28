"""Regression coverage for runtime fixes retained from the parallel reviews."""
from collections import deque
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services.ignition.ignition_detection_service import IgnitionDetectionService


def detect_through_page(times, temperatures, criteria):
    from views.pages.ignition_page import IgnitionExperimentPage

    config = {'ignition_detection': {
        'enabled': True, 'check_interval': 0.2, 'criteria': criteria}}
    detector = IgnitionDetectionService(config)
    detector.last_check_time = 0
    found = []
    page = SimpleNamespace(
        config=config, ignition_detector=detector, data_collector=None,
        temp_history={0: deque(temperatures)}, time_history=deque(times),
        ignition_detected_flags=[False],
        _mark_ignition=lambda *result: found.append(result),
    )
    IgnitionExperimentPage._check_ignition(page)
    return found


@pytest.mark.parametrize('times', [
    [0, .5, 1, 1.5, 2, 2.5],
    [0, 1, 2, 4, 7, 10],
])
def test_rise_rate_uses_observed_sample_times_not_detection_frequency(times):
    assert detect_through_page(times, [200, 200.5, 201, 201.5, 202, 202.5], {
        'rise_rate': {'enabled': True, 'threshold': 2.0},
    }) == []


def test_rise_rate_accepts_true_threshold_crossing():
    assert detect_through_page([0, .5, 1, 1.5, 2, 2.5],
                               [200, 201, 202, 203, 204, 205], {
        'rise_rate': {'enabled': True, 'threshold': 2.0},
    }) == [(0, 205, '温升速率')]


def test_temperature_rise_uses_the_full_actual_time_window():
    times = [i * .5 for i in range(21)]
    assert detect_through_page(times, [200 + t for t in times], {
        'temperature_rise': {'enabled': True, 'threshold': 10, 'time_window': 10},
    }) == [(0, 210, '温度突升')]


def test_temperature_rise_does_not_include_samples_outside_the_window():
    times = list(range(0, 20, 2))
    assert detect_through_page(times, [200 + t for t in times], {
        'temperature_rise': {'enabled': True, 'threshold': 12, 'time_window': 10},
    }) == []


def test_temperature_rise_waits_until_the_time_window_is_observed():
    assert detect_through_page([i * .5 for i in range(10)],
                               [200 + i * 2 for i in range(10)], {
        'temperature_rise': {'enabled': True, 'threshold': 10, 'time_window': 10},
    }) == []


@pytest.mark.parametrize('times', [
    [], [0, 1], [0, 1, 2, 2, 4, 5], [0, 1, 2, 1, 4, 5],
    [0, 1, 2, float('nan'), 4, 5], [0, 1, 2, 3, 4, float('inf')],
])
def test_missing_or_invalid_sample_times_cannot_assert_a_rise_rate(times):
    assert detect_through_page(times, [200, 205, 210, 215, 220, 225], {
        'rise_rate': {'enabled': True, 'threshold': 2.0},
    }) == []


def test_absolute_temperature_does_not_require_elapsed_time():
    assert detect_through_page([], [200, 205, 210, 215, 220, 225], {
        'absolute_temperature': {'enabled': True, 'threshold': 220},
    }) == [(0, 225, '绝对温度')]


@pytest.mark.parametrize('existing_origin', [None, 40.0])
def test_start_uses_one_monotonic_origin_for_the_whole_session(monkeypatch, existing_origin):
    import views.pages.ignition_page as module

    monkeypatch.setattr(module.time, 'monotonic', lambda: 100.0)
    page = SimpleNamespace(
        controller=SimpleNamespace(current_session_id=1, start_experiment=lambda: True),
        _check_temperature_condition=lambda: True, start_time=existing_origin,
        data_collector=None, update_timer=SimpleNamespace(isActive=lambda: True),
    )
    module.IgnitionExperimentPage._on_start(page)
    assert page.start_time == (100.0 if existing_origin is None else existing_origin)


def test_plot_sample_times_ignore_wall_clock_adjustment(qapp, monkeypatch):
    import yaml
    from pathlib import Path
    import views.pages.ignition_page as module
    from utils.path_manager import PathManager

    config = yaml.safe_load(Path(PathManager.get_config_path('experiment_config.yaml')).read_text(encoding='utf-8'))
    page = module.IgnitionExperimentPage(config['ignition_experiment'], config['ui'])
    data = {'channels': [{'temperature': 200.0}] * 6, 'sample_id': 1}
    page.manager = SimpleNamespace(get_latest_data=lambda name: data)
    page.controller.is_running = True
    page.start_time = 10.0
    try:
        with monkeypatch.context() as clock:
            samples = iter([10.0, 11.0])
            clock.setattr(module.time, 'monotonic', lambda: next(samples))
            clock.setattr(module.time, 'time', lambda: -1000000.0)
            assert page._update_temperature_data()
            data['sample_id'] = 2
            assert page._update_temperature_data()
        assert list(page.time_history) == [0.0, 1.0]
    finally:
        page.controller.is_running = False
        page.manager = None
        assert page.cleanup()
        page.close()
        page.deleteLater()


def test_manager_start_failure_does_not_report_connected_or_discard_transport(qapp):
    from controllers.ignition_controller import IgnitionController
    from models.experiment_states import IgnitionExperimentState

    controller = IgnitionController({})
    manager = Mock(connected=True, started=False)
    manager.connect.return_value = True
    manager.start.return_value = False
    controller.manager = manager
    results = []
    controller.device_connected.connect(lambda *result: results.append(result))
    try:
        controller._execute_connect()
        qapp.processEvents()
        assert results and not any(success for success, _ in results)
        assert controller.current_state == IgnitionExperimentState.IDLE
        assert not controller.data_monitor_timer.isActive()
        assert controller.manager is manager
        manager.disconnect.assert_not_called()
    finally:
        controller.data_monitor_timer.stop()
        controller.db.close()
        controller.db = None
        controller.manager = None
        controller.deleteLater()


@pytest.mark.parametrize('kind', ['ignition', 'explosion'])
@pytest.mark.parametrize('connected', [False, True])
def test_controller_status_reports_transport_connection(kind, connected):
    from controllers.ignition_controller import IgnitionController
    from controllers.explosion_controller import ExplosionController

    controller = SimpleNamespace(
        is_running=False, sequence_running=False, current_session_id=None,
        current_experiment_config=None, current_exp_config=None, current_round_number=0,
        manager=SimpleNamespace(connected=connected, started=False))
    cls = IgnitionController if kind == 'ignition' else ExplosionController
    assert cls.get_experiment_status(controller)['device_connected'] is connected
