"""
FlameKit - 工业相机火焰长度测试工具包
# 版本号：0.1.1 增加多参数设置
"""
from importlib import import_module

__version__ = "0.1.1"

__all__ = ["FlameKit", "FlameAnalyzer", "__version__"]

_LAZY_IMPORTS = {
    "FlameKit": ".core",
    "FlameAnalyzer": ".analyzer",
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

