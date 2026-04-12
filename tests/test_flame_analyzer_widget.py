#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal, collection-safe pytest coverage for FlameAnalyzerWidget."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def widget_module(qapp):
    from views.dialogs.flame_analyzer import flame_analyzer_widget as module

    return module


@pytest.fixture
def config_module(qapp):
    from views.dialogs.flame_analyzer import config_manager as module

    return module


@pytest.fixture
def processor_module(qapp):
    from views.dialogs.flame_analyzer import flame_processor as module

    return module


@pytest.fixture
def temp_image_dir(tmp_path):
    np = pytest.importorskip("numpy")
    cv2 = pytest.importorskip("cv2")

    image_dir = tmp_path / "images"
    image_dir.mkdir()

    image = np.ones((100, 120, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (30, 20), (90, 80), (0, 0, 255), -1)
    cv2.imwrite(str(image_dir / "frame_001.jpg"), image)
    cv2.imwrite(str(image_dir / "frame_002.jpg"), image)
    return image_dir


@pytest.fixture
def widget(qapp, widget_module, config_module, temp_image_dir, monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QTimer, "singleShot", staticmethod(lambda _delay, callback: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))

    config = config_module.FlameAnalyzerConfig()
    created_widget = widget_module.FlameAnalyzerWidget(
        input_folder=str(temp_image_dir),
        config=config,
    )
    try:
        yield created_widget
    finally:
        created_widget.close()
        created_widget.deleteLater()


def test_widget_initializes_core_components(widget, temp_image_dir):
    assert widget.input_folder == str(temp_image_dir)
    assert widget.processor is not None
    assert widget.analysis_completed is False
    assert widget.is_playing is False
    assert widget.play_speed == 1.0
    assert widget.windowTitle() == widget.config.window_title
    assert widget.list_widget is not None
    assert widget.lb_img_viewer is not None
    assert widget.play_pause_button is not None
    assert widget.speed_slider is not None


def test_speed_slider_updates_playback_speed(widget):
    expected_speeds = {
        1: 0.5,
        2: 1.0,
        3: 2.0,
        4: 4.0,
        5: 8.0,
        6: 16.0,
    }

    for slider_value, expected_speed in expected_speeds.items():
        widget.on_speed_changed(slider_value)
        assert widget.play_speed == expected_speed
        assert widget.speed_value_label.text() == f"{expected_speed:.1f}x"


def test_navigation_buttons_change_selected_row(widget):
    widget.list_widget.clear()
    for item in ["frame_001.jpg: 100 mm", "frame_002.jpg: 110 mm", "frame_003.jpg: 120 mm"]:
        widget.list_widget.addItem(item)

    widget.list_widget.setCurrentRow(1)
    widget.on_prev_button_clicked()
    assert widget.list_widget.currentRow() == 0

    widget.on_next_button_clicked()
    assert widget.list_widget.currentRow() == 1

    widget.list_widget.setCurrentRow(0)
    widget.on_prev_button_clicked()
    assert widget.list_widget.currentRow() == 0

    widget.list_widget.setCurrentRow(widget.list_widget.count() - 1)
    widget.on_next_button_clicked()
    assert widget.list_widget.currentRow() == widget.list_widget.count() - 1


def test_play_pause_toggles_when_results_are_available(widget, processor_module):
    widget.list_widget.clear()
    widget.analysis_results = [
        processor_module.FlameAnalysisResult(
            filename="frame_001.jpg",
            flame_size_mm=100,
            flame_region=(0, 0, 20, 20),
            success=True,
        ),
        processor_module.FlameAnalysisResult(
            filename="frame_002.jpg",
            flame_size_mm=120,
            flame_region=(0, 0, 24, 20),
            success=True,
        ),
    ]
    widget.analysis_completed = True

    for result in widget.analysis_results:
        widget.list_widget.addItem(f"{result.filename}: {result.flame_size_mm} mm")

    widget.on_play_pause_clicked()
    assert widget.is_playing is True
    assert "暂停" in widget.play_pause_button.text()

    widget.on_play_pause_clicked()
    assert widget.is_playing is False
    assert "播放" in widget.play_pause_button.text()


def test_processor_injection_is_supported(qapp, widget_module, config_module, processor_module, temp_image_dir, monkeypatch):
    from PySide6.QtCore import QTimer

    monkeypatch.setattr(QTimer, "singleShot", staticmethod(lambda _delay, callback: None))
    mock_processor = Mock(spec=processor_module.FlameImageProcessor)

    widget = widget_module.FlameAnalyzerWidget(
        input_folder=str(temp_image_dir),
        config=config_module.FlameAnalyzerConfig(),
        processor=mock_processor,
    )
    try:
        assert widget.processor is mock_processor
    finally:
        widget.close()
        widget.deleteLater()
