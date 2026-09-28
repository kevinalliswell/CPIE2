#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验数据一致性回归测试

- 实时温度数据的时间戳必须与会话开始时间使用同一（本地）时钟，elapsed_seconds 不能偏差一个时区
- 旧数据（SQLite CURRENT_TIMESTAMP 写入的 UTC 时间戳）读取时要转换为本地时间
- 删除会话时先删数据库记录再删文件；找不到会话时不得删除任何文件
- 温升速率/温升窗口按真实采样周期换算
"""

import os
import sys
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from models.ignition_database import IgnitionDatabase  # noqa: E402
from services.ignition.ignition_detection_service import IgnitionDetectionService  # noqa: E402


@pytest.fixture
def db(tmp_path):
    database = IgnitionDatabase(str(tmp_path / "ignition.db"))
    yield database
    database.close()


def _session(database, session_id):
    """按会话ID取回会话字典（IgnitionDatabase 没有 get_session_by_id）"""
    return next((s for s in database.get_all_experiment_sessions() if s["id"] == session_id), None)


def test_realtime_timestamps_use_session_clock(db):
    session_id = db.start_experiment_session(experiment_id="IGN-TEST", experiment_name="t")
    assert session_id > 0
    for i in range(3):
        assert db.insert_ignition_data(200 + i, 1, 2, 3, 4, 5, 6, session_id=session_id) > 0

    data = db.get_session_temperature_data(session_id)
    assert len(data) == 3
    for record in data:
        assert 0.0 <= record["elapsed_seconds"] < 5.0
        assert "." in record["timestamp"]  # 新数据固定带小数秒

    # 按会话开始/结束时间做范围查询也必须能命中（旧版报告曲线依赖此行为）
    assert db.end_experiment_session(session_id, status="completed")
    session = _session(db, session_id)
    assert session is not None and session["status"] == "completed"
    rows = db.get_data_by_time_range(str(session["start_time"]), str(session["end_time"]))
    assert len(rows) == 3


def test_legacy_utc_timestamps_are_converted(db):
    session_id = db.start_experiment_session(experiment_id="IGN-LEGACY", experiment_name="t")
    # 模拟旧版本写入：CURRENT_TIMESTAMP（UTC、无小数秒）
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    legacy_ts = (now_utc + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")
    db.cursor.execute(
        "INSERT INTO ignition_realtime_data (session_id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, legacy_ts, 200, 1, 2, 3, 4, 5, 6),
    )
    db.conn.commit()

    data = db.get_session_temperature_data(session_id)
    assert len(data) == 1
    assert 0.0 <= data[0]["elapsed_seconds"] < 10.0


def test_end_experiment_session_reports_missing_session(db):
    assert db.end_experiment_session(9999, status="completed") is False


def test_delete_session_removes_files_only_after_db_delete(db, tmp_path):
    session_id = db.start_experiment_session(experiment_id="IGN-DEL", experiment_name="t")
    image = tmp_path / "tangent_ch1.png"
    image.write_bytes(b"png")
    db.record_ignition_detection(session_id, 1, 350.0, detection_method="tangent", image_path=str(image))

    assert db.delete_session(session_id) is True
    assert not image.exists()
    assert _session(db, session_id) is None

    # 会话不存在时不得删除任何文件
    other = tmp_path / "other.png"
    other.write_bytes(b"png")
    assert db.delete_session(424242) is False
    assert other.exists()


def test_get_all_data_rejects_unknown_order_column(db):
    session_id = db.start_experiment_session(experiment_id="IGN-ORD", experiment_name="t")
    db.insert_ignition_data(200, 1, 2, 3, 4, 5, 6, session_id=session_id)
    rows = db.get_all_data(order_by="pv; DROP TABLE ignition_realtime_data", limit=1)
    assert len(rows) == 1
    assert db.get_all_data(limit=5)


def test_backup_contains_data(db, tmp_path):
    session_id = db.start_experiment_session(experiment_id="IGN-BAK", experiment_name="t")
    db.insert_ignition_data(200, 1, 2, 3, 4, 5, 6, session_id=session_id)
    backup_path = tmp_path / "backups" / "ignition_backup.db"
    assert db.backup(str(backup_path)) is True

    copy = IgnitionDatabase(str(backup_path))
    try:
        assert _session(copy, session_id) is not None
        assert len(copy.get_session_temperature_data(session_id)) == 1
    finally:
        copy.close()


def _service():
    config = {
        "ignition_detection": {
            "enabled": True,
            "criteria": {
                "absolute_temperature": {"enabled": False, "threshold": 600.0},
                "temperature_rise": {"enabled": False, "threshold": 10.0, "time_window": 10.0},
                "rise_rate": {"enabled": True, "threshold": 0.25},
            },
        }
    }
    service = IgnitionDetectionService(config)
    service.last_check_time = 0.0  # 跳过调用频率限制
    return service


def test_rise_rate_uses_real_sample_interval():
    # 0.1 °C/s 的缓慢升温：每 0.5 s 采样一次，相邻样本相差 0.05 °C
    history = {0: deque([300 + 0.05 * i for i in range(10)])}
    flags = [False]

    # 未提供采样周期（旧行为）：按 0.2 s 换算得到 0.25 °C/s，误判着火
    assert _service().check_ignition(history, flags, 0.2, 150.0) == [(0, history[0][-1], "温升速率")]
    # 提供真实采样周期 0.5 s：速率为 0.1 °C/s，低于阈值，不应判定着火
    assert _service().check_ignition(history, flags, 0.2, 150.0, sample_interval=0.5) == []

    # 真正的快速温升（1 °C/s）在真实采样周期下仍能检出
    fast = {0: deque([300 + 0.5 * i for i in range(10)])}
    assert _service().check_ignition(fast, [False], 0.2, 150.0, sample_interval=0.5) == [(0, fast[0][-1], "温升速率")]
