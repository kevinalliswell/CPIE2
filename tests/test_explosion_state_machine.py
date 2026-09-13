#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验状态机与控制器安全行为回归测试

覆盖的缺陷：
- 用户停止运行中的时序后必须回到 SESSION_CREATED（此前卡在 WAITING_ANALYSIS，无法继续）
- SESSION_CREATED 必须允许直接完成实验（此前完成实验被拒绝并以 running 状态写库）
- 时序异常中止后必须关闭全部继电器并回到可恢复状态（此前 ERROR 状态下阀门保持导通且无按钮可用）
- 没有继电器回读数据时 verify_all_off 不能判定为"已关闭"
- 清理时必须断开设备管理器并冲刷尚未执行的继电器关闭命令
"""

import os
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT / "modbus_multi_device_package", PROJECT_ROOT / "flame_package", PROJECT_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("numpy")
pytest.importorskip("cv2")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from models.experiment_states import ExplosionExperimentState as S  # noqa: E402


class FakeExecutor:
    def __init__(self):
        self.queue = []

    def stop(self):
        self.queue.clear()


class FakeManager:
    """模拟 ModbusDeviceManager：send_control 只是入队，不代表已执行"""

    def __init__(self, fail_relays=()):
        self.started = True
        self.connected = True
        self.executor = FakeExecutor()
        self.sent = []
        self.fail_relays = set(fail_relays)
        self.latest = {}
        self.disconnected = False

    def send_control(self, device_name, control_data, priority="normal"):
        relay = control_data["set_relay"]["relay"]
        state = control_data["set_relay"]["state"]
        self.sent.append((relay, state))
        if relay in self.fail_relays and state:
            return False
        self.executor.queue.append((relay, state))
        return True

    def get_latest_data(self, name):
        return self.latest.get(name)

    def stop(self):
        self.executor.stop()

    def disconnect(self):
        self.disconnected = True
        self.stop()


@pytest.fixture(scope="module")
def qapp():
    # 必须使用 QApplication（而非 QCoreApplication）：同一进程内的其他测试会创建 QWidget，
    # 若先创建了 QCoreApplication，后续 QWidget 构造会直接终止解释器
    return QApplication.instance() or QApplication([])


@pytest.fixture
def make_controller(qapp, tmp_path, monkeypatch):
    """构造把数据目录重定向到临时目录的 ExplosionController"""
    from utils import path_manager as pm

    monkeypatch.setattr(pm.PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))

    from controllers.explosion_controller import ExplosionController

    created = []

    def _make(sequence_steps=None, fail_relays=()):
        config = {
            "relay_mapping": {"spray_valve": 1, "purge_valve": 2, "vacuum_cleaner": 3, "reserved": 4},
            "sequence_steps": sequence_steps or [
                {"step": 1, "name": "open", "action": "relay_on", "relay": "spray_valve", "delay_after": 0.0},
                {"step": 2, "name": "wait", "action": "delay", "duration": 0.3},
                {"step": 3, "name": "close", "action": "relay_off", "relay": "spray_valve", "delay_after": 0.0},
                {"step": 4, "name": "multi", "action": "relay_multi_on", "relays": ["purge_valve", "vacuum_cleaner"]},
                {"step": 5, "name": "multi off", "action": "relay_multi_off", "relays": ["purge_valve", "vacuum_cleaner"]},
            ],
        }
        controller = ExplosionController(config=config)
        controller.manager = FakeManager(fail_relays=fail_relays)
        controller._set_state(S.CONNECTED)
        assert controller.create_experiment({
            "experiment_id": "EXP-TEST", "experiment_name": "n", "sample_name": "s", "description": "",
        })
        created.append(controller)
        return controller

    yield _make

    for controller in created:
        controller.cleanup()


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_transition_table_allows_stop_and_finalize():
    assert S.SEQUENCE_RUNNING.can_transition_to(S.SESSION_CREATED)
    assert S.SESSION_CREATED.can_transition_to(S.COMPLETED)
    # 原有转换保持不变
    assert S.SEQUENCE_RUNNING.can_transition_to(S.WAITING_ANALYSIS)
    assert S.WAITING_ANALYSIS.can_transition_to(S.SESSION_CREATED)
    assert S.ERROR.can_transition_to(S.SESSION_CREATED)
    assert not S.CANCELLED.can_transition_to(S.SESSION_CREATED)


def test_user_stop_returns_to_session_created(make_controller):
    controller = make_controller()
    assert controller.start_experiment()
    pump(0.1)
    assert controller.stop_experiment()
    pump(0.6)  # 等待时序线程退出

    assert controller.current_state == S.SESSION_CREATED
    assert controller.current_state.can_start()
    assert not controller.is_running and not controller.sequence_running
    # 停止时必须下发全部继电器的关闭命令
    assert {(1, False), (2, False), (3, False), (4, False)} <= set(controller.manager.sent)
    # 可以再次启动下一轮
    assert controller.start_experiment()
    pump(0.1)
    controller.stop_experiment()
    pump(0.6)


def test_relay_failure_shuts_down_relays_and_recovers(make_controller):
    controller = make_controller(fail_relays={3})  # 打开吸尘器失败
    assert controller.start_experiment()
    pump(1.5)

    sent = controller.manager.sent
    # 吹扫阀已打开后时序中止，必须为所有继电器补发关闭命令
    assert (2, True) in sent
    failure_index = sent.index((3, True))
    offs_after_failure = {relay for relay, state in sent[failure_index + 1:] if state is False}
    assert offs_after_failure == {1, 2, 3, 4}
    # 回到可恢复状态而不是 ERROR 死锁
    assert controller.current_state == S.SESSION_CREATED
    assert controller.current_state.can_start()
    assert not controller.is_running


def test_verify_relays_off_requires_readback(make_controller):
    controller = make_controller()
    step = {"retry_count": 1, "retry_delay": 0.01}
    assert controller._verify_relays_off(step) is False

    controller.manager.latest["爆炸性-继电器"] = {"relays": {"relay_1": False, "relay_2": True}}
    assert controller._verify_relays_off(step) is False

    controller.manager.latest["爆炸性-继电器"] = {"relays": {"relay_1": False, "relay_2": False}}
    assert controller._verify_relays_off(step) is True


def test_finalize_from_session_created_is_recorded_as_completed(make_controller):
    controller = make_controller()
    controller.add_test_round(controller.current_session_id, 1, 100.0, None)
    controller._set_state(S.COMPLETED)
    assert controller.current_state == S.COMPLETED
    assert controller.finalize_experiment(controller.current_session_id, status=S.COMPLETED.to_db_status())
    session = controller.db.get_session_by_id(controller.current_session_id)
    assert session["status"] == "completed"


def test_finalize_rejects_running_status(make_controller):
    controller = make_controller()
    controller.add_test_round(controller.current_session_id, 1, 100.0, None)
    assert controller.finalize_experiment(controller.current_session_id, status="running") is False
    session = controller.db.get_session_by_id(controller.current_session_id)
    assert session["status"] == "running"
    assert controller.db.get_session_result(controller.current_session_id) is None


def test_cleanup_disconnects_manager(make_controller):
    controller = make_controller(sequence_steps=[
        {"step": 1, "name": "open", "action": "relay_on", "relay": "spray_valve", "delay_after": 0.0},
        {"step": 2, "name": "wait", "action": "delay", "duration": 5.0},
    ])
    assert controller.start_experiment()
    pump(0.1)
    manager = controller.manager
    controller.cleanup()
    pump(0.3)
    assert manager.disconnected is True
    assert {(1, False), (2, False), (3, False), (4, False)} <= set(manager.sent)


def test_control_executor_flushes_pending_commands_before_stop():
    from modbus_multi_device.poller import ControlExecutor

    class SlowDevice:
        name = "dev"
        last_error = None

        def __init__(self):
            self.writes = []

        def write_control(self, control_data):
            time.sleep(0.05)
            self.writes.append(control_data)
            return True

    device = SlowDevice()
    executor = ControlExecutor(devices=[device])
    executor.start()
    for i in range(4):
        assert executor.submit_high_priority("dev", {"set_relay": {"relay": i + 1, "state": False}})
    executor.stop(flush_timeout=3.0)
    assert len(device.writes) == 4
