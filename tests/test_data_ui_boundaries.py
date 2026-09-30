"""Input and configuration boundaries shared by offline experiment tools."""
import math
from datetime import datetime

import pytest


def test_legacy_services_import_and_require_experiment_inputs():
    from services.experiment_file import ExperimentFile
    from services.experiment_data import ReductionExperimentData, RDIExperimentData, SwellingExperimentData
    common = dict(experiment_id='x', experiment_name='x', sample_name='x', start_time=datetime.now(), operator='x')
    for cls, values in [
        (ReductionExperimentData, dict(initial_sample_weight_g=1.0, oxygen_content_percentage=20)),
        (RDIExperimentData, dict(initial_sample_mass_g=1.0)),
        (SwellingExperimentData, dict(number_of_pellets_tested=6)),
    ]:
        with pytest.raises(TypeError):
            cls(**common)
        model = cls(**common, **values)
        assert all(getattr(model, key) == value for key, value in values.items())
        assert model.raw_data_log == []
    assert ExperimentFile


def test_editing_mode_does_not_mutate_preset_and_rejects_invalid_values(qapp):
    from views.dialogs.mode_switch_dialog import ModeSwitchDialog
    dialog = ModeSwitchDialog()
    try:
        preset = {'name': 'Known', 'segments': [[100.0, 10], [200.0, 20]]}
        dialog._on_preset_selected(True, preset)
        item = dialog.segments_table.item(0, 1)
        item.setText('150')
        assert preset['segments'][0][0] == 100
        assert dialog.current_segments[0][0] == 150
        for value in ('invalid', 'nan', 'inf'):
            item.setText(value)
            assert math.isfinite(dialog.current_segments[0][0])
            assert item.text() == '150.0'
        time_item = dialog.segments_table.item(0, 2)
        for value in ('inf', '2.5'):
            time_item.setText(value)
            assert dialog.current_segments[0][1] == 10
            assert time_item.text() == '10'
    finally:
        dialog.close()


def test_history_password_change_persists_and_controls_confirmation(qapp, monkeypatch):
    from types import SimpleNamespace
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    from views.pages.history_query_page import HistoryQueryPage
    from utils.password_manager import PasswordManager
    from utils.logger import get_logger
    answers = iter([('1952', True), ('new-secret', True), ('new-secret', True)])
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args: next(answers))
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)
    errors = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: errors.append(args[-1]))
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: errors.append(args[-1]))
    HistoryQueryPage.change_password(SimpleNamespace(logger=get_logger(__name__)))
    assert errors == []
    manager = PasswordManager()
    assert manager.verify_password('new-secret')
    assert not manager.verify_password('1952')
