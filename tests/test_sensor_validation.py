from types import SimpleNamespace

import pytest

from services.explosion.experiment_validator import ExperimentValidator
from services.ignition.temperature_condition_validator import TemperatureConditionValidator


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "bad", True])
def test_ignition_start_rejects_invalid_temperature(value):
    manager = SimpleNamespace(get_latest_data=lambda name: {"pv": value})
    valid, message = TemperatureConditionValidator({}, manager).check_start_condition()
    assert not valid
    assert "数据" in message


@pytest.mark.parametrize("data", [{}, {"pressure": None}, {"pressure": float("nan")}, {"pressure": True}])
def test_explosion_start_requires_a_valid_pressure_sample(data):
    manager = SimpleNamespace(get_latest_data=lambda name: {"pv": 0.0} if name == "爆炸性-温控仪表" else data)
    valid, message = ExperimentValidator({}, manager).check_conditions()
    assert not valid
    assert "压力" in message


def test_primary_relay_display_clears_stale_state(qapp):
    from views.widgets.explosion.relay_panel import RelayPanelWidget
    panel = RelayPanelWidget({'relay_mapping': {'spray_valve': 1}})
    assert panel.relay_labels[1].text() == '未知'
    panel.update_all_relay_status({'relay_1': True})
    assert panel.relay_labels[1].text() == '导通'
    panel.update_all_relay_status({})
    assert panel.relay_labels[1].text() == '未知'
    panel.update_all_relay_status({'relay_1': 'invalid'})
    assert panel.relay_labels[1].text() == '未知'
    panel.close()


def test_primary_temperature_page_records_each_channel_once_and_clears_invalid(qapp):
    import time
    import yaml
    from pathlib import Path
    from views.pages.ignition_page import IgnitionExperimentPage
    from utils.path_manager import PathManager
    config = yaml.safe_load(Path(PathManager.get_config_path('experiment_config.yaml')).read_text(encoding='utf-8'))
    page = IgnitionExperimentPage(config['ignition_experiment'], config['ui'])
    data = {"channels": [{"temperature": 20.0 + i} for i in range(6)], "sample_id": 1}
    page.manager = SimpleNamespace(get_latest_data=lambda name: data)
    page.controller.is_running = True
    page.start_time = time.time()
    try:
        assert isinstance(page.temp_history, dict)
        assert page._update_temperature_data()
        assert not page._update_temperature_data()
        assert len(page.time_history) == 1
        assert [list(page.temp_history[i]) for i in range(6)] == [[20.0 + i] for i in range(6)]
        data['sample_id'] = 2
        data['channels'][0]['temperature'] = None
        assert not page._update_temperature_data()
        assert page.last_temperatures[0] is None
        assert len(page.time_history) == 1
    finally:
        page.controller.is_running = False
        page.manager = None
        assert page.cleanup()
        page.close()
        page.deleteLater()
