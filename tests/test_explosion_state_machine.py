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


def test_verify_relays_off_requires_fresh_readback(make_controller):
    controller = make_controller()
    controller.config["devices"] = [{"name": "爆炸性-继电器", "type": "relay_controller", "poll_interval": 0.05}]
    controller.sequence_running = True  # 校验步骤只在时序运行中执行，等待逻辑依赖该标志
    step = {"retry_count": 2, "retry_delay": 0.02}

    # 没有任何回读
    assert controller._verify_relays_off(step) is False

    # 回读是本步骤开始之前采集的（旧数据），即使全部为关也不能确认
    controller.manager.latest["爆炸性-继电器"] = {
        "relays": {"relay_1": False, "relay_2": False}, "timestamp": time.time() - 10.0,
    }
    assert controller._verify_relays_off(step) is False

    # 新鲜回读但仍有继电器导通
    controller.manager.latest["爆炸性-继电器"] = {
        "relays": {"relay_1": False, "relay_2": True}, "timestamp": time.time() + 5.0,
    }
    assert controller._verify_relays_off(step) is False

    # 新鲜回读且全部关闭
    controller.manager.latest["爆炸性-继电器"] = {
        "relays": {"relay_1": False, "relay_2": False}, "timestamp": time.time() + 5.0,
    }
    assert controller._verify_relays_off(step) is True


def test_verify_relays_off_waits_for_next_poll(make_controller):
    """retry_count*retry_delay 小于轮询周期时，验证窗口仍要覆盖下一次回读"""
    controller = make_controller()
    controller.config["devices"] = [{"name": "爆炸性-继电器", "type": "relay_controller", "poll_interval": 0.2}]
    controller.sequence_running = True
    step = {"retry_count": 1, "retry_delay": 0.01}

    def poller():
        time.sleep(0.25)
        controller.manager.latest["爆炸性-继电器"] = {
            "relays": {"relay_1": False}, "timestamp": time.time(),
        }

    import threading
    threading.Thread(target=poller, daemon=True).start()
    assert controller._verify_relays_off(step) is True


class _AliveThread:
    """模拟一个尚未退出的旧时序线程"""

    def __init__(self):
        self.alive = True
        self.join_timeouts = []

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.join_timeouts.append(timeout)


def test_start_refused_until_previous_sequence_thread_exits(make_controller):
    """停止后旧时序线程未退出前不得启动新一轮，否则旧线程会继续执行剩余步骤"""
    controller = make_controller()
    old_thread = _AliveThread()
    controller._sequence_thread = old_thread

    assert controller.start_experiment() is False
    assert old_thread.join_timeouts  # 先等待过旧线程
    assert controller.current_state == S.SESSION_CREATED
    assert controller.current_round_number == 0
    assert controller.manager.sent == []

    old_thread.alive = False
    assert controller.start_experiment() is True
    assert controller._sequence_thread is not old_thread
    pump(0.1)
    controller.stop_experiment()
    pump(0.6)


def test_immediate_restart_after_stop_waits_for_old_thread(make_controller):
    controller = make_controller(sequence_steps=[
        {"step": 1, "name": "open", "action": "relay_on", "relay": "spray_valve", "delay_after": 0.0},
        {"step": 2, "name": "wait", "action": "delay", "duration": 5.0},
        {"step": 3, "name": "purge", "action": "relay_on", "relay": "purge_valve", "delay_after": 0.0},
    ])
    assert controller.start_experiment()
    pump(0.1)
    first_thread = controller._sequence_thread
    assert controller.stop_experiment()

    # 立即重新启动：必须等旧线程退出，而不是让它和新一轮并发
    assert controller.start_experiment()
    assert not first_thread.is_alive()
    pump(0.2)
    assert controller.current_state == S.SEQUENCE_RUNNING
    assert controller.sequence_running
    assert (2, True) not in controller.manager.sent
    controller.stop_experiment()
    pump(0.6)


def test_stop_sends_offs_after_in_flight_relay_on(make_controller):
    """停止时补发的关闭命令必须排在时序线程正在下发的打开命令之后"""
    import threading

    controller = make_controller()
    manager = controller.manager
    entered = threading.Event()
    release = threading.Event()
    original_send = manager.send_control

    def blocking_send(device_name, control_data, priority="normal"):
        if control_data["set_relay"] == {"relay": 1, "state": True}:
            entered.set()
            release.wait(2.0)
        return original_send(device_name, control_data, priority)

    manager.send_control = blocking_send
    controller._set_state(S.SEQUENCE_RUNNING)
    controller.is_running = True
    controller.sequence_running = True

    results = {}
    worker = threading.Thread(target=lambda: results.setdefault("on", controller._sequence_relay_on("spray_valve")))
    worker.start()
    assert entered.wait(2.0)

    stopper = threading.Thread(target=lambda: results.setdefault("stop", controller.stop_experiment()))
    stopper.start()
    time.sleep(0.1)
    assert all(state for _, state in manager.sent)  # 打开命令入队前不得先发关闭命令

    release.set()
    worker.join(2.0)
    stopper.join(2.0)

    assert results == {"on": True, "stop": True}
    on_index = manager.sent.index((1, True))
    off_indices = [i for i, (_, state) in enumerate(manager.sent) if state is False]
    assert off_indices and min(off_indices) > on_index
    # 停止之后时序线程不再下发打开命令
    assert controller._sequence_relay_on("purge_valve") is None
    assert (2, True) not in manager.sent


def test_stale_sequence_thread_does_not_touch_new_run(make_controller):
    controller = make_controller(sequence_steps=[])
    controller._set_state(S.SEQUENCE_RUNNING)
    controller.sequence_running = True
    controller._sequence_generation = 2
    completed = []
    controller.sequence_completed.connect(lambda: completed.append(True))

    controller._execute_sequence(generation=1)

    assert controller.sequence_running is True
    assert controller.current_state == S.SEQUENCE_RUNNING
    assert completed == []
    controller.sequence_running = False
    controller._set_state(S.SESSION_CREATED)


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
