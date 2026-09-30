"""Real Qt result display uses the chosen configuration and numeric results."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel

from views.dialogs.tangent_analysis_dialog import TangentAnalysisDialog


@pytest.fixture
def make_dialog(qapp):
    dialogs = []
    time = np.arange(0, 1200, 1)
    temperature = 200.0 + time / 12.0 + 150.0 * (1.0 - np.exp(-np.maximum(time - 400.0, 0) ** 2 / 200.0))
    records = [dict(elapsed_seconds=int(t), **{f"sample{channel}_temperature": float(temp)
               for channel in range(1, 7)}) for t, temp in zip(time, temperature)]

    def create(config, bad_sample=None, bad_time=None, count=None):
        data = [dict(record) for record in records]
        if bad_sample is not None:
            data[100]["sample1_temperature"] = bad_sample
        if bad_time is not None:
            data[100]["elapsed_seconds"] = bad_time
        if count is not None:
            data = data[:count]
        database = SimpleNamespace(get_session_temperature_data=lambda session_id: data)
        dialog = TangentAnalysisDialog(1, database, config)
        dialogs.append(dialog)
        return dialog

    yield create
    for dialog in dialogs:
        dialog.close()
        dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


@pytest.mark.parametrize("full_root", [True, False])
def test_dialog_applies_tangent_config_from_root_or_experiment(make_dialog, full_root):
    config = {"ignition_detection": {"tangent_method": {"min_temp_rise": 10000.0}}}
    if full_root:
        config = {"ignition_experiment": config}
    dialog = make_dialog(config)
    assert dialog.analysis_results == {}


def test_dialog_displays_actual_fit_correlations(make_dialog):
    dialog = make_dialog({})
    assert dialog.analysis_results
    result = dialog.analysis_results[0]
    text = dialog.sample_widgets[0].findChild(QLabel, "result_label_0").text()
    assert f"(R={result['r1']:.3f})" in text
    assert f"(R={result['r2']:.3f})" in text
    json.dumps(dialog.analysis_results, allow_nan=False)


@pytest.mark.parametrize("bad_sample", ["invalid", np.nan, np.inf])
def test_invalid_sample_does_not_prevent_other_channels_from_analysis(make_dialog, bad_sample):
    dialog = make_dialog({}, bad_sample=bad_sample)
    assert 0 not in dialog.analysis_results
    assert set(dialog.analysis_results) == {1, 2, 3, 4, 5}
    text = dialog.sample_widgets[0].findChild(QLabel, "result_label_0").text()
    assert "分析中" not in text


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_manual_entry_rejects_nonfinite_result(make_dialog, monkeypatch, value):
    from views.dialogs import tangent_analysis_dialog as module
    dialog = make_dialog({"ignition_detection": {"tangent_method": {"min_temp_rise": 10000.0}}})
    monkeypatch.setattr(module.QInputDialog, "getDouble", lambda *args, **kwargs: (value, True))
    monkeypatch.setattr(module.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(module.QMessageBox, "critical", lambda *args, **kwargs: None)
    dialog._manual_input_temperature(0)
    assert dialog.analysis_results == {}


def test_manual_result_with_integer_timestamps_is_json_serializable(make_dialog, monkeypatch):
    from views.dialogs import tangent_analysis_dialog as module
    dialog = make_dialog({"ignition_detection": {"tangent_method": {"min_temp_rise": 10000.0}}})
    monkeypatch.setattr(module.QInputDialog, "getDouble", lambda *args, **kwargs: (250.0, True))
    dialog._manual_input_temperature(0)
    assert dialog.analysis_results[0]["method"] == "manual"
    json.dumps(dialog.analysis_results, allow_nan=False)


@pytest.mark.parametrize("bad_time", [np.nan, np.inf, 99.0, 98.0])
def test_dialog_rejects_invalid_time_axis_for_automatic_and_manual_results(make_dialog, monkeypatch, bad_time):
    from views.dialogs import tangent_analysis_dialog as module
    dialog = make_dialog({}, bad_time=bad_time)
    assert dialog.analysis_results == {}
    for channel in range(6):
        label = dialog.sample_widgets[channel].findChild(QLabel, f"result_label_{channel}")
        assert "无法分析" in label.text()
    monkeypatch.setattr(module.QInputDialog, "getDouble", lambda *args, **kwargs: (250.0, True))
    monkeypatch.setattr(module.QMessageBox, "warning", lambda *args, **kwargs: None)
    dialog._manual_input_temperature(0)
    assert dialog.analysis_results == {}


@pytest.mark.parametrize("count", [0, 10, 49])
def test_dialog_finishes_with_an_explicit_status_for_insufficient_data(make_dialog, count):
    dialog = make_dialog({}, count=count)
    assert dialog.analysis_results == {}
    for channel in range(6):
        label = dialog.sample_widgets[channel].findChild(QLabel, f"result_label_{channel}")
        assert "分析中" not in label.text()


def test_real_session_analysis_saves_plot_and_numeric_result(qapp, tmp_path):
    from datetime import datetime, timedelta
    from pathlib import Path
    from models.ignition_database import IgnitionDatabase

    database = IgnitionDatabase(str(tmp_path / "tangent.db"))
    dialog = None
    try:
        session_id = database.start_experiment_session(experiment_id="TANGENT-TEST")
        start = datetime(2026, 9, 29, 12)
        database.conn.execute("UPDATE experiment_sessions SET start_time = ? WHERE id = ?",
                              (start.isoformat(sep=" ", timespec="microseconds"), session_id))
        time = np.arange(0, 1200, 1)
        temperature = 200.0 + time / 12.0 + 150.0 * (1.0 - np.exp(-np.maximum(time - 400.0, 0) ** 2 / 3200.0))
        rows = [(session_id, (start + timedelta(seconds=int(t))).isoformat(sep=" ", timespec="microseconds"),
                 *([float(temp)] * 7)) for t, temp in zip(time, temperature)]
        database.conn.executemany(
            "INSERT INTO ignition_realtime_data (session_id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        database.conn.commit()
        dialog = TangentAnalysisDialog(session_id, database, {"ignition_experiment": {}})
        result = dialog.analysis_results[0]
        assert dialog._save_single_channel_data(0, result, str(tmp_path))
        saved = database.conn.execute(
            "SELECT ignition_temperature, detection_method, tangent_analysis_image_path FROM ignition_detection "
            "WHERE session_id = ? AND channel = 1", (session_id,)).fetchone()
        assert saved[0] == pytest.approx(result["ignition_temp"])
        assert saved[1] == "tangent"
        assert Path(saved[2]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        json.dumps(result, allow_nan=False)
    finally:
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()
        database.close()
