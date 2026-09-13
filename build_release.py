#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPIE 1.1 应用打包发布脚本 (优化版)
支持 Windows、macOS 和 Linux 平台
使用 PyInstaller 进行打包
支持本地包和完整依赖检测
"""

import sys
import shutil
import subprocess
import platform
import argparse
import hashlib
import importlib.metadata
import re
from pathlib import Path
import zipfile
import json
from datetime import datetime


def _configure_console_streams():
    """Avoid UnicodeEncodeError on non-UTF-8 consoles such as Windows cp1252."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue

        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            # Keep the original stream settings if reconfiguration is unsupported.
            pass


_configure_console_streams()


class CPIEBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.src_dir = self.project_root / "src"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.release_dir = self.project_root / "release"
        
        # 本地包路径
        self.local_packages = {
            "modbus_multi_device": self.project_root / "modbus_multi_device_package"
        }
        
        # 应用信息
        # 从配置文件 configs/software.info 读取应用信息
        software_info_file = self.project_root / "configs" / "software.info"
        if not software_info_file.exists():
            raise FileNotFoundError(f"未找到配置文件: {software_info_file}")
        with open(software_info_file, "r", encoding="utf-8") as f:
            info = json.load(f)
        self.app_name = info.get("name", "CPIE") if "name" in info else "CPIE"
        self.app_version = info.get("version", "1.0.0")
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", self.app_version):
            raise ValueError("软件版本必须是 X.Y.Z 或 X.Y.Z-prerelease")
        self.app_description = info.get("description", "")
        self.main_script = self.src_dir / "app.py"
        
        # 平台信息
        self.platform = platform.system().lower()
        self.arch = platform.machine().lower()
        
        print("=" * 60)
        print("CPIE Builder 初始化完成")
        print("=" * 60)
        print(f"项目根目录: {self.project_root}")
        print(f"目标平台: {self.platform} ({self.arch})")
        print(f"应用版本: {self.app_version}")
        print(f"Python 版本: {sys.version}")
        print("=" * 60)

    def check_dependencies(self):
        """检查构建依赖"""
        print("\n检查构建依赖...")
        print("-" * 60)
        
        # 检查 PyInstaller
        try:
            import PyInstaller
            print(f"✓ PyInstaller 已安装: {PyInstaller.__version__}")
        except ImportError:
            print("✗ 缺少 PyInstaller，请先安装 requirements-dev.txt")
            return False
        
        # 检查主要依赖 (包括新增的包)
        required_packages = [
            # UI 框架
            ("PySide6", "PySide6.QtCore"),
            ("PySide6", "PySide6.QtWidgets"),
            ("PySide6", "PySide6.QtGui"),
            ("PySide6", "PySide6.QtCharts"),
            
            # 图表和数据可视化
            ("pyqtgraph", "pyqtgraph"),
            ("matplotlib", "matplotlib"),
            ("matplotlib", "matplotlib.pyplot"),
            
            # 数据处理
            ("numpy", "numpy"),
            ("scipy", "scipy"),
            ("opencv-python", "cv2"),
            
            # 串口通信
            ("pyserial", "serial"),
            ("pymodbus", "pymodbus"),
            
            # 文档处理
            ("python-docx", "docx"),
            ("reportlab", "reportlab"),
            ("lxml", "lxml"),
            ("openpyxl", "openpyxl"),
            
            # 系统和工具
            ("PyYAML", "yaml"),
            
            # 本地包
            ("flamekit", "flamekit"),
            ("modbus_multi_device", "modbus_multi_device"),
        ]
        
        missing_packages = []
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                print(f"✓ {package_name:25s} 已安装")
            except ImportError:
                print(f"✗ {package_name:25s} 未安装")
                missing_packages.append(package_name)
        
        if missing_packages:
            print("\n" + "=" * 60)
            print("缺少以下依赖包:")
            for pkg in missing_packages:
                print(f"  - {pkg}")
            print("\n建议操作:")
            print("1. 安装标准包: pip install -r requirements.txt")
            print("2. 安装本地包:")
            for pkg_name, pkg_path in self.local_packages.items():
                if pkg_path.exists():
                    print(f"   pip install -e {pkg_path}")
            print("=" * 60)
            return False
        
        print("-" * 60)
        print("✓ 所有依赖检查通过")
        return True

    def check_local_packages(self):
        """检查本地包是否存在并已安装"""
        print("\n检查本地包...")
        print("-" * 60)
        
        all_ok = True
        for pkg_name, pkg_path in self.local_packages.items():
            if not pkg_path.exists():
                print(f"✗ {pkg_name}: 目录不存在 - {pkg_path}")
                all_ok = False
            else:
                print(f"✓ {pkg_name}: 目录存在 - {pkg_path}")
                
                # 检查是否已安装
                try:
                    __import__(pkg_name)
                    print(f"  └─ 已安装并可导入")
                except ImportError:
                    print(f"  └─ ✗ 未安装，请运行: pip install -e {pkg_path}")
                    all_ok = False
        
        print("-" * 60)
        return all_ok

    def clean_build(self):
        """清理构建目录"""
        print("\n清理构建目录...")
        print("-" * 60)
        
        for dir_path in [self.dist_dir, self.build_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"✓ 已清理: {dir_path}")
        
        print("-" * 60)

    def create_spec_file(self, debug=False):
        """创建 PyInstaller spec 文件"""
        print("\n创建 PyInstaller spec 文件...")
        print("-" * 60)
        
        # 获取本地包路径
        local_package_paths = [str(pkg_path) for pkg_path in self.local_packages.values() if pkg_path.exists()]
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# 项目路径
project_root = Path(r"{self.project_root}")
src_dir = project_root / "src"

# 本地包路径
local_packages = {local_package_paths}

# 数据文件
datas = [
    (str(project_root / "configs"), "configs"),
    (str(project_root / "resources"), "resources"),
]
datas += collect_data_files("flamekit", includes=["*.json"])
datas += copy_metadata("flamekit")

# 隐藏导入 - 完整列表
hiddenimports = [
    # PySide6 核心模块
    "PySide6.QtCore",
    "PySide6.QtWidgets", 
    "PySide6.QtGui",
    "PySide6.QtCharts",
    "PySide6.QtPrintSupport",
    
    # 图表和数据可视化
    "pyqtgraph",
    "pyqtgraph.graphicsItems",
    "pyqtgraph.graphicsItems.PlotItem",
    "pyqtgraph.graphicsItems.ViewBox",
    "pyqtgraph.graphicsItems.AxisItem",
    "pyqtgraph.graphicsItems.LegendItem",
    
    "matplotlib",
    "matplotlib.pyplot",
    "matplotlib.figure",
    "matplotlib.backends",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",
    
    # 数据处理
    "numpy",
    "numpy.core",
    "numpy.core._multiarray_umath",
    "numpy.testing",                       # ⭐ numpy 测试模块
    "numpy.testing._private",              # ⭐ numpy 测试私有模块
    "scipy",
    "scipy.signal",
    "scipy.interpolate",
    "scipy.optimize",
    "cv2",
    
    # 串口通信和Modbus
    "serial",
    "serial.tools",
    "serial.tools.list_ports",
    "pymodbus",
    "pymodbus.client",
    
    # 文档处理
    "docx",
    "docx.shared",
    "docx.enum.text",
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.lib",
    "reportlab.lib.pagesizes",
    "reportlab.platypus",
    "lxml",
    "lxml.etree",
    "openpyxl",
    
    # 系统和工具
    "yaml",
    
    # 本地包
    "flamekit",
    "flamekit.core",
    "flamekit.analyzer",
    "flamekit.camera",
    "flamekit.config",
    "flamekit.mvsdk",
    "modbus_multi_device",
    "scripts.smoke_check",
    
    # Python 标准库
    "unittest",                            # ⭐ 单元测试框架 (numpy/scipy 需要)
    "unittest.mock",                       # ⭐ mock 模块
    "sqlite3",
    "json",
    "logging",
    "logging.handlers",
    "threading",
    "queue",
    "datetime",
    "pathlib",
    "dataclasses",
    "enum",
    "collections",
    "collections.abc",
    "contextlib",
    "abc",
    "statistics",
    "hashlib",
    "secrets",
    "re",
    "functools",
    "atexit",
    "traceback",
    "csv",
    "binascii",
    "random",
    "uuid",
    "typing",
    "typing_extensions",
    "webbrowser",
    "urllib",
    "urllib.parse",
    "email",
    "email.mime",
    "email.mime.text",
    "email.mime.multipart",
    "smtplib",
    "struct",
    "array",
    "itertools",
    "operator",
    "math",
    "decimal",
    "fractions",
    "time",
    "os",
    "sys",
    "shutil",
    "tempfile",
    "gzip",
    "zipfile",
    "tarfile",
]

# 分析
a = Analysis(
    [str(src_dir / "app.py")],
    pathex=[str(project_root), str(src_dir)] + local_packages,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的包以减小体积
        "tkinter",
        # 注意: 不要排除 unittest, numpy.testing 需要它
        # "unittest",  
        # "test",  # numpy/scipy 可能需要 test 模块
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="{self.app_name}",
    debug={debug!r},
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={debug!r},  # 调试参数必须写入 spec；spec 构建不接受 --debug
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "resources" / "icons" / "cpie_logo_icon.ico"),
)

# 收集文件
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="{self.app_name}",
)
'''
        
        self.build_dir.mkdir(parents=True, exist_ok=True)
        spec_file = self.build_dir / f"{self.app_name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✓ Spec 文件已创建: {spec_file}")
        print(f"  - 包含 {len(local_package_paths)} 个本地包路径")
        print("-" * 60)
        return spec_file

    def build_application(self, spec_file, debug=False):
        """构建应用程序"""
        print("\n开始构建应用程序...")
        print("-" * 60)
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
        ]
        
        cmd.append(str(spec_file))
        
        print(f"执行命令: {subprocess.list2cmdline(cmd)}")
        print("-" * 60)
        
        try:
            subprocess.run(cmd, cwd=self.project_root, check=True, 
                          capture_output=False, text=True)
            print("-" * 60)
            print("✓ 应用程序构建完成")
            return True
        except subprocess.CalledProcessError as e:
            print("-" * 60)
            print(f"✗ 构建失败: {e}")
            return False

    def copy_additional_files(self):
        """复制额外需要的文件"""
        print("\n复制额外文件...")
        print("-" * 60)
        
        app_dir = self.dist_dir / self.app_name
        if not app_dir.exists():
            print(f"✗ 应用目录不存在: {app_dir}")
            return False
        
        # 复制配置文件
        configs_src = self.project_root / "configs"
        configs_dst = app_dir / "configs"
        if configs_src.exists():
            if configs_dst.exists():
                shutil.rmtree(configs_dst)
            shutil.copytree(configs_src, configs_dst)
            print(f"✓ 已复制配置文件: {configs_dst}")
        
        # 复制资源文件
        resources_src = self.project_root / "resources"
        resources_dst = app_dir / "resources"
        if resources_src.exists():
            if resources_dst.exists():
                shutil.rmtree(resources_dst)
            shutil.copytree(resources_src, resources_dst)
            print(f"✓ 已复制资源文件: {resources_dst}")
        
        # 检查样式文件
        styles_path = app_dir / "resources" / "styles"
        if styles_path.exists():
            qss_files = list(styles_path.glob("*.qss"))
            print(f"✓ 样式文件已包含，找到 {len(qss_files)} 个QSS文件")
            for qss_file in qss_files:
                print(f"  - {qss_file.name}")
        else:
            print(f"⚠ 样式文件目录不存在: {styles_path}")
        
        # 创建必要的目录
        required_dirs = ["data", "logs", "data/experiments", "data/uploads", "exports"]
        for dir_name in required_dirs:
            dir_path = app_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ 已创建目录: {dir_path}")
        
        # 复制文档文件
        doc_files = [
            "README.md", "QUICK_START.md", "BUILD_GUIDE.md", "requirements.txt",
            "CHANGELOG.md", "LICENSE", "docs/HARDWARE_ACCEPTANCE.md",
        ]
        for doc_file in doc_files:
            src_file = self.project_root / doc_file
            if src_file.exists():
                dst_file = app_dir / doc_file
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                print(f"✓ 已复制文档: {dst_file}")

        (app_dir / "build_info.json").write_text(
            json.dumps(self.get_build_metadata(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        
        print("-" * 60)
        return True

    def create_installer_script(self):
        """Install for the current user, preserving experimental data and settings."""
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        if self.platform == "windows":
            install_script = r'''@echo off
setlocal
chcp 65001 >nul
if not defined LOCALAPPDATA exit /b 1
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\CPIE"
set "SOURCE_DIR=%~dp0CPIE"
if not exist "%SOURCE_DIR%\CPIE.exe" exit /b 1
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if errorlevel 1 exit /b 1
rem User records and existing configuration must survive an upgrade.
robocopy "%SOURCE_DIR%" "%INSTALL_DIR%" /E /XD configs data logs exports /R:2 /W:1 /NFL /NDL
if errorlevel 8 exit /b 1
rem Only install new configuration files; never overwrite existing settings.
robocopy "%SOURCE_DIR%\configs" "%INSTALL_DIR%\configs" /E /XC /XN /XO /R:2 /W:1 /NFL /NDL
if errorlevel 8 exit /b 1
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $desktop=[Environment]::GetFolderPath('Desktop'); New-Item -ItemType Directory -Force -Path $desktop | Out-Null; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut((Join-Path $desktop 'CPIE.lnk')); $s.TargetPath=Join-Path $env:INSTALL_DIR 'CPIE.exe'; $s.WorkingDirectory=$env:INSTALL_DIR; $s.Save()"
if errorlevel 1 exit /b 1
echo CPIE installed to "%INSTALL_DIR%". Existing data and settings were preserved.
exit /b 0
'''
            script_file = self.dist_dir / "install.bat"
            with script_file.open("w", encoding="utf-8", newline="\r\n") as stream:
                stream.write(install_script)
        else:
            # Portable operation is also the default on macOS/Linux. No sudo or
            # system directory changes are needed to run an extracted package.
            script_file = self.dist_dir / "install.sh"
            script_file.write_text(
                '#!/bin/sh\nset -eu\n'
                'cd "$(dirname "$0")"\n'
                'echo "CPIE uses portable mode. Keep this folder in a user-writable location."\n'
                'chmod u+x CPIE/CPIE\n'
                'echo "Start with: ./CPIE/CPIE"\n',
                encoding="utf-8",
            )
            script_file.chmod(0o755)
        print(f"✓ 安装脚本已创建: {script_file}")

    def get_build_metadata(self):
        """Record exactly which source and installed packages produced the build."""
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.project_root, text=True
        ).strip()
        source_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=self.project_root, text=True,
        ).strip())
        dependencies = {
            distribution.metadata["Name"]: distribution.version
            for distribution in importlib.metadata.distributions()
            if distribution.metadata.get("Name")
        }
        flamekit_distribution = importlib.metadata.distribution("flamekit")
        direct_url = json.loads(flamekit_distribution.read_text("direct_url.json") or "{}")
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "app_description": self.app_description,
            "platform": self.platform,
            "architecture": self.arch,
            "python_version": platform.python_version(),
            "build_time": datetime.now().astimezone().isoformat(),
            "source_commit": source_commit,
            "source_dirty": source_dirty,
            "dependencies": dict(sorted(dependencies.items(), key=lambda item: item[0].lower())),
            "flamekit_commit": direct_url.get("vcs_info", {}).get("commit_id"),
        }

    def create_release_package(self):
        """创建发布包"""
        print("\n创建发布包...")
        print("-" * 60)
        
        # 确保发布目录存在
        self.release_dir.mkdir(exist_ok=True)
        
        # 发布包名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = f"{self.app_name}_{self.app_version}_{self.platform}_{self.arch}_{timestamp}"
        
        # 创建压缩包
        package_file = self.release_dir / f"{package_name}.zip"
        
        print(f"正在打包到: {package_file.name}")
        
        with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加应用目录
            app_dir = self.dist_dir / self.app_name
            file_count = 0
            for file_path in app_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.dist_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
            
            print(f"  - 已打包 {file_count} 个文件")
            
            # 添加安装脚本
            for script_file in self.dist_dir.glob('install.*'):
                zipf.write(script_file, script_file.name)
                print(f"  - 已添加: {script_file.name}")
        
        file_size_mb = package_file.stat().st_size / 1024 / 1024
        print(f"\n✓ 发布包已创建: {package_file}")
        print(f"  文件大小: {file_size_mb:.1f} MB")
        
        # 创建发布信息文件
        package_sha256 = hashlib.sha256()
        with package_file.open("rb") as archive:
            for chunk in iter(lambda: archive.read(1024 * 1024), b""):
                package_sha256.update(chunk)
        release_info = self.get_build_metadata()
        release_info.update({
            "package_file": package_file.name,
            "package_size_bytes": package_file.stat().st_size,
            "package_sha256": package_sha256.hexdigest(),
        })
        package_file.with_suffix(".zip.sha256").write_text(
            f"{package_sha256.hexdigest()}  {package_file.name}\n", encoding="ascii"
        )
        
        info_file = self.release_dir / f"{package_name}_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(release_info, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 发布信息已创建: {info_file}")
        print("-" * 60)
        
        return package_file

    def _check_app_icons(self):
        """检查应用图标是否存在"""
        print("\n检查应用图标...")
        print("-" * 60)
        
        icon_file = self.project_root / "resources" / "icons" / "cpie_logo_icon.ico"
        if icon_file.exists():
            print(f"✓ 应用图标已存在: {icon_file}")
            print(f"  文件大小: {icon_file.stat().st_size / 1024:.1f} KB")
            print("-" * 60)
            return True
        else:
            print(f"⚠ 应用图标不存在: {icon_file}")
            print("  将使用默认图标")
            print("-" * 60)
            return False
    
    def verify_build(self):
        """验证构建结果"""
        print("\n验证构建结果...")
        print("-" * 60)
        
        app_dir = self.dist_dir / self.app_name
        if not app_dir.exists():
            print(f"✗ 应用目录不存在: {app_dir}")
            return False
        
        # 检查关键文件
        key_files = [
            self.app_name + (".exe" if self.platform == "windows" else ""),
            "configs",
            "resources",
            "resources/styles",
            "configs/software.info",
            "configs/experiment_config.yaml",
            "configs/flame_analyzer_config.yaml",
            "_internal/flamekit/config_default.json",
            "build_info.json",
        ]
        
        all_ok = True
        for file_name in key_files:
            file_path = app_dir / file_name
            if not file_path.exists():
                print(f"✗ 缺少: {file_name}")
                all_ok = False
            else:
                if file_path.is_file():
                    size = file_path.stat().st_size / 1024 / 1024
                    print(f"✓ 已找到: {file_name} ({size:.1f} MB)")
                else:
                    print(f"✓ 已找到: {file_name} (目录)")
        
        # 检查样式文件
        styles_dir = app_dir / "resources" / "styles"
        if styles_dir.exists():
            qss_files = list(styles_dir.glob("*.qss"))
            if qss_files:
                print(f"✓ 找到 {len(qss_files)} 个样式文件:")
                for qss_file in qss_files:
                    print(f"  - {qss_file.name}")
            else:
                print("⚠ 样式目录存在但没有找到QSS文件")
                all_ok = False
        
        # 统计总文件数和大小
        total_files = sum(1 for _ in app_dir.rglob('*') if _.is_file())
        total_size = sum(f.stat().st_size for f in app_dir.rglob('*') if f.is_file())
        total_size_mb = total_size / 1024 / 1024
        
        print(f"\n构建统计:")
        print(f"  总文件数: {total_files}")
        print(f"  总大小: {total_size_mb:.1f} MB")
        
        print("-" * 60)
        if all_ok:
            print("✓ 构建结果验证完成")
        else:
            print("⚠ 构建验证发现问题")
        
        return all_ok

    def build(self, debug=False, clean=True):
        """完整构建流程"""
        print("\n" + "=" * 60)
        print(f"开始构建 CPIE {self.app_version}")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 1. 检查应用图标
            self._check_app_icons()
            
            # 2. 检查本地包
            if not self.check_local_packages():
                print("\n✗ 本地包检查失败")
                print("请确保本地包已正确安装")
                return False
            
            # 3. 检查依赖
            if not self.check_dependencies():
                return False
            
            # 4. 清理构建目录
            if clean:
                self.clean_build()
            
            # 5. 创建 spec 文件
            spec_file = self.create_spec_file(debug=debug)
            
            # 6. 构建应用程序
            if not self.build_application(spec_file, debug):
                return False
            
            # 7. 复制额外文件
            if not self.copy_additional_files():
                return False
            
            # 8. 验证构建结果
            if not self.verify_build():
                print("✗ 构建验证失败，不生成发布包")
                return False
            
            # 9. 创建安装脚本
            self.create_installer_script()
            
            # 10. 创建发布包
            package_file = self.create_release_package()
            
            # 计算构建时间
            end_time = datetime.now()
            build_time = (end_time - start_time).total_seconds()
            
            print("\n" + "=" * 60)
            print("✓ 构建完成！")
            print("=" * 60)
            print(f"构建时间: {build_time:.1f} 秒")
            print(f"应用目录: {self.dist_dir / self.app_name}")
            print(f"发布包: {package_file}")
            print(f"发布包大小: {package_file.stat().st_size / 1024 / 1024:.1f} MB")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print("\n" + "=" * 60)
            print(f"✗ 构建失败: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

def main():
    parser = argparse.ArgumentParser(
        description="CPIE 应用打包构建脚本 (优化版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build_release.py                    # 正常构建
  python build_release.py --debug            # 调试模式构建
  python build_release.py --no-clean         # 不清理构建目录
  python build_release.py --debug --no-clean # 组合选项
        """
    )
    parser.add_argument("--debug", action="store_true", 
                       help="启用调试模式,输出详细构建信息")
    parser.add_argument("--no-clean", action="store_true", 
                       help="不清理构建目录,用于增量构建")
    
    args = parser.parse_args()
    
    try:
        builder = CPIEBuilder()
        success = builder.build(debug=args.debug, clean=not args.no_clean)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断构建")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n构建过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
