"""Regression coverage for backups, deletion and historical experiment reports."""
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from models.explosion_database import ExplosionDatabase
from models.ignition_database import IgnitionDatabase
from utils.path_manager import PathManager


@pytest.fixture(params=[ExplosionDatabase, IgnitionDatabase])
def database(request, tmp_path):
    db = request.param(str(tmp_path / 'source.db'))
    yield db
    db.close()


def test_backup_preserves_committed_wal_data(database, tmp_path):
    database.conn.execute('PRAGMA journal_mode=WAL')
    database.conn.execute('PRAGMA wal_autocheckpoint=0')
    sid = database.start_experiment_session(experiment_name='WAL snapshot')
    target = tmp_path / 'backup.db'
    assert database.backup(str(target))
    with sqlite3.connect(target) as copy:
        assert copy.execute('SELECT experiment_name FROM experiment_sessions WHERE id=?', (sid,)).fetchone() == ('WAL snapshot',)
        assert copy.execute('PRAGMA integrity_check').fetchone() == ('ok',)


def test_failed_database_delete_preserves_image(database):
    sid = database.start_experiment_session(experiment_name='Keep original')
    if isinstance(database, ExplosionDatabase):
        image = PathManager.get_max_flame_images_path('original.png')
        database.add_test_round(sid, 1, 10.0, image)
    else:
        image = PathManager.get_data_path('original.png')
        database.record_ignition_detection(sid, 1, 300, image_path=image)
    from pathlib import Path
    Path(image).write_bytes(b'original measurement')
    database.conn.execute("CREATE TRIGGER prevent_delete BEFORE DELETE ON experiment_sessions BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
    database.conn.commit()
    assert database.delete_session(sid) is False
    assert Path(image).read_bytes() == b'original measurement'
    assert database.conn.execute('SELECT COUNT(*) FROM experiment_sessions WHERE id=?', (sid,)).fetchone()[0] == 1


@pytest.fixture
def ignition(tmp_path):
    db = IgnitionDatabase(str(tmp_path / 'ignition.db'))
    yield db
    db.close()


def test_new_samples_have_local_microsecond_timestamps(ignition):
    sid = ignition.start_experiment_session(experiment_name='Local clock')
    ignition.insert_ignition_data(200, 1, 2, 3, 4, 5, 6, session_id=sid)
    ignition.insert_batch_data([(201, 2, 3, 4, 5, 6, 7)], session_id=sid)
    samples = ignition.get_session_temperature_data(sid)
    assert len(samples) == 2
    assert all('.' in sample['timestamp'] for sample in samples)
    assert all(0 <= sample['elapsed_seconds'] < 5 for sample in samples)


def test_legacy_utc_samples_use_local_session_clock(ignition):
    sid = ignition.start_experiment_session(experiment_name='Legacy clock')
    utc_time = (datetime.now(timezone.utc) + timedelta(seconds=2)).strftime('%Y-%m-%d %H:%M:%S')
    ignition.conn.execute('INSERT INTO ignition_realtime_data (session_id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6) VALUES (?, ?, 200, 1, 2, 3, 4, 5, 6)', (sid, utc_time))
    ignition.conn.commit()
    assert 0 <= ignition.get_session_temperature_data(sid)[0]['elapsed_seconds'] < 5


def test_empty_session_never_borrows_another_sessions_samples(ignition):
    empty = ignition.start_experiment_session(experiment_name='Empty')
    other = ignition.start_experiment_session(experiment_name='Other')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    ignition.conn.execute('INSERT INTO ignition_realtime_data (session_id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6) VALUES (?, ?, 200, 1, 2, 3, 4, 5, 6)', (other, timestamp))
    ignition.conn.commit()
    assert ignition.get_session_temperature_data(empty) == []


def test_legacy_unassigned_samples_are_matched_in_utc(ignition):
    sid = ignition.start_experiment_session(experiment_name='Legacy unassigned')
    start = datetime.now() - timedelta(seconds=2)
    end = datetime.now() + timedelta(seconds=2)
    ignition.conn.execute('UPDATE experiment_sessions SET start_time=?, end_time=? WHERE id=?', (start, end, sid))
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    ignition.conn.execute('INSERT INTO ignition_realtime_data (timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6) VALUES (?, 210, 1, 2, 3, 4, 5, 6)', (timestamp,))
    ignition.conn.commit()
    rows = ignition.get_session_temperature_data(sid)
    assert len(rows) == 1
    assert 0 <= rows[0]['elapsed_seconds'] < 5


def test_report_uses_session_identity_and_keeps_sparse_positions(qapp):
    from views.dialogs.generate_report_dialog import GenerateReportDialog
    rows = [{'elapsed_seconds': 0.5, 'sample1_temperature': 123}]
    owner = SimpleNamespace(exp_id=42, exp_type='ignition', exp_data={},
                            ignition_db=SimpleNamespace(get_session_temperature_data=lambda sid: rows if sid == 42 else []))
    assert GenerateReportDialog._get_temperature_series(owner)[0]['sample1_temperature'] == 123
    samples = [{'position': 2, 'name': 'Channel two'}, {'position': 6, 'name': 'Channel six'}]
    assert GenerateReportDialog._sample_name_for_position(samples, 2) == 'Channel two'
    assert GenerateReportDialog._sample_name_for_position(samples, 6) == 'Channel six'
    assert GenerateReportDialog._sample_name_for_position(samples, 1) == '样品1'


def test_pdf_exports_literal_user_markup(qapp, monkeypatch, tmp_path):
    from views.dialogs.generate_report_dialog import GenerateReportDialog, QFileDialog, QMessageBox
    import reportlab.platypus
    texts = []
    real_paragraph = reportlab.platypus.Paragraph
    def paragraph(text, *args, **kwargs):
        texts.append(text)
        return real_paragraph(text, *args, **kwargs)
    monkeypatch.setattr(reportlab.platypus, 'Paragraph', paragraph)
    target = tmp_path / 'report.pdf'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(target), ''))
    errors = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *a: errors.append(a[2]))
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: None)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    data = {'experiment_code': 'EXP-1', 'sample_name': '<b>raw & sample', 'conclusion': '<b>result', 'notes': 'A & B\n<raw>'}
    dialog = GenerateReportDialog(1, 'explosion', data)
    try:
        dialog.on_export_pdf()
        assert errors == []
        assert target.read_bytes().startswith(b'%PDF')
        assert any('&lt;b&gt;raw &amp; sample' in str(text) for text in texts)
        assert '&lt;b&gt;result' in texts
        assert 'A &amp; B<br/>&lt;raw&gt;' in texts
    finally:
        dialog.close()
