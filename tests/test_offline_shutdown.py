"""No equipment must not trap exit; previous device contact must still require STOP."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
import yaml
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse

from controllers.explosion_controller import ExplosionController
from controllers.ignition_controller import IgnitionController


READS = ('read_holding_registers', 'read_input_registers', 'read_coils')
WRITES = ('write_register', 'write_registers', 'write_coil')


@pytest.fixture(params=['explosion', 'ignition'])
def offline_controller(request, qapp, monkeypatch):
    config = yaml.safe_load((Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml').read_text(encoding='utf-8'))
    config = config[request.param + '_experiment']
    config['polling']['enabled'] = False
    client = create_autospec(ModbusSerialClient, instance=True)
    client.connect.return_value = True  # USB serial adapter exists, equipment does not.
    for name in READS + WRITES:
        getattr(client, name).side_effect = ModbusIOException('No device response')
    monkeypatch.setattr('modbus_multi_device.manager.ModbusSerialClient', lambda **kwargs: client)
    cls = ExplosionController if request.param == 'explosion' else IgnitionController
    controller = cls(config=config)
    yield controller, client
    controller.data_monitor_timer.stop()
    if controller.manager is not None:
        assert controller.manager.disconnect()
    if controller.db is not None:
        controller.db.close()


def test_never_connected_closes_without_hardware_access(offline_controller):
    controller, client = offline_controller
    assert controller.cleanup()
    assert controller.db is None
    client.connect.assert_not_called()


def test_serial_port_unavailable_does_not_trap_exit(offline_controller):
    controller, client = offline_controller
    client.connect.return_value = False
    controller._execute_connect()
    assert controller.cleanup()
    assert controller.db is None
    client.close.assert_called()


def test_open_adapter_with_no_device_response_closes_without_stop_writes(offline_controller):
    controller, client = offline_controller
    controller._execute_connect()
    assert controller.manager.connected and not controller.manager.ready
    assert not controller.is_running and controller.current_session_id is None
    assert controller.cleanup()
    assert controller.db is None and controller.manager is None
    client.close.assert_called()
    for name in WRITES:
        getattr(client, name).assert_not_called()


@pytest.mark.parametrize('contact', ['initialization_register', 'device_exception'])
def test_incomplete_reads_still_require_device_shutdown(offline_controller, contact):
    controller, client = offline_controller
    calls = []
    def read(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            if contact == 'device_exception':
                return ExceptionResponse(3, 2)
            return SimpleNamespace(registers=[0], isError=lambda: False)
        raise ModbusIOException('Device stopped responding')
    client.read_holding_registers.side_effect = read
    controller._execute_connect()
    assert controller.manager.connected and not controller.manager.ready
    assert not controller.manager.latest_data  # No complete sample does not imply no contact.
    assert not controller.cleanup()
    assert controller.db is not None and controller.manager is not None
    client.close.assert_not_called()


def test_response_history_survives_cache_clear_and_failed_reconnect(offline_controller):
    controller, client = offline_controller
    controller._execute_connect()
    controller.manager._on_data_received({'device': 'previously seen device', 'pv': 1})
    controller.manager._invalidate_data()
    controller._execute_connect()
    assert not controller.manager.ready and not controller.manager.latest_data
    assert not controller.cleanup()
    client.close.assert_not_called()


def test_timed_out_write_is_not_treated_as_never_controlled(offline_controller):
    controller, client = offline_controller
    controller._execute_connect()
    heater = next(device for name, device in controller.manager.devices.items() if '温控仪表' in name)
    assert not heater.write_control({'set_run_status': {'status': 'run'}})
    assert not controller.cleanup()
    client.close.assert_not_called()


def test_unknown_device_configuration_cannot_prove_a_complete_probe(offline_controller):
    controller, client = offline_controller
    controller.config['devices'][0]['type'] = 'not_a_device_driver'
    controller._execute_connect()
    assert not controller.cleanup()
    client.close.assert_not_called()


@pytest.mark.parametrize('offline_controller', ['explosion'], indirect=True)
def test_partial_relay_on_response_cannot_be_treated_as_no_equipment(offline_controller):
    controller, client = offline_controller
    calls = []
    def read(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            return SimpleNamespace(bits=[True], isError=lambda: False)
        raise ModbusIOException('Remaining coils unavailable')
    client.read_coils.side_effect = read
    controller._execute_connect()
    assert not controller.manager.ready and not controller.manager.latest_data
    assert not controller.cleanup()
    client.close.assert_not_called()
