"""Slow capture must not block Qt, overlap SDK operations, or accept missing frames."""
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QTimer

from services.explosion.camera_capture import CameraCaptureWorker


def finish(qapp, worker, reports):
    deadline = time.monotonic() + 2
    while not reports and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(.001)
    assert worker.wait(1)
    qapp.processEvents()
    assert reports
    return reports[-1]


def test_slow_capture_keeps_qt_responsive_and_rejects_overlap(qapp, tmp_path):
    worker = CameraCaptureWorker()
    release = threading.Event()
    reports, ticks, threads = [], [], []
    worker.finished.connect(reports.append)
    def capture(directory, **kwargs):
        threads.append(threading.get_ident())
        assert kwargs['duration'] == .4
        assert kwargs['max_buffer_bytes'] == 64 * 1024 * 1024
        assert release.wait(2)
        file = Path(directory) / 'frame.jpg'
        file.write_bytes(b'frame')
        return [str(file)], 1
    kit = SimpleNamespace(camera=SimpleNamespace(capture_sequence=capture))
    assert worker.capture(kit, tmp_path / 'round1', .4, (1, 1), max_buffer_mb=64)
    assert not worker.capture(kit, tmp_path / 'overlap', .4, (1, 2))
    QTimer.singleShot(0, lambda: (ticks.append(True), release.set()))
    result = finish(qapp, worker, reports)
    assert ticks and threads == [worker._thread.ident]
    assert threads[0] != threading.get_ident()
    assert result['success'] and result['context'] == (1, 1)
    assert not (tmp_path / 'overlap').exists()


@pytest.mark.parametrize('outcome', ['zero', 'missing', 'mismatch', 'exception'])
def test_incomplete_capture_never_reports_success(qapp, tmp_path, outcome):
    worker = CameraCaptureWorker()
    reports = []
    worker.finished.connect(reports.append)
    def capture(directory, **kwargs):
        if outcome == 'exception':
            raise RuntimeError('SDK conversion failed')
        if outcome == 'zero':
            return [], 0
        return [str(Path(directory) / 'absent.jpg')], 2 if outcome == 'mismatch' else 1
    assert worker.capture(SimpleNamespace(camera=SimpleNamespace(capture_sequence=capture)), tmp_path / outcome, 1, outcome)
    assert not finish(qapp, worker, reports)['success']


def test_cancel_during_trigger_delay_never_calls_camera(qapp, tmp_path):
    worker = CameraCaptureWorker()
    reports, calls = [], []
    worker.finished.connect(reports.append)
    kit = SimpleNamespace(camera=SimpleNamespace(capture_sequence=lambda *a, **k: calls.append(True)))
    assert worker.capture(kit, tmp_path / 'cancel', 1, 'cancel', delay=10)
    worker.cancel()
    assert not finish(qapp, worker, reports)['success']
    assert calls == []
