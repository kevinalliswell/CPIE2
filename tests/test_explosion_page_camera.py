"""
爆炸性实验页面的相机时序测试（offscreen）

- camera.trigger_delay > 0 时的延时拍摄由页面持有的定时器执行：停止/换轮后必须取消，
  时序先于拍摄结束时要等拍摄完成后再打开火焰分析器
- 预览在后台线程取帧：拍摄与释放相机前必须先关闭预览
"""

import copy
import time
from pathlib import Path

import pytest
import yaml
from PySide6.QtCore import QCoreApplication

from models.experiment_states import ExplosionExperimentState as S

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "experiment_config.yaml"


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


@pytest.fixture
def page(qapp, tmp_path, monkeypatch):
    from utils import path_manager as pm

    monkeypatch.setattr(pm.PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))
    from views.pages.explosion_page import ExplosionExperimentPage

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = copy.deepcopy(yaml.safe_load(f)["explosion_experiment"])
    config["camera"]["trigger_delay"] = 0.05

    page = ExplosionExperimentPage(config=config, ui_config={"update_interval": 500})
    page.camera_enabled = True
    page.controller.current_state = S.SEQUENCE_RUNNING
    page.controller.current_round_number = 1

    events = []
    page._trigger_camera_capture = lambda: events.append("capture")
    page._analyze_flame = lambda: events.append("analyze")
    page.events = events
    yield page
    page.controller.current_state = S.IDLE
    page.cleanup()
    page.deleteLater()


def test_zero_delay_captures_immediately(page):
    page.config["camera"]["trigger_delay"] = 0.0
    page._on_spray_valve_opened()
    assert page.events == ["capture"]
    assert not page._capture_timer.isActive()


def test_delayed_capture_runs_for_the_originating_round(page):
    page._on_spray_valve_opened()
    assert page.events == []
    assert page._capture_timer.isActive()

    pump(0.2)

    assert page.events == ["capture"]
    assert not page._capture_timer.isActive()


def test_stop_cancels_pending_capture(page):
    page._on_spray_valve_opened()
    page._on_controller_experiment_stopped()
    pump(0.2)

    assert page.events == []
    assert not page._capture_timer.isActive()


def test_capture_for_a_previous_round_is_skipped(page):
    page._on_spray_valve_opened()
    page.controller.current_round_number = 2  # 另一轮已开始
    pump(0.2)

    assert page.events == []


def test_new_round_start_cancels_pending_capture(page):
    page._on_spray_valve_opened()
    page._on_controller_experiment_started()
    pump(0.2)

    assert page.events == []


def test_sequence_completion_waits_for_pending_capture_before_analysis(page):
    page.config["camera"]["trigger_delay"] = 0.1
    page._on_spray_valve_opened()

    page._on_controller_sequence_completed()
    page.controller.current_state = S.WAITING_ANALYSIS
    pump(0.03)
    assert page.events == []  # 图像尚未拍摄，不能先打开分析器

    pump(0.25)
    assert page.events == ["capture", "analyze"]


def test_sequence_completion_without_pending_capture_opens_analyzer(page):
    page.config["camera"]["trigger_delay"] = 0.0
    page._on_spray_valve_opened()
    page._on_controller_sequence_completed()
    pump(0.05)

    assert page.events == ["capture", "analyze"]


class FakePreview:
    def __init__(self, log):
        self.log = log

    def stop(self):
        self.log.append("preview-stop")
        return True

    def close(self):
        self.log.append("preview-close")


def test_camera_users_close_preview_first(page, monkeypatch):
    from views.pages.explosion_page import ExplosionExperimentPage

    log = []
    monkeypatch.setattr(page.flame_kit, "capture_one_second",
                        lambda temp_dir=None, duration=None: (log.append("capture") or ([], 0)))

    page.preview_dialog = FakePreview(log)
    ExplosionExperimentPage._trigger_camera_capture(page)
    assert log[:3] == ["preview-stop", "preview-close", "capture"]
    assert page.preview_dialog is None

    log.clear()
    page.preview_dialog = FakePreview(log)
    page._manual_capture()
    assert log[:3] == ["preview-stop", "preview-close", "capture"]


def test_toggle_preview_refused_while_sequence_running(page, monkeypatch):
    import views.dialogs.camera_preview_dialog as preview_module

    created = []
    monkeypatch.setattr(preview_module, "CameraPreviewDialog", lambda *a, **k: created.append(True))

    page._toggle_preview()

    assert created == []
    assert page.preview_dialog is None


def test_cleanup_closes_preview_before_releasing_camera(page, monkeypatch):
    log = []
    page.preview_dialog = FakePreview(log)
    monkeypatch.setattr(page.flame_kit, "release", lambda: log.append("release"))

    page.cleanup()

    assert "release" in log
    assert log.index("preview-stop") < log.index("release")


class StuckPreview(FakePreview):
    def stop(self):
        self.log.append("preview-stop")
        return False


def test_capture_aborts_and_keeps_preview_when_it_cannot_stop(page, monkeypatch):
    from views.pages.explosion_page import ExplosionExperimentPage

    log = []
    monkeypatch.setattr(page.flame_kit, "capture_one_second",
                        lambda temp_dir=None, duration=None: (log.append("capture") or ([], 0)))
    monkeypatch.setattr(page.flame_kit, "release", lambda: log.append("release"))
    stuck = StuckPreview(log)
    page.preview_dialog = stuck

    ExplosionExperimentPage._trigger_camera_capture(page)
    page._manual_capture()

    assert "capture" not in log
    assert page.preview_dialog is stuck  # 下次调用还会再次等待

    page.cleanup()
    assert "release" not in log
