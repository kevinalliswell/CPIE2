#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据页面：表格排序后选中/删除必须作用于高亮的那条记录

此前页面用视图行号直接索引 experiments_data，用户点击表头排序后行号与列表下标错位，
详情卡片显示、导出和删除都会作用到另一条记录（删除会连带删掉别的实验的图片）。
"""

import os
import sys
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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qapp, tmp_path, monkeypatch):
    from utils import path_manager as pm

    # 数据目录重定向到临时目录（页面会创建两个数据库）
    monkeypatch.setattr(pm.PathManager, "get_project_root", staticmethod(lambda: str(tmp_path)))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: QMessageBox.Ok))

    from views.pages.history_query_page import HistoryQueryPage

    created = HistoryQueryPage()

    # 交错插入着火点/爆炸性会话，使两种类型在按类型排序后位置发生变化
    ids = []
    for i in range(3):
        ign = created.ignition_db.start_experiment_session(
            experiment_id=f"IGN-{i}", experiment_name=f"ign{i}", sample_names="[]"
        )
        exp = created.explosion_db.start_experiment_session(
            experiment_id=f"EXP-{i}", experiment_name=f"exp{i}", sample_name="s"
        )
        ids.append(("着火点", ign))
        ids.append(("爆炸性", exp))
    created.load_experiments()
    try:
        yield created
    finally:
        created.ignition_controller.cleanup()
        created.explosion_controller.cleanup()
        created.deleteLater()


def _visible_identity(page, row):
    return page.table.item(row, 0).text(), int(page.table.item(row, 1).text())


def test_selection_follows_visible_row_after_sorting(page):
    assert page.table.rowCount() == 6
    assert page.table.isSortingEnabled()

    # 模拟用户点击"实验类型"表头排序，再按会话ID升序排序
    for column, order in ((0, Qt.AscendingOrder), (0, Qt.DescendingOrder), (1, Qt.AscendingOrder)):
        page.table.sortItems(column, order)
        for row in range(page.table.rowCount()):
            page.table.clearSelection()
            page.table.selectRow(row)
            exp_type, session_id = _visible_identity(page, row)
            assert page.current_experiment is not None
            assert (page.current_experiment["experiment_type"], page.current_experiment["id"]) == (exp_type, session_id)


def test_delete_removes_the_highlighted_record(page, monkeypatch):
    from views.dialogs.password_confirm_dialog import PasswordConfirmDialog

    monkeypatch.setattr(PasswordConfirmDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))

    page.table.sortItems(0, Qt.DescendingOrder)  # 类型列降序：与 experiments_data 顺序不同
    target_row = 2
    page.table.clearSelection()
    page.table.selectRow(target_row)
    exp_type, session_id = _visible_identity(page, target_row)
    remaining_before = {(e["experiment_type"], e["id"]) for e in page.experiments_data}
    assert (exp_type, session_id) in remaining_before

    page.delete_experiment()

    db = page.ignition_db if exp_type == "着火点" else page.explosion_db
    assert all(s["id"] != session_id for s in db.get_all_experiment_sessions())
    remaining_after = {(e["experiment_type"], e["id"]) for e in page.experiments_data}
    assert remaining_after == remaining_before - {(exp_type, session_id)}
    assert page.table.rowCount() == 5
    # 其余记录都还在数据库中
    for other_type, other_id in remaining_after:
        other_db = page.ignition_db if other_type == "着火点" else page.explosion_db
        assert any(s["id"] == other_id for s in other_db.get_all_experiment_sessions())
