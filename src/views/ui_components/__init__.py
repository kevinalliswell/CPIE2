#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
火焰分析仪模块
Flame Analyzer Module

提供火焰图像分析的配置管理、图像处理和UI组件
"""


from .sidebar import Sidebar
from .status_bar import StatusBar
from .title_bar import TitleBar

__all__ = [
    'Sidebar',
    'StatusBar',
    'TitleBar'
    ]

__version__ = 'CPIE_1.0.0'
