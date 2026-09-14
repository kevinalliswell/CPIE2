"""
相机预览对话框测试（offscreen）

预览通过 QTimer 轮询单帧，不再用 cv2.imshow 循环阻塞 GUI 线程。
"""

import numpy as np
import pytest
from PySide6.QtTest import QTest


class FakeCamera:
    def __init__(self, frame):
        self.frame = frame
        self.calls = 0

    def capture_single_frame(self):
        self.calls += 1
        return self.frame


class FakeFlameKit:
    def __init__(self, frame=None, init_result=True, init_error=None):
        self.camera = FakeCamera(frame)
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


@pytest.mark.parametrize("frame_shape", [(48, 64), (48, 64, 3)])
def test_preview_polls_frames_without_blocking(dialog_cls, frame_shape):
    frame = np.full(frame_shape, 128, dtype=np.uint8)
    kit = FakeFlameKit(frame=frame)
    dialog = dialog_cls(kit, fps=100, timeout_s=60.0)
    try:
        dialog.show()
        assert dialog.start() is True
        assert kit.initialize_calls == 1
        assert dialog.frame_timer.isActive()
        assert dialog.timeout_timer.isActive()

        QTest.qWait(150)

        assert kit.camera.calls > 0
        assert dialog.frame_count > 0
        assert dialog.image_label.pixmap() is not None and not dialog.image_label.pixmap().isNull()
        assert "64×48" in dialog.info_label.text()

        # "关闭预览"按钮走 close()：窗口必须真正关闭并停止定时器
        dialog.close_button.click()
        assert not dialog.isVisible()
        assert not dialog.frame_timer.isActive()
        assert not dialog.timeout_timer.isActive()
    finally:
        dialog.deleteLater()


def test_preview_stops_after_timeout(dialog_cls):
    kit = FakeFlameKit(frame=np.zeros((8, 8), dtype=np.uint8))
    dialog = dialog_cls(kit, fps=100, timeout_s=0.1)
    try:
        assert dialog.start()
        QTest.qWait(300)

        assert not dialog.frame_timer.isActive()
        assert "超时" in dialog.info_label.text()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_start_fails_when_camera_unavailable(dialog_cls):
    dialog = dialog_cls(FakeFlameKit(init_result=False))
    try:
        assert dialog.start() is False
        assert not dialog.frame_timer.isActive()
        assert "相机未就绪" in dialog.image_label.text()
    finally:
        dialog.deleteLater()

    dialog = dialog_cls(FakeFlameKit(init_error=RuntimeError("no sdk")))
    try:
        assert dialog.start() is False
        assert "no sdk" in dialog.image_label.text()
    finally:
        dialog.deleteLater()


def test_reject_closes_and_stops_timers(dialog_cls):
    kit = FakeFlameKit(frame=np.zeros((8, 8), dtype=np.uint8))
    dialog = dialog_cls(kit, fps=100)
    try:
        dialog.show()
        assert dialog.start()
        dialog.reject()  # Esc

        assert not dialog.isVisible()
        assert not dialog.frame_timer.isActive()
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
        dialog._update_frame()
        assert dialog.frame_count == 0

        dialog.flame_kit.camera = ErrorCamera()
        dialog._update_frame()
        assert "boom" in dialog.info_label.text()
    finally:
        dialog.close()
        dialog.deleteLater()
