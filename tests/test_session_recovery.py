"""Startup recovery closes orphan sessions without inventing measured results."""
import importlib
import sqlite3
from datetime import datetime

import pytest


@pytest.fixture(params=["ignition", "explosion"])
def database(request, tmp_path):
    name = request.param
    module = importlib.import_module(f"models.{name}_database")
    cls = getattr(module, f"{name.title()}Database")
    db = cls(str(tmp_path / f"{name}.db"))
    yield name, db
    db.close()


def session_rows(db):
    return db.conn.execute("SELECT * FROM experiment_sessions ORDER BY id").fetchall()


def test_recovery_is_explicit_preserves_measurements_and_is_idempotent(database):
    kind, db = database
    states = [("prepared", None), ("running", None), ("error", None),
              ("running", "2026-09-01 12:00:00"), ("completed", None), ("cancelled", None)]
    ids = []
    for status, end_time in states:
        session_id = db.start_experiment_session(experiment_name=status, description="现场原始备注")
        ids.append(session_id)
        db.conn.execute("UPDATE experiment_sessions SET status=?, end_time=? WHERE id=?",
                        (status, end_time, session_id))
    db.conn.commit()
    if kind == "ignition":
        db.insert_ignition_data(410, 420, 421, 422, 423, 424, 425, session_id=ids[1])
        db.record_ignition_detection(ids[1], 1, 420)
        measurement_tables = ("ignition_realtime_data", "ignition_detection")
    else:
        db.add_test_round(ids[1], 1, 123.5, None)
        measurement_tables = ("test_rounds", "experiment_results")
    original_measurements = {
        table: db.conn.execute(f"SELECT * FROM {table}").fetchall()
        for table in measurement_tables
    }
    original_sessions = session_rows(db)

    # History creates additional DB connections during a live process. Merely
    # opening a connection must not interpret that process's session as orphaned.
    observer = type(db)(db.db_path)
    assert session_rows(observer) == original_sessions
    before = datetime.now()
    assert db.recover_interrupted_sessions() == 3
    after = datetime.now()
    recovered = db.conn.execute(
        "SELECT id, status, end_time, description FROM experiment_sessions ORDER BY id"
    ).fetchall()
    for session_id, status, end_time, description in recovered[:3]:
        assert status == "error"
        assert before <= datetime.fromisoformat(end_time) <= after
        assert description.startswith("现场原始备注\n")
        assert "恢复检测时间" in description
        assert "不是实测结束时间" in description
    # Existing end times and non-active states remain byte-for-byte unchanged.
    assert session_rows(db)[3:] == original_sessions[3:]
    recovered_sessions = session_rows(db)
    assert db.recover_interrupted_sessions() == 0
    assert session_rows(observer) == recovered_sessions
    for table in measurement_tables:
        assert db.conn.execute(f"SELECT * FROM {table}").fetchall() == original_measurements[table]
    observer.close()


def test_recovery_failure_rolls_back_and_is_not_reported_as_success(database):
    _, db = database
    db.start_experiment_session(experiment_name="first")
    second = db.start_experiment_session(experiment_name="second")
    db.conn.execute(f"""
        CREATE TRIGGER reject_recovery BEFORE UPDATE ON experiment_sessions
        WHEN OLD.id = {second}
        BEGIN SELECT RAISE(ABORT, 'recovery denied'); END
    """)
    db.conn.commit()
    before = session_rows(db)
    with pytest.raises(sqlite3.Error, match="recovery denied"):
        db.recover_interrupted_sessions()
    assert session_rows(db) == before


def test_ending_missing_session_returns_false(database):
    _, db = database
    assert db.end_experiment_session(987654, "error") is False
    session_id = db.start_experiment_session(experiment_name="real session")
    assert db.end_experiment_session(session_id, "cancelled") is True
    assert db.conn.execute("SELECT status FROM experiment_sessions WHERE id=?",
                           (session_id,)).fetchone()[0] == "cancelled"
