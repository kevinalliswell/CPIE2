#!/utils/bin/env python
# -*- encoding: utf-8 -*-
"""
工具模块模块
Utils Module

提供日志管理，路径管理，密码管理，数据保存等功能
"""

from importlib import import_module

from .logger import LoggerManager, get_logger, logger_manager
from .path_manager import PathManager

__all__ = [
    'DataSaver',
    'DataExportDialog',
    'LoggerManager',
    'logger_manager',
    'get_logger',
    'PathManager',
    'PasswordManager',
    'Tools',
    'SingleInstance'
]

__version__ = '1.0.0'

_LAZY_IMPORTS = {
    'DataSaver': '.data_saver',
    'DataExportDialog': '.data_saver',
    'PasswordManager': '.password_manager',
    'Tools': '.tools',
    'SingleInstance': '.single_instance',
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
