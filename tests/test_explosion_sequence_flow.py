"""Explosion sequence admission and manual cleaning, using in-memory hardware."""
import copy
import threading

import pytest

from modbus_multi_device.manager import ModbusDeviceManager
from models.experiment_states import ExplosionExperimentState as State


class MemoryRelay:
    name = '爆炸性-继电器'
    enabled = True
    poll_interval = 1.0
    last_error = None

    def __init__(self):
        self.io_lock = threading.RLock()
        self.states = [False] * 4
        self.writes = []
        self.fail_all_off = False
        self.fail_on = None
        self.after_write = lambda: None

    def write_control(self, command):
        self.writes.append((copy.deepcopy(command), self.states[:]))
        if 'set_all' in command:
            if self.fail_all_off:
                return False
            self.states = list(command['set_all']['states'])
        else:
            relay = command['set_relay']
            if relay['state'] and relay['relay'] == self.fail_on:
                return False
            self.states[relay['relay'] - 1] = relay['state']
        self.after_write()
        return True

    def read_data(self):
        return {'device': self.name,
                'relays': {f'relay_{i + 1}': state for i, state in enumerate(self.states)}}


@pytest.fixture
def rig(monkeypatch, qapp):
    import controllers.explosion_controller as module
    monkeypatch.setattr(module, 'FlameKit', lambda **kwargs: None)
    controller = module.ExplosionController({
        'relay_mapping': {'spray_valve': 1, 'purge_valve': 2, 'vacuum_cleaner': 3},
        'test-rounds': {'max-rounds': 10},
        'control_conditions': {'target_temperature': {'value': 1100.0, 'tolerance': 2.0},
                               'target_pressure': {'value': 50.0, 'tolerance': 2.0}},
        'sequence_steps': [
            {'step': 1, 'name': 'spray on', 'action': 'relay_on', 'relay': 'spray_valve'},
            {'step': 2, 'name': 'spray off', 'action': 'relay_off', 'relay': 'spray_valve'},
        ],
    })
    manager = ModbusDeviceManager(config_dict={'logging': {'save_to_file': False},
                                              'polling': {'enabled': False}})
    relay = MemoryRelay()
    manager.devices = {relay.name: relay}
    manager.device_list = [relay]
    manager.connected = manager.ready = True
    assert manager.start()
    manager._on_data_received({'device': '爆炸性-温控仪表', 'pv': 1100.0})
    manager._on_data_received({'device': '爆炸性-压力表', 'pressure': 50.0})
    controller.manager = manager
    controller._set_state(State.CONNECTED)
    assert controller.create_experiment({'experiment_name': 'sequence test',
                                         'sample_name': 'virtual', 'description': ''})
    yield controller, manager, relay
    relay.fail_all_off = False
    relay.after_write = lambda: None
    controller.cleanup()


def wait_sequence(controller):
    controller._sequence_thread.join(2)
    assert not controller._sequence_thread.is_alive()


def test_start_establishes_confirmed_all_off_before_spray(rig):
    controller, _, relay = rig
    relay.states = [True, True, True, False]
    assert controller.start_experiment() is True
    wait_sequence(controller)
    assert relay.writes[0][0] == {'set_all': {'states': [False] * 4}}
    spray_write = next(item for item in relay.writes if 'set_relay' in item[0])
    assert spray_write[1] == [False] * 4


@pytest.mark.parametrize('bad_reading', [None, 1000.0, float('nan')])
def test_start_requires_valid_current_temperature_without_counting_attempt(rig, bad_reading):
    controller, manager, relay = rig
    manager._on_error_occurred('爆炸性-温控仪表', RuntimeError('offline'))
    if bad_reading is not None:
        manager._on_data_received({'device': '爆炸性-温控仪表', 'pv': bad_reading})
    started = controller.start_experiment()
    if started:
        wait_sequence(controller)
    assert not started
    assert controller.current_round_number == 0
    assert not any(command.get('set_relay', {}).get('state') for command, _ in relay.writes)


def test_start_rechecks_conditions_after_off_barrier(rig):
    controller, manager, relay = rig
    relay.after_write = lambda: manager._on_error_occurred('爆炸性-压力表', RuntimeError('offline'))
    started = controller.start_experiment()
    if started:
        wait_sequence(controller)
    assert not started
    assert controller.current_round_number == 0
    assert all('set_all' in command for command, _ in relay.writes)


def test_failed_off_preflight_cannot_spray_or_advance_round(rig):
    controller, _, relay = rig
    relay.fail_all_off = True
    started = controller.start_experiment()
    if started:
        wait_sequence(controller)
    assert not started
    assert controller.current_round_number == 0
    assert controller.current_state == State.ERROR
    assert all('set_all' in command for command, _ in relay.writes)


def test_unsaved_attempt_retries_same_round_then_uses_persisted_number(rig):
    controller, _, _ = rig
    controller.config['sequence_steps'] = [
        {'step': 1, 'name': 'delay', 'action': 'delay', 'duration': 1.0}]
    assert controller.start_experiment()
    assert controller.current_round_number == 1
    assert controller.stop_experiment()
    assert controller.start_experiment()
    assert controller.current_round_number == 1
    assert controller.stop_experiment()
    session = controller.current_session_id
    assert controller.add_test_round(session, 1, 10.0) > 0
    controller.current_round_number = 50  # An attempt counter must not override stored rounds.
    assert controller.start_experiment()
    assert controller.current_round_number == 2
    assert controller.stop_experiment()


@pytest.mark.parametrize('after_round', [False, True])
def test_manual_clean_can_resume_after_confirmed_stop_or_normal_round(rig, after_round):
    controller, _, relay = rig
    if after_round:
        assert controller.start_experiment()
        wait_sequence(controller)
    else:
        assert controller.stop_experiment()
    assert controller.set_auto_clean(True)
    assert relay.states == [True, True, True, False]
    assert controller.set_auto_clean(False)
    assert relay.states == [False] * 4


def test_partial_manual_clean_failure_turns_every_output_off(rig):
    controller, _, relay = rig
    relay.fail_on = 2
    assert not controller.set_auto_clean(True)
    assert relay.states == [False] * 4
    assert not any(command.get('set_relay', {}).get('relay') == 3 for command, _ in relay.writes)
    assert relay.writes[-1][0] == {'set_all': {'states': [False] * 4}}


def test_manual_clean_rejects_active_sequence_and_closing(rig):
    controller, _, relay = rig
    controller.config['sequence_steps'] = [
        {'step': 1, 'name': 'delay', 'action': 'delay', 'duration': 1.0}]
    assert controller.start_experiment()
    before = len(relay.writes)
    assert not controller.set_auto_clean(True)
    assert len(relay.writes) == before
    assert controller.stop_experiment()
    controller._closing = True
    assert not controller.set_auto_clean(True)
    assert relay.states == [False] * 4


def test_stop_during_start_preflight_cannot_be_cleared_by_start(rig):
    controller, _, relay = rig
    relay.after_write = controller._stop_requested.set
    started = controller.start_experiment()
    if started:
        wait_sequence(controller)
    assert not started
    assert controller.current_round_number == 0
    assert all('set_all' in command for command, _ in relay.writes)


def test_spray_waits_for_first_frame_before_opening_valve(rig):
    controller, _, relay = rig
    checking, first_frame = threading.Event(), threading.Event()
    phases = []

    def guard(phase):
        phases.append(phase)
        if phase == 'before_spray':
            checking.set()
            return first_frame.wait(1)
        return True

    controller.camera_round_guard = guard
    assert controller.start_experiment() is True
    try:
        assert checking.wait(1)
        assert all('set_all' in command for command, _ in relay.writes)
    finally:
        first_frame.set()
    wait_sequence(controller)
    assert phases == ['before_spray', 'after_spray']
    assert controller.current_state == State.WAITING_ANALYSIS


def test_missing_first_frame_aborts_without_spraying(rig):
    from PySide6.QtCore import Qt
    controller, _, relay = rig
    completed = []
    controller.sequence_completed.connect(lambda: completed.append(True), Qt.DirectConnection)
    first_frame = threading.Event()
    controller.camera_round_guard = lambda phase: first_frame.wait(.01)
    assert controller.start_experiment() is True
    wait_sequence(controller)
    assert controller.current_state == State.ERROR
    assert completed == []
    assert all('set_all' in command for command, _ in relay.writes)
    assert relay.states == [False] * 4


def test_camera_window_ending_during_slow_on_ack_aborts_and_closes_valve(rig):
    from PySide6.QtCore import Qt
    controller, _, relay = rig
    completed, phases = [], []
    controller.sequence_completed.connect(lambda: completed.append(True), Qt.DirectConnection)
    first_frame, acquisition_done = threading.Event(), threading.Event()
    first_frame.set()

    def guard(phase):
        phases.append(phase)
        return first_frame.is_set() and not acquisition_done.is_set()

    original_write = relay.write_control

    def delayed_ack(command):
        if command.get('set_relay', {}).get('state'):
            # Simulate the one-second capture ending while the serial ON is
            # in flight; acknowledgement arrives after the capture window.
            acquisition_done.set()
        return original_write(command)

    relay.write_control = delayed_ack
    controller.camera_round_guard = guard
    assert controller.start_experiment() is True
    wait_sequence(controller)
    assert phases == ['before_spray', 'after_spray']
    assert controller.current_state == State.ERROR
    assert completed == []
    assert any(command.get('set_relay', {}).get('state') for command, _ in relay.writes)
    assert relay.writes[-1][0] == {'set_all': {'states': [False] * 4}}
    assert relay.states == [False] * 4


@pytest.mark.parametrize('failed_phase', ['before_spray', 'after_spray'])
def test_camera_guard_exception_never_emits_sequence_success(rig, failed_phase):
    from PySide6.QtCore import Qt
    controller, _, relay = rig
    completed = []
    controller.sequence_completed.connect(lambda: completed.append(True), Qt.DirectConnection)

    def guard(phase):
        if phase == failed_phase:
            raise RuntimeError('Camera event unavailable')
        return True

    controller.camera_round_guard = guard
    assert controller.start_experiment() is True
    wait_sequence(controller)
    assert controller.current_state == State.ERROR
    assert completed == []
    assert relay.states == [False] * 4
    assert relay.writes[-1][0] == {'set_all': {'states': [False] * 4}}
    has_on = any(command.get('set_relay', {}).get('state') for command, _ in relay.writes)
    assert has_on is (failed_phase == 'after_spray')


@pytest.mark.parametrize('failed_phase', [None, 'before_spray', 'after_spray'])
def test_grouped_spray_uses_the_same_capture_guard(rig, failed_phase):
    from PySide6.QtCore import Qt
    controller, _, relay = rig
    controller.config['sequence_steps'] = [{
        'step': 1, 'name': 'grouped spray', 'action': 'relay_multi_on',
        'relays': ['purge_valve', 'spray_valve', 'vacuum_cleaner'],
    }]
    phases, signals, completed = [], [], []
    controller.spray_valve_opened.connect(lambda: signals.append(True), Qt.DirectConnection)
    controller.sequence_completed.connect(lambda: completed.append(True), Qt.DirectConnection)

    def guard(phase):
        phases.append(phase)
        if phase == 'before_spray':
            assert relay.states[0] is False
        else:
            assert relay.states[0] is True
        return phase != failed_phase

    controller.camera_round_guard = guard
    assert controller.start_experiment() is True
    wait_sequence(controller)
    assert signals == [True]
    assert phases == (['before_spray'] if failed_phase == 'before_spray'
                      else ['before_spray', 'after_spray'])
    opened = [command['set_relay']['relay'] for command, _ in relay.writes
              if command.get('set_relay', {}).get('state')]
    if failed_phase:
        assert controller.current_state == State.ERROR
        assert completed == []
        assert 3 not in opened
        assert (1 in opened) is (failed_phase == 'after_spray')
    else:
        assert controller.current_state == State.WAITING_ANALYSIS
        assert completed == [True]
        assert opened == [2, 1, 3]
    assert relay.states == [False] * 4
