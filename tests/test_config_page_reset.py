#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置页"重置"必须原地更新共享的配置字典（含嵌套子字典），否则实验页面读不到之后的修改"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


def test_update_dict_in_place_keeps_nested_identity():
    from views.pages.config_page import ConfigPage

    config = {
        "explosion_experiment": {"test-rounds": {"max-rounds": 2}, "relay_mapping": {"a": 1}},
        "ui": {"update_interval": 500},
        "stale": {"x": 1},
    }
    explosion_ref = config["explosion_experiment"]
    rounds_ref = explosion_ref["test-rounds"]
    ui_ref = config["ui"]

    fresh = {
        "explosion_experiment": {"test-rounds": {"max-rounds": 10, "phase-rounds": 5}},
        "ui": {"update_interval": 250},
        "ignition_experiment": {"collect_start_temperature": 200.0},
    }
    ConfigPage._update_dict_in_place(config, fresh)

    assert config["explosion_experiment"] is explosion_ref
    assert config["explosion_experiment"]["test-rounds"] is rounds_ref
    assert config["ui"] is ui_ref
    assert rounds_ref == {"max-rounds": 10, "phase-rounds": 5}
    assert "relay_mapping" not in explosion_ref
    assert ui_ref["update_interval"] == 250
    assert "stale" not in config
    assert config["ignition_experiment"] == {"collect_start_temperature": 200.0}
