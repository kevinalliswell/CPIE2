"""Secondary displays must not keep stale readings or imply unknown relays are off."""
from types import SimpleNamespace

import pytest


@pytest.fixture
def panels(qapp):
    from views.ui_components.monitor_panels.ignition_monitor_panel import IgnitionMonitorPanel
    from views.ui_components.monitor_panels.explosion_monitor_panel import ExplosionMonitorPanel

    readings = {
        "着火点-温控仪表": {"pv": 400},
        "着火点-温度模块": {"channels": [{"temperature": 420}] * 6},
        "爆炸性-温控仪表": {"pv": 1100},
        "爆炸性-压力表": {"pressure": 50},
        "爆炸性-继电器": {"relays": {f"relay_{i}": True for i in range(1, 5)}},
    }
    controller = SimpleNamespace(manager=SimpleNamespace(get_latest_data=readings.get))
    ignition, explosion = IgnitionMonitorPanel(), ExplosionMonitorPanel()
    for panel in (ignition, explosion):
        panel.controller = controller
        panel._update_display()
    yield ignition, explosion, controller, readings
    for panel in (ignition, explosion):
        panel.update_timer.stop()
        panel.close()
        panel.deleteLater()
    qapp.processEvents()


def assert_unknown(ignition, explosion):
    assert ignition.furnace_temp_card.value_label.text() == "--"
    assert [item.temp_label.text() for item in ignition.sample_items] == ["--"] * 6
    assert explosion.temp_card.value_label.text() == "--"
    assert explosion.pressure_card.value_label.text() == "--"
    assert [label.text() for label in explosion.relay_card.relay_labels.values()] == ["未知"] * 4


@pytest.mark.parametrize("payload", [None, {}])
def test_expired_data_clears_previously_valid_readings(panels, payload):
    ignition, explosion, _, readings = panels
    assert ignition.furnace_temp_card.value_label.text() == "400.0"
    assert explosion.pressure_card.value_label.text() == "50.0"
    for device in readings:
        readings[device] = payload
    ignition._update_display()
    explosion._update_display()
    assert_unknown(ignition, explosion)


@pytest.mark.parametrize("action", ["missing_manager", "disconnect", "reset"])
def test_disconnect_and_reset_remove_stale_readings(panels, action):
    ignition, explosion, controller, _ = panels
    if action == "missing_manager":
        controller.manager = None
    for panel in (ignition, explosion):
        if action == "disconnect":
            panel.disconnect_controller_signals(controller)
        elif action == "reset":
            panel.reset()
        else:
            panel._update_display()
    assert_unknown(ignition, explosion)


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), "bad", True])
def test_invalid_sensor_values_are_not_displayed_as_measurements(panels, invalid):
    ignition, explosion, _, readings = panels
    readings["着火点-温控仪表"] = {"pv": invalid}
    readings["爆炸性-温控仪表"] = {"pv": invalid}
    readings["爆炸性-压力表"] = {"pressure": invalid}
    readings["着火点-温度模块"] = {"channels": [{"temperature": invalid}] * 6}
    readings["爆炸性-继电器"] = {"relays": {"relay_1": None, "relay_2": "false"}}
    ignition._update_display()
    explosion._update_display()
    assert_unknown(ignition, explosion)


@pytest.mark.parametrize("channels", [None, [None], [None, {"temperature": 0}, {"temperature": -5}]])
def test_empty_or_partial_channels_clear_missing_samples(panels, channels):
    ignition, _, _, readings = panels
    readings["着火点-温度模块"] = {"channels": channels}
    ignition._update_display()
    expected = ["--", "0", "-5", "--", "--", "--"] if channels and len(channels) == 3 else ["--"] * 6
    assert [item.temp_label.text() for item in ignition.sample_items] == expected


def test_partial_relay_snapshot_distinguishes_off_from_unknown(panels):
    _, explosion, _, readings = panels
    readings["爆炸性-继电器"] = {"relays": {"relay_1": True, "relay_2": False}}
    explosion._update_display()
    assert [label.text() for label in explosion.relay_card.relay_labels.values()] == ["导通", "关闭", "未知", "未知"]
