"""Hardware-free contracts for serial I/O, fresh samples and safe shutdown."""
import importlib
import threading
import time
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from pymodbus.client import ModbusSerialClient

from modbus_multi_device.devices import (
    PressureSensorDevice, RelayControllerDevice, TemperatureSensorDevice,
    YudianControllerDevice,
)
from modbus_multi_device.manager import ModbusDeviceManager


def response(registers=None, bits=None, error=False):
    return SimpleNamespace(registers=registers or [1] * 8,
                           bits=bits or [False], isError=lambda: error)


@pytest.fixture
def serial_client():
    # autospec binds the REAL installed PyModbus signatures without opening a port.
    client = create_autospec(ModbusSerialClient, instance=True)
    for method in ("read_holding_registers", "read_input_registers", "read_coils",
                   "write_register", "write_registers", "write_coil"):
        getattr(client, method).return_value = response()
    return client


@pytest.mark.parametrize("driver", [PressureSensorDevice, RelayControllerDevice,
                                    TemperatureSensorDevice, YudianControllerDevice])
def test_device_reads_match_installed_pymodbus_signature(serial_client, driver):
    device = driver("test", 2, serial_client)
    assert device.read_data() is not None, device.last_error


@pytest.mark.parametrize("driver,command", [
    (PressureSensorDevice, {"set_alarm1": {"threshold": 10}}),
    (RelayControllerDevice, {"set_relay": {"relay": 1, "state": False}}),
    (YudianControllerDevice, {"set_run_status": {"status": "StoP"}}),
])
def test_device_writes_match_installed_pymodbus_signature(serial_client, driver, command):
    device = driver("test", 2, serial_client)
    assert device.write_control(command), device.last_error


def test_partial_relay_read_is_not_a_successful_all_off_snapshot(serial_client):
    serial_client.read_coils.side_effect = [response(), response(error=True),
                                           response(), response()]
    device = RelayControllerDevice("relay", 2, serial_client)
    assert device.read_data() is None


@pytest.fixture
def manager():
    obj = ModbusDeviceManager(config_dict={"logging": {"save_to_file": False},
                                          "polling": {"enabled": False}})
    yield obj
    obj.disconnect()


def test_cache_expires_and_failed_reads_invalidate_it(manager, monkeypatch):
    manager.started = manager.connected = True
    clock = [100.0]
    monkeypatch.setattr("modbus_multi_device.manager.time.monotonic", lambda: clock[0])
    manager._on_data_received({"device": "temperature", "pv": 250, "timestamp": time.time()})
    first = manager.get_latest_data("temperature")
    assert first and "sample_id" in first
    assert manager.get_latest_data("temperature")["sample_id"] == first["sample_id"]
    clock[0] += 4
    assert manager.get_latest_data("temperature") is None
    manager._on_data_received({"device": "temperature", "pv": 251, "timestamp": time.time()})
    assert manager.get_latest_data("temperature")["sample_id"] > first["sample_id"]
    manager._on_error_occurred("temperature", RuntimeError("disconnected"))
    assert manager.get_latest_data("temperature") is None


class RelayDevice:
    """In-memory coils with an optional blocked first write."""
    name = "爆炸性-继电器"
    enabled = True
    poll_interval = 1.0
    last_error = None

    def __init__(self):
        self.io_lock = threading.RLock()
        self.states = [False] * 4
        self.fail_relay = None
        self.fail_all_off = False
        self.write_started = threading.Event()
        self.release_write = threading.Event()
        self.block_first_write = False
        self.writes = []

    def write_control(self, data):
        self.writes.append(data)
        if self.block_first_write:
            self.block_first_write = False
            self.write_started.set()
            assert self.release_write.wait(2)
        if "set_all" in data:
            if self.fail_all_off:
                return False
            self.states = list(data["set_all"]["states"])
        else:
            relay = data["set_relay"]
            if relay["relay"] == self.fail_relay:
                return False
            self.states[relay["relay"] - 1] = relay["state"]
        return True

    def read_data(self):
        return {"device": self.name, "relays": {f"relay_{i + 1}": state
                for i, state in enumerate(self.states)}, "timestamp": time.time()}


def start_manager(manager, device):
    manager.connected = True
    manager.devices = {device.name: device}
    manager.device_list = [device]
    assert manager.start()


def test_control_wait_returns_execution_failure_not_enqueue_success(manager):
    device = RelayDevice()
    device.fail_relay = 1
    start_manager(manager, device)
    assert not manager.send_control_and_wait(device.name, {"set_relay": {"relay": 1, "state": True}})
    assert device.states == [False] * 4


def test_shutdown_cancels_queued_on_and_confirms_off_before_stop(manager):
    device = RelayDevice()
    device.block_first_write = True
    start_manager(manager, device)
    on = {"set_relay": {"relay": 1, "state": True}}
    assert manager.send_control(device.name, on)
    assert device.write_started.wait(1)
    assert manager.send_control(device.name, {"set_relay": {"relay": 2, "state": True}})
    result = []
    worker = threading.Thread(target=lambda: result.append(manager.shutdown_relays(device.name, timeout=2)))
    worker.start()
    # Wait for admission to close before releasing the in-flight ON.
    deadline = time.monotonic() + 1
    while manager.send_control(device.name, on) and time.monotonic() < deadline:
        threading.Event().wait(0.001)
    device.release_write.set()
    worker.join(3)
    assert not worker.is_alive()
    assert result == [True]
    assert device.states == [False] * 4
    assert not manager.send_control(device.name, on)
    assert not any(item.get("set_relay", {}).get("relay") == 2 for item in device.writes)
    manager.stop()
    assert device.states == [False] * 4


@pytest.fixture
def controller(tmp_path, monkeypatch, manager, qapp):
    # Configure paths before importing logger/controller modules; no user data.
    from utils.path_manager import PathManager
    monkeypatch.setattr(PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))
    module = importlib.import_module("controllers.explosion_controller")
    monkeypatch.setattr(module, "FlameKit", lambda **kw: None)
    obj = module.ExplosionController(config={"relay_mapping": {"first": 1, "second": 2},
                                            "relay_settle_delay_ms": 0})
    yield obj
    obj.cleanup()


def test_sequence_failure_turns_off_open_relays_and_allows_safety_stop(controller, manager):
    from models.experiment_states import ExplosionExperimentState as State
    device = RelayDevice()
    device.fail_relay = 2
    start_manager(manager, device)
    controller.manager = manager
    controller.current_session_id = 1
    controller.current_state = State.SEQUENCE_RUNNING
    controller.is_running = controller.sequence_running = True
    controller.config["sequence_steps"] = [
        {"step": 1, "name": "open", "action": "relay_on", "relay": "first"},
        {"step": 2, "name": "failure", "action": "relay_on", "relay": "second"},
    ]
    controller._execute_sequence()
    assert controller.current_state == State.ERROR
    assert device.states == [False] * 4
    assert controller.stop_experiment()


def test_cleanup_turns_off_manual_relays_even_without_running_experiment(controller, manager):
    device = RelayDevice()
    start_manager(manager, device)
    controller.manager = manager
    assert manager.send_control_and_wait(device.name, {"set_relay": {"relay": 1, "state": True}})
    controller.cleanup()
    assert device.states == [False] * 4
    assert not manager.started


def test_shutdown_readback_failure_is_reported(manager):
    device = RelayDevice()
    start_manager(manager, device)
    device.read_data = lambda: None
    assert not manager.shutdown_relays(device.name, timeout=1)


def session_with_round(controller):
    from models.experiment_states import ExplosionExperimentState as State
    session_id = controller.db.start_experiment_session(experiment_name="Safety test", sample_name="sample")
    controller.db.add_test_round(session_id, 1, 30.0)
    controller.current_session_id = session_id
    controller.current_exp_config = {"experiment_name": "Safety test"}
    controller.current_state = State.SESSION_CREATED
    return session_id


def test_finalize_commits_before_clearing_controller_session(controller):
    from models.experiment_states import ExplosionExperimentState as State
    session_id = session_with_round(controller)
    assert controller.finalize_experiment(session_id)
    assert controller.current_session_id is None
    assert controller.current_exp_config is None
    assert controller.current_state == State.COMPLETED
    assert controller.db.get_session_by_id(session_id)["status"] == "completed"


def test_finalize_failure_keeps_session_retryable(controller, monkeypatch):
    from models.experiment_states import ExplosionExperimentState as State
    session_id = session_with_round(controller)
    monkeypatch.setattr(controller.db, "finalize_experiment", lambda *a, **kw: False)
    assert not controller.finalize_experiment(session_id)
    assert controller.current_session_id == session_id
    assert controller.current_state == State.SESSION_CREATED


def test_prepare_shutdown_ends_session_but_keeps_resources_until_commit(controller):
    session_id = session_with_round(controller)
    database = controller.db
    assert controller.prepare_shutdown()
    assert controller.db is database
    session = database.get_session_by_id(session_id)
    assert session["status"] == "cancelled"
    assert session["end_time"]
    assert controller.current_session_id is None


def test_prepare_shutdown_failure_preserves_database_and_manager(controller, manager):
    device = RelayDevice()
    start_manager(manager, device)
    controller.manager = manager
    session_id = session_with_round(controller)
    device.fail_all_off = True
    assert not controller.prepare_shutdown()
    assert controller.manager is manager and manager.started
    assert controller.db.get_session_by_id(session_id)["status"] == "running"
    assert not controller.cleanup()
    device.fail_all_off = False
    assert controller.cleanup()


def test_stop_waits_for_sequence_and_old_on_cannot_follow_off(controller, manager):
    from models.experiment_states import ExplosionExperimentState as State
    device = RelayDevice()
    # The initial all-OFF preflight must finish. Block the first ON so the
    # original stop-vs-in-flight-control race remains the behavior under test.
    original_write = device.write_control
    block_next_on = [True]

    def write_with_blocked_on(command):
        if command.get('set_relay', {}).get('state') and block_next_on[0]:
            block_next_on[0] = False
            device.block_first_write = True
        return original_write(command)

    device.write_control = write_with_blocked_on
    start_manager(manager, device)
    manager._on_data_received({'device': '爆炸性-温控仪表', 'pv': 1100.0})
    manager._on_data_received({'device': '爆炸性-压力表', 'pressure': 50.0})
    controller.manager = manager
    controller.config['control_conditions'] = {
        'target_temperature': {'value': 1100.0, 'tolerance': 2.0},
        'target_pressure': {'value': 50.0, 'tolerance': 2.0},
    }
    session_with_round(controller)
    controller.config["sequence_steps"] = [
        {"step": 1, "name": "open", "action": "relay_on", "relay": "first"},
        {"step": 2, "name": "must not open", "action": "relay_on", "relay": "second"},
    ]
    assert controller.start_experiment()
    assert device.write_started.wait(1)
    result = []
    worker = threading.Thread(target=lambda: result.append(controller.stop_experiment()))
    worker.start()
    assert controller._stop_requested.wait(1)
    device.release_write.set()
    worker.join(3)
    assert result == [True]
    assert not controller._sequence_thread.is_alive()
    assert device.states == [False] * 4
    assert not any(item.get("set_relay", {}).get("relay") == 2 for item in device.writes)
    assert controller.current_state == State.SESSION_CREATED


def test_timed_out_shutdown_keeps_off_queued_and_blocks_resume(manager):
    device = RelayDevice()
    device.block_first_write = True
    start_manager(manager, device)
    assert manager.send_control(device.name, {"set_relay": {"relay": 1, "state": True}})
    assert device.write_started.wait(1)
    assert not manager.shutdown_relays(device.name, timeout=0.01)
    assert manager.started
    assert not manager.resume_controls(device.name)
    device.release_write.set()
    assert manager.shutdown_relays(device.name, timeout=1)
    assert device.states == [False] * 4
    assert manager.resume_controls(device.name)


def test_prepared_shutdown_cannot_accept_a_new_session(controller):
    from models.experiment_states import ExplosionExperimentState as State
    assert controller.prepare_shutdown()
    controller.current_state = State.CONNECTED
    assert not controller.create_experiment({"experiment_name": "late", "sample_name": "x", "description": ""})
    assert controller.current_session_id is None


def test_shutdown_exceptions_are_failures_not_unhandled_threads(controller, manager, monkeypatch):
    device = RelayDevice()
    start_manager(manager, device)
    controller.manager = manager
    original = manager.shutdown_relays
    monkeypatch.setattr(manager, "shutdown_relays", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("lost transport")))
    assert not controller.stop_experiment()
    monkeypatch.setattr(manager, "shutdown_relays", original)


def test_partial_device_connect_is_rejected(manager):
    good = RelayDevice()
    bad = RelayDevice()
    bad.name = "offline-required-device"
    bad.read_data = lambda: None
    manager.device_list = [good, bad]
    assert not manager._verify_devices()


def test_heater_stop_cancels_older_pending_run(manager):
    class Heater(RelayDevice):
        name = "着火点-温控仪表"

        def write_control(self, data):
            if not self.writes:
                self.write_started.set()
                assert self.release_write.wait(2)
            self.writes.append(data)
            self.status = data["set_run_status"]["status"]
            return True

    heater = Heater()
    start_manager(manager, heater)
    run = {"set_run_status": {"status": "run"}}
    stop = {"set_run_status": {"status": "StoP"}}
    assert manager.send_control(heater.name, run)
    assert heater.write_started.wait(1)
    assert manager.send_control(heater.name, run)
    assert not manager.shutdown_control(heater.name, stop, timeout=0.01)
    assert not manager.send_control(heater.name, run)
    heater.release_write.set()
    assert manager.shutdown_control(heater.name, stop, timeout=1)
    assert heater.status == "StoP"
    assert heater.writes == [run, stop]


def test_missing_telemetry_never_emits_zero_pressure_or_all_off(controller, manager):
    controller.manager = manager
    pressures, relay_states, online = [], [], []
    controller.pressure_updated.connect(pressures.append)
    controller.relay_status_updated.connect(relay_states.append)
    controller.device_status_changed.connect(lambda name, value: online.append((name, value)))
    controller._poll_device_data()
    assert not pressures
    assert not relay_states
    assert dict(online) == {"温控器": False, "压力表": False, "继电器": False}


def test_exit_during_connection_still_confirms_existing_relays_off(controller, manager, monkeypatch):
    device = RelayDevice()
    device.states[0] = True  # Hardware may already be ON when the port opens.
    manager.devices = {device.name: device}
    manager.device_list = [device]
    connecting, finish_connection = threading.Event(), threading.Event()

    def connect():
        connecting.set()
        assert finish_connection.wait(2)
        manager.connected = True
        return True

    monkeypatch.setattr(manager, "connect", connect)
    module = importlib.import_module("controllers.explosion_controller")
    monkeypatch.setattr(module, "ModbusDeviceManager", lambda **kw: manager)
    assert controller.connect_devices()
    assert connecting.wait(1)
    prepared = []
    exiting = threading.Thread(target=lambda: prepared.append(controller.prepare_shutdown()))
    exiting.start()
    assert controller._stop_requested.wait(1)
    finish_connection.set()
    exiting.join(3)
    assert prepared == [True]
    assert device.states == [False] * 4
    assert manager.connected  # Actual disconnection belongs to the commit phase.


def partial_connection(manager, monkeypatch):
    relay = RelayDevice()
    relay.states[0] = True

    class Heater(RelayDevice):
        name = "爆炸性-温控仪表"
        online = False

        def read_data(self):
            return {"device": self.name, "pv": 250} if self.online else None

        def write_control(self, data):
            return self.online

    heater = Heater()

    class Client:
        closed = False

        def connect(self):
            return True

        def close(self):
            self.closed = True

    client = Client()
    monkeypatch.setattr("modbus_multi_device.manager.ModbusSerialClient", lambda **kw: client)
    manager.devices = {device.name: device for device in (relay, heater)}
    manager.device_list = [relay, heater]
    monkeypatch.setattr(manager, "_init_devices", lambda: None)
    return relay, heater, client


def test_partial_connection_retains_transport_to_turn_off_and_retry(controller, manager, monkeypatch):
    relay, heater, client = partial_connection(manager, monkeypatch)
    module = importlib.import_module("controllers.explosion_controller")
    monkeypatch.setattr(module, "ModbusDeviceManager", lambda **kw: manager)
    controller._execute_connect()
    assert not controller.prepare_shutdown()  # Offline heater cannot acknowledge STOP.
    assert relay.states == [False] * 4
    assert not client.closed and manager.connected
    assert not manager.ready
    heater.online = True
    assert controller.prepare_shutdown()
    assert not client.closed
    assert controller.cleanup()
    assert client.closed


def test_reconnecting_partial_devices_reuses_live_manager(controller, manager, monkeypatch):
    relay, heater, client = partial_connection(manager, monkeypatch)
    factories = []

    def factory(**kw):
        factories.append(True)
        return manager

    module = importlib.import_module("controllers.explosion_controller")
    monkeypatch.setattr(module, "ModbusDeviceManager", factory)
    controller._execute_connect()
    heater.online = True
    controller._execute_connect()
    assert len(factories) == 1
    assert manager.ready and manager.started
    assert not client.closed


def test_start_cannot_replace_executor_whose_stop_timed_out(manager, monkeypatch):
    device = RelayDevice()
    device.block_first_write = True
    closed = []
    manager.client = SimpleNamespace(close=lambda: closed.append(True))
    start_manager(manager, device)
    assert manager.send_control(device.name, {"set_relay": {"relay": 1, "state": True}})
    assert device.write_started.wait(1)
    previous = manager.executor
    stop = previous.stop
    monkeypatch.setattr(previous, "stop", lambda: stop(timeout=0.01))
    try:
        assert not manager.stop()
        assert not manager.start()
        assert manager.executor is previous
        assert not manager.disconnect()
        assert not closed
    finally:
        device.release_write.set()
        previous.executor_thread.join(1)
    assert manager.disconnect()
    assert closed
