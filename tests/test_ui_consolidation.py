"""UI and resource regressions retained from the parallel closeout reviews."""
import copy
import io
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


@pytest.fixture
def quiet_dialogs(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtCore import QTimer
    monkeypatch.setattr(QTimer, 'singleShot', lambda *args: None)
    for name in ('question', 'warning', 'information', 'critical'):
        monkeypatch.setattr(QMessageBox, name, lambda *args, **kwargs: QMessageBox.Yes)


@pytest.mark.parametrize('separate_ui', [False, True])
def test_reset_keeps_live_nested_config_references(qapp, quiet_dialogs, separate_ui):
    from utils.path_manager import PathManager
    from views.pages.config_page import ConfigPage

    path = Path(PathManager.get_config_path('experiment_config.yaml'))
    saved = yaml.safe_load(path.read_text(encoding='utf-8'))
    config = copy.deepcopy(saved)
    ui = copy.deepcopy(config['ui']) if separate_ui else config['ui']
    page = ConfigPage(config, ui, str(path))
    ignition = config['ignition_experiment']
    serial = ignition['serial']
    root_ui = config['ui']
    chart = ui['chart']
    serial['port'] = 'unsaved'
    serial['obsolete'] = True
    ui['update_interval'] = 1700
    chart['max_points'] = 100
    try:
        page._on_reset()
        assert page.config is config
        assert page.config['ignition_experiment'] is ignition
        assert ignition['serial'] is serial
        assert serial == saved['ignition_experiment']['serial']
        assert page.config['ui'] is root_ui
        assert page.ui_config is ui and ui['chart'] is chart
        assert ui == saved['ui']
        page.config_widgets['ui_update_interval'].setValue(800)
        page._on_apply()
        assert ui['update_interval'] == 800
    finally:
        page.close()
        page.deleteLater()


@pytest.fixture
def analyzer(qapp, quiet_dialogs, tmp_path, monkeypatch):
    from views.dialogs.flame_analyzer.flame_analyzer_widget import FlameAnalyzerWidget

    widget = FlameAnalyzerWidget(str(tmp_path))
    widget.output_folder = str(tmp_path)
    monkeypatch.setattr(widget, '_copy_max_flame_image', lambda *args: None)
    yield widget
    widget.analysis_completed = True
    widget.close()
    widget.deleteLater()


def test_maximum_result_selects_its_row_after_failed_images(analyzer):
    from views.dialogs.flame_analyzer.flame_processor import FlameAnalysisResult
    analyzer.analysis_results = [
        FlameAnalysisResult('failed.jpg', 0, (0, 0, 0, 0), False),
        FlameAnalysisResult('small.jpg', 10, (0, 0, 1, 1)),
        FlameAnalysisResult('maximum.jpg', 40, (0, 0, 1, 1)),
    ]
    analyzer.statistics = analyzer.processor.calculate_statistics(analyzer.analysis_results)
    analyzer._update_ui_with_results()
    assert analyzer.list_widget.currentRow() == 2
    assert analyzer.exp_results['max_flame_image_path'].endswith('maximum.jpg')


@pytest.mark.parametrize('method', ['reject', 'escape'])
def test_dismissing_completed_analysis_emits_results(analyzer, qapp, method):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    results = []
    analyzer.analysis_completed = True
    analyzer.exp_results = {'max_flame_size': 40}
    analyzer.window_closed.connect(results.append)
    analyzer.show()
    qapp.processEvents()
    if method == 'reject':
        analyzer.reject()
    else:
        QTest.keyClick(analyzer, Qt.Key_Escape)
    assert results == [{'max_flame_size': 40}]
    assert not analyzer.isVisible()


@pytest.mark.parametrize('content', [None, '{"version": "9.9"}', '{broken json'])
def test_software_info_fallback_contains_every_page_field(content):
    from utils.path_manager import PathManager
    from utils.tools import Tools
    path = Path(PathManager.get_config_path('software.info'))
    if content is None:
        path.unlink()
    else:
        path.write_text(content, encoding='utf-8')
    info = Tools.load_software_info()
    assert {'version', 'author', 'description', 'release_date', 'copyright',
            'contact', 'website', 'build_date', 'python_version', 'platforms'} <= set(info)
    if content and '9.9' in content:
        assert info['version'] == '9.9'


def test_home_logo_loads_outside_project_working_directory(qapp):
    from PySide6.QtWidgets import QLabel
    from views.pages.home_page import HomePage
    page = HomePage()
    try:
        assert any(label.pixmap() is not None and not label.pixmap().isNull()
                   for label in page.findChildren(QLabel))
    finally:
        page.close()
        page.deleteLater()


@pytest.mark.parametrize('component', ['modbus', 'flame'])
def test_repeated_log_setup_deduplicates_own_handlers_and_keeps_external(component, tmp_path):
    name = 'ModbusManager' if component == 'modbus' else 'FlameImageProcessor'
    logger = logging.getLogger(name)
    previous = logger.handlers[:]
    for handler in previous:
        logger.removeHandler(handler)
    stream = io.StringIO()
    class ExternalHandler(logging.StreamHandler):
        closed_by_component = False

        def close(self):
            self.closed_by_component = True
            super().close()

    external = ExternalHandler(stream)
    logger.addHandler(external)
    try:
        if component == 'modbus':
            from modbus_multi_device import ModbusDeviceManager
            config = {'logging': {'save_to_file': True, 'log_dir': str(tmp_path)}}
            first = ModbusDeviceManager(config_dict=config)
            second = ModbusDeviceManager(config_dict=config)
        else:
            from views.dialogs.flame_analyzer.flame_processor import FlameImageProcessor
            config = SimpleNamespace(logging_enabled=True, log_level='INFO', log_file=tmp_path / 'flame.log')
            first = FlameImageProcessor(config)
            second = FlameImageProcessor(config)
        assert first.logger is second.logger
        assert external in logger.handlers and not external.closed_by_component
        assert len(logger.handlers) == 3  # external, one console, one file
        logger.warning('single-event-marker')
        for handler in logger.handlers:
            handler.flush()
        assert stream.getvalue().count('single-event-marker') == 1
        assert sum(p.read_text(encoding='utf-8').count('single-event-marker')
                   for p in tmp_path.glob('*.log')) == 1
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        for handler in previous:
            logger.addHandler(handler)


@pytest.mark.parametrize('interval, expected', [(1200, 1200), (None, 500), (-1, 500), ('invalid', 500)])
def test_secondary_display_uses_top_level_ui_refresh_interval(qapp, quiet_dialogs, interval, expected):
    from views.secondary_display_window import SecondaryDisplayWindow
    controller = SimpleNamespace(manager=None, config={})
    window = SecondaryDisplayWindow(controller, controller, ui_config={'update_interval': interval})
    try:
        assert window.explosion_panel.update_timer.interval() == expected
        assert window.ignition_panel.update_timer.interval() == expected
    finally:
        window.close()
        window.deleteLater()


def test_main_window_passes_its_ui_config_to_secondary_display(qapp, quiet_dialogs):
    from views.main_window import MainWindow
    controller = SimpleNamespace(manager=None, config={})
    window = SimpleNamespace(
        secondary_display_window=None, ui_config={'update_interval': 1300},
        _get_explosion_controller=lambda: controller,
        _get_ignition_controller=lambda: controller,
        _on_secondary_display_closed=lambda: None,
    )
    try:
        MainWindow._open_secondary_display(window)
        assert window.secondary_display_window.explosion_panel.update_timer.interval() == 1300
        assert window.secondary_display_window.ignition_panel.update_timer.interval() == 1300
    finally:
        if window.secondary_display_window is not None:
            window.secondary_display_window.close()
            window.secondary_display_window.deleteLater()
