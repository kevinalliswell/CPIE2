"""
FlameKit.capture_one_second 的采集时长/目录参数测试

采集时长来自显式参数或构造时的 capture_duration，采集目录可由调用方指定（应用层传入
data/camera_captures 的绝对路径，避免写到当前工作目录）。
"""

import pytest

from flamekit.core import FlameKit


class FakeCamera:
    def __init__(self, capture_duration=None):
        self.capture_duration = capture_duration
        self.calls = []

    def capture_sequence(self, save_dir, duration=1.0):
        self.calls.append((save_dir, duration))
        return ([f"{save_dir}/frame_000.jpg"], 1)


class FakeConfig:
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir

    def get(self, key, default=None):
        return self.temp_dir if key == "paths.temp_dir" else default


@pytest.fixture
def kit(tmp_path):
    """绕过硬件初始化，直接注入假相机"""
    instance = FlameKit.__new__(FlameKit)
    instance.camera = FakeCamera(capture_duration=2.0)
    instance.analyzer = None
    instance.config = FakeConfig(str(tmp_path / "config_temp"))
    instance._last_image_paths = []
    instance._last_analysis = None
    instance._last_max_image_path = ""
    instance._initialized = True
    return instance


def test_duration_defaults_to_camera_setting(kit, tmp_path):
    target = tmp_path / "captures"

    images, count = kit.capture_one_second(temp_dir=str(target))

    assert kit.camera.calls == [(str(target), 2.0)]
    assert count == 1 and images == kit._last_image_paths
    assert target.is_dir()


def test_explicit_duration_and_clamping(kit, tmp_path):
    target = str(tmp_path / "captures")

    kit.capture_one_second(temp_dir=target, duration=0.5)
    kit.capture_one_second(temp_dir=target, duration=0.01)  # 下限 0.1 s
    kit.capture_one_second(temp_dir=target, duration="bad")  # 非法值回退 1.0 s

    assert [duration for _, duration in kit.camera.calls] == [0.5, 0.1, 1.0]


def test_duration_falls_back_to_one_second_without_camera_setting(kit, tmp_path):
    kit.camera.capture_duration = None

    kit.capture_one_second(temp_dir=str(tmp_path / "captures"))

    assert kit.camera.calls[0][1] == 1.0


def test_default_directory_comes_from_config_and_is_cleared(kit, tmp_path):
    config_dir = tmp_path / "config_temp"
    config_dir.mkdir()
    stale = config_dir / "old.jpg"
    stale.write_bytes(b"x")

    kit.capture_one_second()

    assert kit.camera.calls == [(str(config_dir), 2.0)]
    assert not stale.exists()


def test_capture_requires_initialized_camera(kit):
    kit._initialized = False
    kit.camera.initialize = lambda: False

    assert kit.capture_one_second(temp_dir="unused") == ([], 0)
    assert kit.camera.calls == []
