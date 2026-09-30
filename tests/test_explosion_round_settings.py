"""Round settings must fit database capacity without rewriting legacy values."""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def make_settings(qapp, monkeypatch):
    from views.pages.config_page import ConfigPage
    from utils.path_manager import PathManager
    from PySide6.QtWidgets import QMessageBox

    config_path = Path(PathManager.get_config_path('experiment_config.yaml'))
    baseline = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    messages = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda parent, title, text: messages.append(text))
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)
    pages = []

    def make(maximum=2, phase=1):
        config = deepcopy(baseline)
        config['explosion_experiment']['test-rounds'].update({'max-rounds': maximum, 'phase-rounds': phase})
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding='utf-8')
        page = ConfigPage(config, config['ui'], config_path=str(config_path))
        pages.append(page)
        return page, config_path, messages

    yield make
    for page in pages:
        page.close()
        page.deleteLater()


def test_valid_round_controls_follow_database_limit_and_each_other(make_settings):
    page, path, messages = make_settings()
    maximum = page.config_widgets['test_max_rounds']
    phase = page.config_widgets['test_phase_rounds']
    assert maximum.maximum() == 10
    assert (maximum.value(), phase.value(), phase.maximum()) == (2, 1, 2)
    maximum.setValue(6)
    phase.setValue(5)
    maximum.setValue(3)
    assert (maximum.value(), phase.value(), phase.maximum()) == (3, 3, 3)
    page._on_save()
    saved = yaml.safe_load(path.read_text(encoding='utf-8'))['explosion_experiment']['test-rounds']
    assert (saved['max-rounds'], saved['phase-rounds']) == (3, 3)
    assert messages == []


@pytest.mark.parametrize('maximum,phase', [(12, 5), (2, 5), (0, 1)])
def test_legacy_invalid_rounds_remain_visible_and_cannot_be_saved_or_applied(make_settings, maximum, phase):
    page, path, messages = make_settings(maximum, phase)
    before = path.read_bytes()
    original = deepcopy(page.config)
    updates = []
    page.config_updated.connect(lambda config: updates.append(config))
    assert page.config_widgets['test_max_rounds'].value() == maximum
    assert page.config_widgets['test_phase_rounds'].value() == phase
    page._on_save()
    page._on_apply()
    assert path.read_bytes() == before
    assert page.config == original
    assert updates == []
    assert len(messages) == 2 and all('轮次' in message for message in messages)


def test_explicit_correction_releases_legacy_round_limit(make_settings):
    page, path, messages = make_settings(12, 5)
    maximum = page.config_widgets['test_max_rounds']
    phase = page.config_widgets['test_phase_rounds']
    maximum.setValue(10)
    assert maximum.maximum() == 10
    assert phase.maximum() == 10
    page._on_save()
    saved = yaml.safe_load(path.read_text(encoding='utf-8'))['explosion_experiment']['test-rounds']
    assert (saved['max-rounds'], saved['phase-rounds']) == (10, 5)
    assert messages == []


def test_reloading_config_does_not_clamp_legacy_rounds(make_settings):
    page, path, messages = make_settings()
    page.config['explosion_experiment']['test-rounds'].update({'max-rounds': 12, 'phase-rounds': 11})
    page._update_widgets_from_config()
    assert page.config_widgets['test_max_rounds'].value() == 12
    assert page.config_widgets['test_phase_rounds'].value() == 11
    page._on_apply()
    assert messages and '轮次' in messages[0]
