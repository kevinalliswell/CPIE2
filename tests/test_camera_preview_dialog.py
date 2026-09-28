"""
相机预览对话框测试（offscreen）

预览在后台线程中取帧（相机 SDK 单次取帧超时 1 秒），GUI 线程只显示最新一帧；
不再用 cv2.imshow 循环阻塞 GUI 线程，也不在 GUI 定时器里同步取帧。
"""

import threading
import time

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtTest import QTest


class FakeCamera:
    def __init__(self, frame, delay_s=0.0):
        self.frame = frame
        self.delay_s = delay_s
        self.calls = 0
        self.threads = set()

    def capture_single_frame(self):
        self.calls += 1
        self.threads.add(threading.get_ident())
        if self.delay_s:
            time.sleep(self.delay_s)
        return self.frame


class FakeFlameKit:
    def __init__(self, frame=None, init_result=True, init_error=None, delay_s=0.0):
        self.camera = FakeCamera(frame, delay_s=delay_s)
        self.init_result = init_result
        self.init_error = init_error
        self.initialize_calls = 0

    def initialize(self):
        self.initialize_calls += 1
        if self.init_error is not None:
            raise self.init_error
        return self.init_result


@pytest.fixture
def dialog_cls(qapp):
    from views.dialogs.camera_preview_dialog import CameraPreviewDialog

    return CameraPreviewDialog


def wait_until(predicate, timeout_s=2.0):
    end = time.time() + timeout_s
    while time.time() < end:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


@pytest.mark.parametrize("frame_shape", [(48, 64), (48, 64, 3)])
def test_preview_shows_frames_acquired_off_the_gui_thread(dialog_cls, frame_shape):
    frame = np.full(frame_shape, 128, dtype=np.uint8)
    kit = FakeFlameKit(frame=frame)
    dialog = dialog_cls(kit, fps=100, timeout_s=60.0)
    try:
        dialog.show()
        assert dialog.start() is True
        assert kit.initialize_calls == 1
        assert dialog.is_running()
        assert dialog.timeout_timer.isActive()

        assert wait_until(lambda: dialog.frame_count > 0)
        assert threading.get_ident() not in kit.camera.threads  # 取帧不在 GUI 线程
        assert dialog.image_label.pixmap() is not None and not dialog.image_label.pixmap().isNull()
        assert "64×48" in dialog.info_label.text()

        # "关闭预览"按钮走 close()：窗口必须真正关闭并停止取帧线程
        dialog.close_button.click()
        assert not dialog.isVisible()
        assert not dialog.is_running()
        assert not dialog.timeout_timer.isActive()
        calls = kit.camera.calls
        QTest.qWait(100)
        assert kit.camera.calls == calls
    finally:
        dialog.deleteLater()


def test_stalled_camera_does_not_block_gui(dialog_cls):
    """相机不出帧时 SDK 每次取帧阻塞约 1 秒：GUI 事件循环必须照常运行"""
    kit = FakeFlameKit(frame=None, delay_s=0.5)
    dialog = dialog_cls(kit, fps=30)
    try:
        assert dialog.start()
        assert wait_until(lambda: kit.camera.calls > 0)

        fired = []
        started = time.monotonic()
        QTimer.singleShot(0, lambda: fired.append(time.monotonic() - started))
        assert wait_until(lambda: fired, timeout_s=1.0)
        assert fired[0] < 0.2

        stop_started = time.monotonic()
        assert dialog.stop() is True  # 等待进行中的取帧结束
        assert time.monotonic() - stop_started < dialog.STOP_JOIN_TIMEOUT_S
        assert not dialog.is_running()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_preview_stops_after_timeout(dialog_cls):
    kit = FakeFlameKit(frame=np.zeros((8, 8), dtype=np.uint8))
    dialog = dialog_cls(kit, fps=100, timeout_s=0.1)
    try:
        assert dialog.start()
        assert wait_until(lambda: "超时" in dialog.info_label.text())
        assert wait_until(lambda: not dialog.is_running())
    finally:
        dialog.close()
        dialog.deleteLater()


def test_start_fails_when_camera_unavailable(dialog_cls):
    dialog = dialog_cls(FakeFlameKit(init_result=False))
    try:
        assert dialog.start() is False
        assert not dialog.is_running()
        assert "相机未就绪" in dialog.image_label.text()
    finally:
        dialog.deleteLater()

    dialog = dialog_cls(FakeFlameKit(init_error=RuntimeError("no sdk")))
    try:
        assert dialog.start() is False
        assert "no sdk" in dialog.image_label.text()
    finally:
        dialog.deleteLater()


def test_reject_closes_and_stops_worker(dialog_cls):
    kit = FakeFlameKit(frame=np.zeros((8, 8), dtype=np.uint8))
    dialog = dialog_cls(kit, fps=100)
    try:
        dialog.show()
        assert dialog.start()
        dialog.reject()  # Esc

        assert not dialog.isVisible()
        assert not dialog.is_running()
        assert not dialog.timeout_timer.isActive()
    finally:
        dialog.deleteLater()


def test_none_frames_and_capture_errors_do_not_crash(dialog_cls):
    class ErrorCamera:
        def capture_single_frame(self):
            raise RuntimeError("boom")

    kit = FakeFlameKit(frame=None)
    dialog = dialog_cls(kit, fps=100)
    try:
        assert dialog.start()
        assert wait_until(lambda: kit.camera.calls > 3)
        assert dialog.frame_count == 0
        assert dialog.stop()

        kit.camera = ErrorCamera()
        assert dialog.start()
        assert wait_until(lambda: "boom" in dialog.info_label.text())
    finally:
        dialog.close()
        dialog.deleteLater()
