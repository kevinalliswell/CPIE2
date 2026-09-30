"""A closed calibration dialog must relinquish camera reads without releasing it."""
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from views.dialogs.calibration_dialog import CalibrationDialog


@pytest.fixture
def calibration(qapp, monkeypatch):
    camera = SimpleNamespace(capture_single_frame=Mock(
        side_effect=lambda: np.zeros((5, 5, 3), dtype=np.uint8)))
    kit = SimpleNamespace(camera=camera, initialize=Mock(return_value=True), release=Mock())
    parent = QWidget()
    dialog = CalibrationDialog(kit, parent)
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: QMessageBox.Ok)
    dialog.show()
    yield dialog, kit
    if dialog.preview_timer is not None:
        dialog.preview_timer.stop()
    dialog.close()
    parent.deleteLater()
    qapp.processEvents()


@pytest.mark.parametrize('finish', ['accept', 'reject', 'close', 'done', 'complete'])
def test_every_calibration_exit_stops_preview_reads(calibration, finish):
    dialog, kit = calibration
    values = []
    dialog.calibration_completed.connect(values.append)
    dialog.points = [(0, 0), (10, 0)]
    dialog.length_input.setText('1')
    dialog.complete_btn.setEnabled(True)
    dialog._toggle_preview()
    QTest.qWait(70)
    assert kit.camera.capture_single_frame.call_count > 0

    if finish == 'done':
        dialog.done(QDialog.Accepted)
    elif finish == 'complete':
        dialog._complete_calibration()
        assert values == [0.1]
    else:
        getattr(dialog, finish)()

    assert not dialog.isVisible()
    assert not dialog.preview_timer.isActive()
    calls_after_exit = kit.camera.capture_single_frame.call_count
    QTest.qWait(100)
    assert kit.camera.capture_single_frame.call_count == calls_after_exit
    kit.release.assert_not_called()


@pytest.mark.parametrize('length', ['nan', 'inf', '-inf', '1e309', '0', '-1', '5e-324'])
def test_calibration_rejects_nonfinite_or_nonpositive_scale(calibration, monkeypatch, length):
    dialog, kit = calibration
    warning = Mock(return_value=QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, 'warning', warning)
    values = []
    dialog.calibration_completed.connect(values.append)
    dialog.points = [(0, 0), (10, 0)]
    dialog.length_input.setText(length)

    dialog._complete_calibration()

    assert values == []
    assert dialog.isVisible()
    assert dialog.result() != QDialog.Accepted
    warning.assert_called_once()
    kit.release.assert_not_called()
