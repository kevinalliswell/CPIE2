"""
对话框模块
"""
from importlib import import_module

__all__ = [
    'CalibrationDialog',
    'ExplosionExperimentDialog',
    'IgnitionExperimentDialog',
    'GenerateReportDialog',
    'ImageViewerDialog',
    'ExportDialog',
    'ManualConfirmDialog',
    'LoginDialog',
    'ChangePasswordDialog',
    'ModeSwitchDialog',
    'FlameAnalyzerConfig',
    'FlameAnalyzerWidget',
    'FlameImageProcessor',
    'FlameStatistics'
]

_LAZY_IMPORTS = {
    'CalibrationDialog': '.calibration_dialog',
    'ExplosionExperimentDialog': '.explosion_experiment_dialog',
    'IgnitionExperimentDialog': '.ignition_experiment_dialog',
    'GenerateReportDialog': '.generate_report_dialog',
    'ImageViewerDialog': '.image_viewer_dialog',
    'ExportDialog': '.export_dialog',
    'ManualConfirmDialog': '.manual_confirm_dialog',
    'LoginDialog': '.login_dialog',
    'ChangePasswordDialog': '.change_password_dialog',
    'ModeSwitchDialog': '.mode_switch_dialog',
    'FlameAnalyzerConfig': '.flame_analyzer.config_manager',
    'FlameAnalyzerWidget': '.flame_analyzer.flame_analyzer_widget',
    'FlameImageProcessor': '.flame_analyzer.flame_processor',
    'FlameStatistics': '.flame_analyzer.flame_processor',
}


def __getattr__(name):
    module_name = _LAZY_IMPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
