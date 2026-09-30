"""Round acceptance must be backed by valid analysis and committed SQLite data."""
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from services.explosion.experiment_validator import ExperimentValidator
from services.explosion.flame_analysis_handler import FlameAnalysisHandler
from services.explosion.round_manager import RoundManager


@pytest.fixture
def analysis(tmp_path):
    from models.explosion_database import ExplosionDatabase
    from utils.path_manager import PathManager

    config_path = Path(PathManager.get_config_path('experiment_config.yaml'))
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))['explosion_experiment']
    db = ExplosionDatabase(str(tmp_path / 'analysis.db'), config_path=str(config_path))
    sid = db.start_experiment_session(experiment_name='analysis regression')
    image = Path(PathManager.get_max_flame_images_path('round-1.png'))
    image.write_bytes(b'preserve captured evidence')
    result = dict(max_flame_size=30.0, min_flame_size=10.0,
                  average_flame_size=20.0, total_images=3, failed_images=0,
                  max_flame_saved_path=str(image))
    try:
        yield db, sid, FlameAnalysisHandler(RoundManager(config), db), result, image
    finally:
        db.close()


def test_failed_sqlite_commit_does_not_accept_round_or_consume_images(analysis):
    db, sid, handler, result, image = analysis
    records = []
    db.conn.execute("CREATE TRIGGER deny_round BEFORE INSERT ON test_rounds "
                    "BEGIN SELECT RAISE(ABORT, 'injected write failure'); END")
    failed = handler.process_analysis_results(result, sid, 1, records)
    assert failed['success'] is False
    assert failed.get('db_saved') is False
    assert 'record' not in failed and 'next_action' not in failed
    assert records == [] and db.get_session_test_rounds(sid) == []
    assert image.read_bytes() == b'preserve captured evidence'

    db.conn.execute('DROP TRIGGER deny_round')
    retried = handler.process_analysis_results(result, sid, 1, records)
    assert retried['success'] and retried['db_saved']
    assert len(db.get_session_test_rounds(sid)) == 1
    assert image.exists()


@pytest.mark.parametrize('changes', [
    {'max_flame_size': None}, {'max_flame_size': float('nan')},
    {'max_flame_size': float('inf')}, {'max_flame_size': -1.0},
    {'max_flame_size': True}, {'min_flame_size': 40.0},
    {'average_flame_size': float('inf')}, {'average_flame_size': 31.0},
    {'total_images': 0}, {'total_images': True}, {'total_images': 1.5},
    {'failed_images': 3}, {'failed_images': -1},
])
def test_invalid_or_empty_analysis_is_never_saved(analysis, changes):
    db, sid, handler, result, image = analysis
    result.update(changes)
    processed = handler.process_analysis_results(result, sid, 1, [])
    assert processed['success'] is False
    assert 'record' not in processed and 'next_action' not in processed
    assert db.get_session_test_rounds(sid) == []
    assert image.exists()


def test_missing_measurement_is_not_a_zero_flame(analysis):
    db, sid, handler, result, image = analysis
    del result['max_flame_size']
    assert not handler.process_analysis_results(result, sid, 1, [])['success']
    assert db.get_session_test_rounds(sid) == []


def test_real_zero_flame_with_successful_images_is_accepted(analysis):
    db, sid, handler, result, image = analysis
    result.update(max_flame_size=0.0, min_flame_size=0.0, average_flame_size=0.0)
    processed = handler.process_analysis_results(result, sid, 1, [])
    assert processed['success'] and processed['db_saved']
    assert db.get_session_test_rounds(sid)[0]['flame_length'] == 0.0


def test_partial_image_failure_cannot_hide_a_missed_peak(analysis):
    db, sid, handler, result, image = analysis
    result['failed_images'] = 1
    processed = handler.process_analysis_results(result, sid, 1, [])
    assert processed['success'] is False
    assert 'record' not in processed and 'next_action' not in processed
    assert db.get_session_test_rounds(sid) == []
    assert image.exists()


@pytest.mark.parametrize('kind', ['missing-key', 'blank', 'missing-file', 'directory',
                                  'empty-file', 'capture-temp', 'analysis-temp', 'temp-symlink'])
def test_max_flame_evidence_must_survive_temporary_cleanup(analysis, tmp_path, kind):
    from utils.path_manager import PathManager
    db, sid, handler, result, original_image = analysis
    if kind == 'missing-key':
        del result['max_flame_saved_path']
    elif kind == 'blank':
        result['max_flame_saved_path'] = ''
    else:
        path = tmp_path / 'candidate.png'
        if kind == 'directory':
            path.mkdir()
        elif kind == 'empty-file':
            path.touch()
        elif kind in ('capture-temp', 'analysis-temp', 'temp-symlink'):
            root = Path(PathManager.get_flame_results_path() if kind == 'analysis-temp'
                        else PathManager.get_flame_temp_path())
            transient = root / 'round-1.png'
            transient.write_bytes(b'transient frame')
            if kind == 'temp-symlink':
                try:
                    path.symlink_to(transient)
                except OSError:
                    pytest.skip('This filesystem cannot create symlinks')
            else:
                path = transient
        result['max_flame_saved_path'] = str(path)
    processed = handler.process_analysis_results(result, sid, 1, [])
    assert processed['success'] is False
    assert 'record' not in processed and 'next_action' not in processed
    assert db.get_session_test_rounds(sid) == []
    assert original_image.exists()


def test_analysis_cannot_append_to_an_ended_session(analysis):
    db, sid, handler, result, image = analysis
    assert db.end_experiment_session(sid, status='cancelled')
    assert not handler.process_analysis_results(result, sid, 1, [])['success']
    assert db.get_session_test_rounds(sid) == []


def test_old_callback_cannot_overwrite_a_committed_round(analysis):
    db, sid, handler, result, image = analysis
    assert db.add_test_round(sid, 1, 12.0, 'first.png') > 0
    processed = handler.process_analysis_results(result, sid, 1, [])
    assert not processed['success']
    assert db.get_session_test_rounds(sid)[0]['flame_length'] == 12.0


def test_skipped_attempt_cannot_count_as_a_complete_phase(analysis):
    db, sid, handler, result, image = analysis
    processed = handler.process_analysis_results(result, sid, 2, [])
    assert not processed['success']
    assert db.get_session_test_rounds(sid) == []


def test_memory_records_must_match_the_saved_rounds(analysis):
    db, sid, handler, result, image = analysis
    assert db.add_test_round(sid, 1, 12.0, 'first.png') > 0
    stale = [{'round': 1, 'flame_length': 999.0, 'image_path': 'first.png'}]
    assert not handler.process_analysis_results(result, sid, 2, stale)['success']
    assert len(db.get_session_test_rounds(sid)) == 1


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1.0, True, 'bad', None])
def test_database_round_writers_reject_invalid_measurements(analysis, value):
    db, sid, handler, result, image = analysis
    assert db.add_test_round(sid, 1, value) == -1
    assert db.add_batch_test_rounds(sid, [(1, value, '')]) == 0
    round_id = db.add_test_round(sid, 1, 30.0)
    assert round_id > 0
    assert not db.update_test_round(round_id, flame_length=value)
    assert db.get_session_test_rounds(sid)[0]['flame_length'] == 30.0


@pytest.mark.parametrize('number', [True, 1.5, '1', None])
def test_database_round_numbers_are_integers(analysis, number):
    db, sid, handler, result, image = analysis
    assert db.add_test_round(sid, number, 30.0) == -1
    assert db.add_batch_test_rounds(sid, [(number, 30.0, '')]) == 0


def test_old_nonfinite_measurements_cannot_be_finalized(analysis):
    db, sid, handler, result, image = analysis
    db.conn.execute('INSERT INTO test_rounds (session_id, round_number, flame_length) VALUES (?, ?, ?)',
                    (sid, 1, float('inf')))
    db.conn.commit()
    assert not db.finalize_experiment(sid)
    assert db.get_session_result(sid) is None
    assert db.get_session_by_id(sid)['end_time'] is None


@pytest.mark.parametrize('rows', [
    [(1, -10.0), (2, 30.0)], [(1, 10.0), (1, 30.0)], [(2, 30.0)],
])
def test_invalid_legacy_round_sets_cannot_produce_a_summary(analysis, rows):
    db, sid, handler, result, image = analysis
    db.conn.executemany('INSERT INTO test_rounds (session_id, round_number, flame_length) VALUES (?, ?, ?)',
                        [(sid, number, length) for number, length in rows])
    db.conn.commit()
    assert not db.finalize_experiment(sid)
    assert db.get_session_result(sid) is None
    assert db.get_session_by_id(sid)['end_time'] is None


def test_phase_threshold_is_independent_from_strength_classification():
    manager = RoundManager({'test-rounds': {'phase-rounds': 5, 'max-rounds': 10,
                                           'phase-decision-threshold': 20.0},
                            'explosion-thresholds': {'no-explosion': 25.0}})
    records = [{'round': i, 'flame_length': 22.0} for i in range(1, 6)]
    assert manager.get_next_action(5, records)['action'] == 'complete'
    assert not manager.should_continue_phase2(records)[0]
    assert manager.evaluate_explosion_level(22.0)[0] == '无爆炸性'
    assert '标准' not in manager.get_next_action(5, records)['message']


def test_conclusion_does_not_claim_completion_before_required_rounds():
    handler = FlameAnalysisHandler(RoundManager({}), None)
    records = [{'round': 1, 'flame_length': 100.0}]
    message, complete = handler.build_conclusion_message(records, meets_standard=True)
    assert not complete
    assert '标准' not in message


@pytest.mark.parametrize('records', [
    [{'round': 2, 'flame_length': 0.0}],
    [{'round': 1, 'flame_length': 0.0}, {'round': 1, 'flame_length': 0.0}],
])
def test_round_decisions_reject_sparse_or_duplicate_records(records):
    manager = RoundManager({'test-rounds': {'phase-rounds': 1, 'max-rounds': 2}})
    with pytest.raises(ValueError):
        manager.get_next_action(2, records)


@pytest.mark.parametrize('config', [
    {'test-rounds': {'phase-rounds': 0}},
    {'test-rounds': {'phase-rounds': 5, 'max-rounds': 2}},
    {'test-rounds': {'phase-decision-threshold': float('nan')}},
    {'explosion-thresholds': {'no-explosion': 500.0, 'weak-explosion': 400.0}},
])
def test_round_configuration_rejects_invalid_limits(config):
    with pytest.raises(ValueError):
        RoundManager(config)


@pytest.mark.parametrize('field,value', [
    ('value', float('nan')), ('value', True), ('tolerance', float('inf')),
    ('tolerance', -1.0), ('tolerance', None),
])
def test_start_conditions_reject_invalid_target_configuration(field, value):
    config = {'control_conditions': {
        'target_temperature': {'value': 1100.0, 'tolerance': 2.0},
        'target_pressure': {'value': 50.0, 'tolerance': 2.0},
    }}
    config['control_conditions']['target_temperature'][field] = value
    manager = SimpleNamespace(get_latest_data=lambda name:
        {'pv': 1100.0} if name == '爆炸性-温控仪表' else {'pressure': 50.0})
    valid, message = ExperimentValidator(config, manager).check_conditions()
    assert not valid
    assert '配置' in message


def test_missing_start_conditions_do_not_silently_mean_zero_targets():
    manager = SimpleNamespace(get_latest_data=lambda name: {'pv': 0.0, 'pressure': 0.0})
    valid, message = ExperimentValidator({}, manager).check_conditions()
    assert not valid
    assert '配置' in message


def test_valid_configured_conditions_keep_inclusive_tolerances():
    config = {'control_conditions': {
        'target_temperature': {'value': 1100.0, 'tolerance': 2.0},
        'target_pressure': {'value': 50.0, 'tolerance': 2.0},
    }}
    manager = SimpleNamespace(get_latest_data=lambda name:
        {'pv': 1098.0} if name == '爆炸性-温控仪表' else {'pressure': 52.0})
    assert ExperimentValidator(config, manager).check_conditions()[0]
