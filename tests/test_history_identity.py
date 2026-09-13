"""History operations keep database identity through Qt sorting and filtering.

Use real widgets and two temporary SQLite databases. Only modal dialogs and
detail-card rendering are replaced; no device controller is constructed.
"""
import csv
import importlib
import logging
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def history(qapp, tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "src"))
    monkeypatch.syspath_prepend(str(root / "modbus_multi_device_package"))
    # Patch both import spellings before importing page/DB modules. All writable
    # paths, including database migrations and deletion of images, stay in tmp.
    for module_name in ("utils.path_manager", "src.utils.path_manager"):
        paths = importlib.import_module(module_name).PathManager
        for kind in ("data", "logs", "exports"):
            directory = tmp_path / kind
            directory.mkdir(exist_ok=True)
            monkeypatch.setattr(
                paths, f"get_{kind}_path",
                staticmethod(lambda name=None, directory=directory:
                             str(directory / name) if name else str(directory)),
            )

    module = importlib.import_module("views.pages.history_query_page")
    ignition_db = importlib.import_module("models.ignition_database").IgnitionDatabase(
        str(tmp_path / "ignition.db")
    )
    explosion_db = importlib.import_module("models.explosion_database").ExplosionDatabase(
        str(tmp_path / "explosion.db")
    )
    ignition_id = ignition_db.start_experiment_session(
        experiment_id="IGN-TEST", experiment_name="Z ignition", sample_names='["Coal I"]'
    )
    explosion_id = explosion_db.start_experiment_session(
        experiment_name="A explosion", sample_name="Coal E"
    )
    assert ignition_id == explosion_id == 1
    ignition_db.record_ignition_detection(ignition_id, 1, 421.5)
    explosion_db.add_test_round(explosion_id, 1, 123.5, None)
    explosion_db.finalize_experiment(explosion_id)

    class DetailCard(QWidget):
        data = None

        def load_experiment_detail(self, session_id, data, **kwargs):
            self.data = data

        def show_empty_state(self, message):
            self.data = None

    monkeypatch.setattr(module, "IgnitionDetailCard", DetailCard)
    monkeypatch.setattr(module, "ExplosionDetailCard", DetailCard)
    for method in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, method, lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    password = importlib.import_module("views.dialogs.password_confirm_dialog")
    monkeypatch.setattr(password.PasswordConfirmDialog, "exec", lambda self: QDialog.Accepted)

    page = module.HistoryQueryPage.__new__(module.HistoryQueryPage)
    QWidget.__init__(page)
    page.logger = logging.getLogger("test.history")
    page.config = {}
    page.current_experiment = None
    page.selected_experiment_type = None
    page.date_filter_start = page.date_filter_end = None
    page.ignition_db, page.explosion_db = ignition_db, explosion_db
    page.init_ui()
    ignition = ignition_db.get_all_experiment_sessions()[0]
    explosion = explosion_db.get_all_experiment_sessions()[0]
    ignition.update(experiment_type="着火点", start_time="2026-09-12 12:00:00", end_time=None)
    explosion.update(experiment_type="爆炸性", end_time="2026-09-13 12:00:00")
    page.experiments_data = [ignition, explosion]
    page.update_table(page.experiments_data)
    page.table.sortItems(3, Qt.AscendingOrder)

    yield SimpleNamespace(page=page, module=module, ignition=ignition, explosion=explosion,
                          ignition_db=ignition_db, explosion_db=explosion_db, tmp=tmp_path)
    page.close()
    page.deleteLater()
    qapp.processEvents()
    ignition_db.close()
    explosion_db.close()


def select_type(page, display_type):
    row = next(row for row in range(page.table.rowCount())
               if page.table.item(row, 0).text() == display_type)
    page.table.selectRow(row)
    return row


@pytest.mark.parametrize("display_type", ["爆炸性", "着火点"])
def test_sorted_selection_loads_matching_details_and_report(history, monkeypatch, display_type):
    page = history.page
    captured = {}

    class ReportDialog:
        def __init__(self, session_id, exp_type, data, **kwargs):
            captured.update(session_id=session_id, exp_type=exp_type, data=data, **kwargs)

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr(history.module, "GenerateReportDialog", ReportDialog)
    select_type(page, display_type)
    assert page.current_experiment["experiment_type"] == display_type
    page.on_generate_report()
    expected = history.explosion if display_type == "爆炸性" else history.ignition
    assert captured["data"]["experiment_name"] == expected["experiment_name"]
    if display_type == "爆炸性":
        assert page.explosion_detail_card.data["tests"][0]["flame_length_mm"] == 123.5
        assert captured["data"]["tests"][0]["flame_length_mm"] == 123.5
        assert captured["explosion_db"] is history.explosion_db
    else:
        assert page.ignition_detail_card.data["sample_data"][0]["ignition_temperature"] == 421.5
        assert captured["data"]["sample_data"][0]["ignition_temperature"] == 421.5
        assert captured["ignition_db"] is history.ignition_db


@pytest.mark.parametrize("order", [Qt.AscendingOrder, Qt.DescendingOrder])
def test_type_and_date_filters_follow_records_after_sort(history, order):
    page = history.page
    page.selected_experiment_type = "爆炸性"
    page.date_filter_start = date(2026, 9, 13)
    page.filter_experiments()
    page.table.sortItems(3, order)
    visible = [page.table.item(row, 3).text() for row in range(page.table.rowCount())
               if not page.table.isRowHidden(row)]
    assert visible == ["A explosion"]


def test_hiding_selected_record_clears_detail_and_preserves_filter_on_refresh(history):
    page = history.page
    select_type(page, "爆炸性")
    page.search_edit.setText("Z ignition")
    assert page.current_experiment is None
    assert not page.table.selectedItems()
    page.update_table(page.experiments_data)
    visible = [page.table.item(row, 3).text() for row in range(page.table.rowCount())
               if not page.table.isRowHidden(row)]
    assert visible == ["Z ignition"]


@pytest.mark.parametrize("display_type", ["爆炸性", "着火点"])
def test_delete_sorted_record_only_removes_matching_database_session(history, display_type):
    page = history.page
    select_type(page, display_type)
    page.delete_experiment()
    ignition_rows = history.ignition_db.get_all_experiment_sessions()
    explosion_rows = history.explosion_db.get_all_experiment_sessions()
    assert len(ignition_rows) == (0 if display_type == "着火点" else 1)
    assert len(explosion_rows) == (0 if display_type == "爆炸性" else 1)
    assert len(page.experiments_data) == page.table.rowCount() == 1
    assert page.experiments_data[0]["experiment_type"] != display_type
    assert page.table.item(0, 0).text() != display_type
    assert page.current_experiment is None


@pytest.mark.parametrize("exp_type,display_type", [("explosion", "爆炸性"), ("ignition", "着火点")])
def test_export_dialog_uses_sorted_selection_identity(history, monkeypatch, exp_type, display_type):
    captured = {}

    class ExportDialog:
        def __init__(self, ids, kind, parent):
            captured.update(ids=ids, kind=kind)
            self.export_confirmed = SimpleNamespace(connect=lambda callback: None)

        def exec(self):
            pass

    monkeypatch.setattr(history.module, "ExportDialog", ExportDialog)
    select_type(history.page, display_type)
    history.page.export_data()
    assert captured == {"ids": [1], "kind": exp_type}
    # With no selection, export the visible filtered list rather than hidden
    # records of another experiment type with colliding IDs.
    history.page.table.clearSelection()
    history.page.on_type_filter_changed(display_type)
    captured.clear()
    history.page.export_data()
    assert captured == {"ids": [1], "kind": exp_type}


@pytest.mark.parametrize("exp_type", ["explosion", "ignition"])
@pytest.mark.parametrize("file_format", ["csv", "excel"])
def test_exports_match_type_when_both_databases_have_id_one(history, exp_type, file_format):
    page = history.page
    # Put the other database's id=1 first, reproducing both collision directions.
    page.experiments_data = ([history.ignition, history.explosion] if exp_type == "explosion"
                             else [history.explosion, history.ignition])
    page.update_table(page.experiments_data)
    path = history.tmp / ("records.csv" if file_format == "csv" else "records.xlsx")
    exporter = page._export_to_csv if file_format == "csv" else page._export_to_excel
    assert exporter(str(path), [1], exp_type, True, True, True, True)
    if file_format == "csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
    else:
        import openpyxl
        workbook = openpyxl.load_workbook(path)
        rows = list(workbook["实验数据"].values)
        sheet = "测试轮次详情" if exp_type == "explosion" else "样品详情"
        detail_rows = list(workbook[sheet].values)
        assert len(detail_rows) == 2
        assert detail_rows[1][1] == ("A explosion" if exp_type == "explosion" else "Z ignition")
        assert detail_rows[1][3 if exp_type == "explosion" else 4] == (
            123.5 if exp_type == "explosion" else "421.5")
        workbook.close()
    assert len(rows) == 2
    expected_identity = ['A explosion', '爆炸性'] if exp_type == 'explosion' else ['Z ignition', '着火点']
    assert list(rows[1][2:4]) == expected_identity
    assert float(rows[1][11]) == (123.5 if exp_type == "explosion" else 421.5)


@pytest.mark.parametrize("file_format", ["csv", "excel"])
def test_missing_typed_record_does_not_report_successful_export(history, file_format):
    page = history.page
    page.experiments_data = [history.ignition]
    page.update_table(page.experiments_data)
    path = history.tmp / ("missing.csv" if file_format == "csv" else "missing.xlsx")
    exporter = page._export_to_csv if file_format == "csv" else page._export_to_excel
    assert not exporter(str(path), [1], "explosion", True, True)
    assert not path.exists()
