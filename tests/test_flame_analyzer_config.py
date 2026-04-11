#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pytest coverage for flame analyzer configuration handling."""

import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

pytest.importorskip("cv2")

from views.dialogs.flame_analyzer.config_manager import FlameAnalyzerConfig
from views.dialogs.flame_analyzer.flame_processor import FlameImageProcessor


@pytest.fixture
def config_file(tmp_path):
    config_path = tmp_path / "flame_analyzer_config.yaml"
    config_data = {
        "image_processing": {
            "flame_threshold": 150,
            "mm_per_pixel": 0.816082,
        },
        "paths": {
            "history_csv": "data/exp_explosion/history_explosion.csv",
            "exp_data_json": "data/exp_explosion/explosion_experiment_data.json",
            "temp_folder": "data/temp_captures",
            "flame_output_folder": "data/flame_results",
            "max_flame_save_folder": "data/max_flame_images",
        },
        "image_formats": [".jpg", ".jpeg", ".png", ".bmp"],
        "ui": {
            "window_title": "火焰图像分析",
            "progress_update_interval": 10,
            "max_display_failed_files": 5,
        },
        "opencv": {
            "font": "FONT_HERSHEY_SIMPLEX",
            "font_scale": 0.5,
            "text_color": [0, 255, 0],
            "text_thickness": 2,
            "bbox_color": [0, 255, 0],
            "bbox_thickness": 1,
        },
        "performance": {
            "stream_processing": True,
            "batch_size": 50,
        },
        "logging": {
            "enable": True,
            "level": "INFO",
            "file": "logs/flame_analyzer.log",
        },
    }
    config_path.write_text(yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return config_path


@pytest.fixture
def config(config_file):
    return FlameAnalyzerConfig(config_path=str(config_file))


def test_config_initialization_reads_expected_values(config, config_file):
    assert config.config_path == config_file
    assert config.flame_threshold == 150
    assert abs(config.mm_per_pixel - 0.816082) < 1e-9
    assert config.image_formats == (".jpg", ".jpeg", ".png", ".bmp")
    assert config.window_title == "火焰图像分析"
    assert config.progress_update_interval == 10
    assert config.max_display_failed_files == 5
    assert config.stream_processing is True
    assert config.batch_size == 50
    assert config.logging_enabled is True
    assert config.log_level == "INFO"


def test_config_paths_resolve_against_project_root(config):
    assert config.history_csv_path == PROJECT_ROOT / "data/exp_explosion/history_explosion.csv"
    assert config.exp_data_json_path == PROJECT_ROOT / "data/exp_explosion/explosion_experiment_data.json"
    assert config.temp_folder == PROJECT_ROOT / "data/temp_captures"
    assert config.flame_output_folder == PROJECT_ROOT / "data/flame_results"
    assert config.max_flame_save_folder == PROJECT_ROOT / "data/max_flame_images"
    assert config.log_file == PROJECT_ROOT / "logs/flame_analyzer.log"


def test_processor_receives_same_config_instance(config):
    processor = FlameImageProcessor(config)

    assert processor.config is config
    assert processor.config.flame_threshold == 150
    assert abs(processor.config.mm_per_pixel - 0.816082) < 1e-9


def test_config_can_be_updated_saved_and_reloaded(config_file):
    config = FlameAnalyzerConfig(config_path=str(config_file))
    config.update_config("image_processing.flame_threshold", 200)
    config.update_config("ui.window_title", "自定义标题")
    config.save_config()

    reloaded = FlameAnalyzerConfig(config_path=str(config_file))
    assert reloaded.flame_threshold == 200
    assert reloaded.window_title == "自定义标题"


def test_invalid_config_raises_validation_error(tmp_path):
    invalid_config_path = tmp_path / "invalid_flame_config.yaml"
    invalid_config_path.write_text(
        yaml.safe_dump(
            {
                "image_processing": {
                    "flame_threshold": 300,
                    "mm_per_pixel": -0.1,
                },
                "paths": {},
                "image_formats": [],
                "ui": {},
                "opencv": {},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        FlameAnalyzerConfig(config_path=str(invalid_config_path))
