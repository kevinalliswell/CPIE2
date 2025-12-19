#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
火焰分析仪模块
Flame Analyzer Module

提供火焰图像分析的配置管理、图像处理和UI组件
"""

from .config_manager import FlameAnalyzerConfig
from .flame_processor import (
    FlameImageProcessor,
    FlameAnalysisResult,
    FlameStatistics
)
from .flame_analyzer_widget import FlameAnalyzerWidget

__all__ = [
    'FlameAnalyzerConfig',
    'FlameImageProcessor',
    'FlameAnalysisResult',
    'FlameStatistics',
    'FlameAnalyzerWidget',
]

__version__ = '1.0.0'

