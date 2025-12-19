"""
FlameKit 安装配置文件
支持 pip install -e . (开发模式) 和 pip install . (标准安装)
"""
from setuptools import setup, find_packages
from pathlib import Path

# 读取 README 作为长描述
readme_file = Path(__file__).parent / "flamekit" / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as f:
        long_description = f.read()

# 读取版本号
version = "0.1.0"
init_file = Path(__file__).parent / "flamekit" / "__init__.py"
if init_file.exists():
    with open(init_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

setup(
    name="flamekit",
    version=version,
    description="工业相机火焰长度测试工具包",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CPIE",
    author_email="",
    url="",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    package_data={
        "flamekit": [
            "config_default.json",
            "README.md",
        ],
    },
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
    ],
    extras_require={
        "gui": ["PySide6>=6.5.0"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Image Processing",
    ],
    keywords="camera flame analysis industrial",
)

