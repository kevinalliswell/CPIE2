"""
FlameKit - 工业相机火焰长度测试工具包
# 版本号：0.1.1 增加多参数设置
"""
__version__ = "0.1.1"

from .core import FlameKit
from .analyzer import FlameAnalyzer

__all__ = ["FlameKit", "FlameAnalyzer", "__version__"]

