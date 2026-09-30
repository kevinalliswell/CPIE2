"""Exercise page-level experiment completion with the real controller and SQLite."""
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace
import threading
import time

import pytest
import yaml
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QCoreApplication, QEvent

from models.experiment_states import ExplosionExperimentState as State


@pytest.fixture
def explosion_page(qapp, monkeypatch):
    from views.pages.explosion_page import ExplosionExperimentPage
    config = yaml.safe_load((Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml').read_text())
    page = ExplosionExperimentPage(config['explosion_experiment'], config['ui'])
    for method in ('warning', 'critical', 'information', 'question'):
        monkeypatch.setattr(QMessageBox, method, lambda *a, **k: QMessageBox.Yes)
    page.controller.current_state = State.CONNECTED
    assert page.controller.create_experiment({'experiment_name': 'flow', 'sample_name': 'coal', 'description': ''})
    qapp.processEvents()
    page.controller.current_state = State.WAITING_ANALYSIS
    page.controller.current_round_number = 1
    yield page
    page.camera_flow.worker.cancel()
    assert page.camera_flow.worker.wait(2)
    page.controller.manager = None
    page.update_timer.stop()
    page.controller.data_monitor_timer.stop()
    page.controller.db.close()
    page.close()
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


def add_round(page):
    session = page.current_session_id
    assert page.controller.db.add_test_round(session, 1, 30.0, '') > 0
    page.round_records = [{'round': 1, 'flame_length': 30.0, 'image_path': ''}]
    return session


def test_conclusion_commits_before_clearing_page_and_controller(explosion_page):
    page = explosion_page
    session = add_round(page)
    page._show_experiment_conclusion()
    assert page.controller.db.get_session_by_id(session)['status'] == 'completed'
    assert page.controller.db.get_session_result(session) is not None
    assert page.current_session_id is None and page.controller.current_session_id is None
    assert page.controller.current_state == State.COMPLETED


def test_failed_conclusion_preserves_both_sessions_and_rounds(explosion_page, monkeypatch):
    page = explosion_page
    session = add_round(page)
    monkeypatch.setattr(page.controller.db, 'finalize_experiment', lambda *a, **k: False)
    page._show_experiment_conclusion()
    assert page.current_session_id == page.controller.current_session_id == session
    assert len(page.round_records) == 1
    assert page.controller.current_state == State.WAITING_ANALYSIS
    assert page.controller.db.get_session_by_id(session)['status'] == 'running'


def test_analysis_callback_does_not_reclose_its_sender(explosion_page):
    page = explosion_page
    window = Mock()
    window.isVisible.return_value = True
    page.flame_analyzer_window = window
    page._on_flame_analysis_complete({})
    window.close.assert_not_called()


def test_cleaning_failure_is_not_reported_as_success(explosion_page):
    page = explosion_page
    page.controller.manager = Mock()
    page.controller.set_auto_clean = Mock(return_value=False)
    page.controller.control_relay = Mock(return_value=False)
    messages = []
    page.log_message.connect(messages.append)
    page._on_auto_clean_on()
    assert not any('✓ 自清洁已开启' in message for message in messages)


def pump(qapp, predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(.001)
    assert predicate()


def arm(page):
    page.controller.current_state = State.SESSION_CREATED
    page.camera_enabled = True
    assert page.camera_flow.prepare_round(page.current_session_id, 1)
    page.controller.current_state = State.SEQUENCE_RUNNING
    return page.camera_flow.context


def test_retry_confirmation_uses_persisted_round_number(explosion_page, monkeypatch):
    page = explosion_page
    page.controller.current_state = State.SESSION_CREATED
    page.controller.current_round_number = 1  # Cancelled attempt was not saved.
    page.camera_enabled = True
    monkeypatch.setattr(page, '_check_experiment_conditions', lambda: True)
    prompts = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: prompts.append(args[2]) or QMessageBox.No)
    page._on_start_experiment()
    assert len(prompts) == 1 and '当前轮次: 第 1 轮' in prompts[0]
    assert page.camera_flow.context is None


def saved_image(page):
    image = Path(page.max_flame_save_dir) / 'accepted.jpg'
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b'synthetic retained image')
    return str(image)


@pytest.mark.parametrize('window', ['covered', 'no_first_frame', 'ended_during_ack'])
def test_real_spray_connection_observes_camera_stage_events(explosion_page, monkeypatch, window):
    """Exercise the direct Qt connection, worker events and controller gate together."""
    page = explosion_page
    finish = threading.Event()
    on_calls, outcomes = [], []
    def capture(directory, **kwargs):
        if window == 'no_first_frame':
            kwargs['acquisition_done_event'].set()
            raise RuntimeError('SDK did not produce a valid frame')
        kwargs['ready_event'].set()
        assert finish.wait(2)
        assert kwargs['required_after_event'].is_set() is (window == 'covered')
        kwargs['acquisition_done_event'].set()
        file = Path(directory) / 'frame.jpg'
        file.write_bytes(b'synthetic')
        return [str(file)], 1
    def relay_on(relay, value):
        assert page.camera_flow.worker.capture_ready.is_set()
        assert not page.camera_flow.worker.acquisition_done.is_set()
        on_calls.append((relay, value))
        if window == 'ended_during_ack':
            # Acquisition can end while encoding still keeps the worker busy.
            page.camera_flow.worker.acquisition_done.set()
        return True
    def spray():
        try:
            outcomes.append(page.controller._execute_relay_on('spray_valve'))
        except RuntimeError as error:
            outcomes.append(error)
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', capture)
    monkeypatch.setattr(page.controller, 'control_relay', relay_on)
    page.controller._control_timeout = .3
    arm(page)
    thread = threading.Thread(target=spray)
    try:
        thread.start()
        thread.join(1)
        assert not thread.is_alive(), 'camera gate must finish without pumping the GUI'
        assert len(outcomes) == 1
        assert on_calls == ([] if window == 'no_first_frame' else [('spray_valve', True)])
        if window == 'covered':
            assert outcomes == [True]
            assert page.camera_flow._spray_confirmed.is_set()
            with pytest.raises(RuntimeError, match='尚未开始有效采集'):
                page.controller._execute_relay_on('spray_valve')
            assert on_calls == [('spray_valve', True)]
        else:
            assert isinstance(outcomes[0], RuntimeError)
            assert not page.camera_flow._spray_confirmed.is_set()
    finally:
        finish.set()
        thread.join(2)
        assert page.camera_flow.worker.wait(2)
        page.camera_flow.cancel_round()


def test_analysis_waits_for_both_capture_and_sequence_then_commits(explosion_page, qapp, monkeypatch):
    page = explosion_page
    release = threading.Event()
    def capture(directory, **kwargs):
        assert release.wait(2)
        file = Path(directory) / 'frame.jpg'
        file.write_bytes(b'synthetic')
        return [str(file)], 1
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', capture)
    opened = Mock()
    monkeypatch.setattr(page, '_analyze_flame', opened)
    context = arm(page)
    session = page.current_session_id
    page.camera_flow.trigger()
    page.controller.current_state = State.WAITING_ANALYSIS
    page._on_controller_sequence_completed()
    opened.assert_not_called()
    release.set()
    pump(qapp, lambda: opened.call_count == 1)
    result = page.camera_flow.result
    assert result['count'] == 1
    window = SimpleNamespace(output_folder=None)
    page._accept_flame_analysis({
        'max_flame_size': 30.0, 'min_flame_size': 30.0, 'average_flame_size': 30.0,
        'total_images': 1, 'failed_images': 0, 'max_flame_saved_path': saved_image(page),
    }, context, window)
    assert page.controller.db.get_session_by_id(session)['status'] == 'completed'
    assert len(page.controller.db.get_session_test_rounds(session)) == 1
    assert page.camera_flow.context is None
    assert page.controller.current_session_id is None


def test_stopped_attempt_cannot_trigger_or_supply_next_round_images(explosion_page, qapp, monkeypatch):
    page = explosion_page
    old = arm(page)
    page.camera_flow.cancel_round()
    page.controller.current_state = State.SESSION_CREATED
    capture = Mock()
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', capture)
    page.camera_flow.trigger()
    assert not page.camera_flow.busy
    capture.assert_not_called()
    assert page.camera_flow.prepare_round(page.current_session_id, 1)
    assert page.camera_flow.context != old
    page._accept_flame_analysis({'max_flame_size': 999}, old, SimpleNamespace(output_folder=None))
    assert page.controller.db.get_session_test_rounds(page.current_session_id) == []


def test_capture_failure_stops_sequence_without_opening_analysis(explosion_page, qapp, monkeypatch):
    page = explosion_page
    opened = Mock()
    monkeypatch.setattr(page, '_analyze_flame', opened)
    def fail(*args, **kwargs):
        raise RuntimeError('disk full')
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', fail)
    arm(page)
    page.camera_flow.trigger()
    pump(qapp, lambda: page.camera_flow.context is None)
    assert page.controller.current_state == State.SESSION_CREATED
    assert not page.controller.sequence_running
    opened.assert_not_called()
    assert page.controller.db.get_session_test_rounds(page.current_session_id) == []


def test_save_failure_keeps_capture_for_retry_and_rejects_duplicate_callback(explosion_page, monkeypatch):
    page = explosion_page
    context = arm(page)
    page.controller.current_state = State.WAITING_ANALYSIS
    root = page.camera_flow.root / 'owned-attempt'
    root.mkdir(parents=True)
    raw = root / 'frame.jpg'
    raw.write_bytes(b'synthetic')
    page.temp_dir = str(root)
    page.camera_flow.result = {'directory': str(root), 'paths': [str(raw)], 'count': 1}
    page.camera_flow.sequence_complete = True
    result = {'max_flame_size': 30.0, 'min_flame_size': 30.0, 'average_flame_size': 30.0,
              'total_images': 1, 'failed_images': 0, 'max_flame_saved_path': saved_image(page)}
    window = SimpleNamespace(output_folder=None)
    original = page.controller.db.add_test_round
    monkeypatch.setattr(page.controller.db, 'add_test_round', lambda *a, **k: -1)
    page._accept_flame_analysis(result, context, window)
    assert page.camera_flow.context == context
    assert page.round_records == [] and raw.exists()
    monkeypatch.setattr(page.controller.db, 'add_test_round', original)
    session = page.current_session_id
    page._accept_flame_analysis(result, context, window)
    page._accept_flame_analysis(result, context, window)
    assert len(page.controller.db.get_session_test_rounds(session)) == 1


def test_shutdown_retains_camera_until_worker_exits(explosion_page, qapp, monkeypatch):
    page = explosion_page
    entered, finish = threading.Event(), threading.Event()
    def capture(directory, **kwargs):
        entered.set()
        assert finish.wait(2)
        raise RuntimeError('cancelled')
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', capture)
    release = Mock(return_value=True)
    monkeypatch.setattr(page.flame_kit, 'release', release)
    arm(page)
    page.camera_flow.trigger()
    assert entered.wait(1)
    assert not page.cleanup()
    release.assert_not_called()
    finish.set()
    assert page.camera_flow.worker.wait(2)
    assert page.camera_flow.prepare_shutdown()
    # Controller resources remain open until the real page cleanup is retried.
    assert page.controller.db is not None


def test_cancelled_worker_restores_controls_after_actual_exit(explosion_page, qapp, monkeypatch):
    page = explosion_page
    finish = threading.Event()
    def capture(directory, **kwargs):
        assert finish.wait(2)
        raise RuntimeError('cancelled')
    monkeypatch.setattr(page.flame_kit.camera, 'capture_sequence', capture)
    arm(page)
    page.camera_flow.trigger()
    page.camera_flow.cancel_round()
    page.controller.current_state = State.SESSION_CREATED
    page.camera_flow.refresh_controls()
    assert not page.btn_start.isEnabled()
    finish.set()
    pump(qapp, lambda: page.btn_start.isEnabled())
    assert page.camera_panel.btn_init_camera.isEnabled()


def test_committed_attempt_cleanup_preserves_other_failed_attempts(explosion_page):
    page = explosion_page
    raw = page.camera_flow.root / 'current'
    raw.mkdir(parents=True)
    (raw / 'frame.jpg').write_bytes(b'current')
    outputs = page.flame_config.flame_output_folder
    old = outputs / 'failed_attempt'
    old.mkdir(parents=True)
    evidence = old / 'evidence.png'
    evidence.write_bytes(b'previous failure')
    current_output = outputs / 'current_output'
    current_output.mkdir()
    page.temp_dir = str(raw)
    page._analysis_output_dir = str(current_output)
    page._cleanup_temp_folders()
    assert evidence.read_bytes() == b'previous failure'
    assert not current_output.exists() and not raw.exists()


@pytest.mark.parametrize('maximum,phase', [(2, 5), (12, 5), (0, 1)])
def test_invalid_old_round_config_keeps_settings_reachable(qapp, isolated_runtime, monkeypatch, maximum, phase):
    from views.main_window import MainWindow
    for method in ('question', 'warning', 'critical', 'information'):
        monkeypatch.setattr(QMessageBox, method, lambda *a, **k: QMessageBox.Yes)
    config_file = isolated_runtime / 'configs/experiment_config.yaml'
    config = yaml.safe_load(config_file.read_text())
    config['explosion_experiment']['test-rounds'].update({'max-rounds': maximum, 'phase-rounds': phase})
    config_file.write_text(yaml.safe_dump(config, allow_unicode=True))
    window = MainWindow()
    try:
        page = window.stacked_widget.widget(1)
        assert page._configuration_error
        assert not page.btn_start.isEnabled()
        assert window.stacked_widget.count() == 7
        assert type(window.stacked_widget.widget(4)).__name__ == 'ConfigPage'
        assert yaml.safe_load(config_file.read_text())['explosion_experiment']['test-rounds']['max-rounds'] == maximum
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()
