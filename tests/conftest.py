"""
pytest 公共配置

- 把项目根目录、src/ 以及两个本地包目录加入 sys.path，使 `pytest tests/` 可直接在仓库根目录运行
- 默认使用 offscreen 平台插件，保证 GUI 测试可以在无显示器环境运行
- 将 tests/ 目录下的手工脚本（需要交互、真实数据库或硬件）排除在自动收集之外
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (
    PROJECT_ROOT / "modbus_multi_device_package",
    PROJECT_ROOT / "flame_package",
    PROJECT_ROOT / "src",
    PROJECT_ROOT,
):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 手工/交互脚本：不是 pytest 用例，且会读写真实的 data/ 数据库或打开 GUI 事件循环
collect_ignore = [
    "migrate_database.py",
    "test_database_system.py",
    "test_insert_data.py",
    "test_ignition_button_states.py",
    "test_ignition_temperature_plot.py",
    "test_tangent_analysis_dialog.py",
    "test_tangent_analysis_from_db.py",
    "test_tangent_direct.py",
    "test_tangent_method_visualization.py",
]


@pytest.fixture(scope="session")
def qapp():
    """会话级 QApplication，供需要 Qt 控件的测试使用"""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
