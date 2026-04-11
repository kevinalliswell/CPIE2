#!/models/bin/env python
# -*- encoding: utf-8 -*-
"""
模型模块
Models Module

提供数据库管理等功能
"""

from importlib import import_module

from .experiment_states import ExplosionExperimentState, IgnitionExperimentState

__all__ = [
    'IgnitionDatabase',
    'ExplosionDatabase',
    'ExplosionExperiment',
    'IgnitionExperiment',
    'DataHandler',
    'ExplosionExperimentState',
    'IgnitionExperimentState',
    'UserManager',
    'User'
]

__version__ = '1.0.0'

_LAZY_IMPORTS = {
    'IgnitionDatabase': '.ignition_database',
    'ExplosionDatabase': '.explosion_database',
    'ExplosionExperiment': '.explosion_experiment',
    'IgnitionExperiment': '.ignition_experiment',
    'DataHandler': '.data_handler',
    'UserManager': '.user_manager',
    'User': '.user_manager',
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
