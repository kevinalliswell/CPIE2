# CPIE 2.0 打包构建指南

## 📋 目录
- [环境准备](#环境准备)
- [依赖安装](#依赖安装)
- [构建流程](#构建流程)
- [常见问题](#常见问题)
- [优化说明](#优化说明)

---

## 🔧 环境准备

### 系统要求
- **操作系统**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python 版本**: 3.10+ (推荐 3.11)
- **磁盘空间**: 至少 2GB 可用空间
- **内存**: 建议 8GB 以上

### 检查 Python 版本
```bash
python --version
# 或
python3 --version
```

---

## 📦 依赖安装

### 1. 创建虚拟环境 (推荐)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 升级 pip
```bash
python -m pip install --upgrade pip
```

### 3. 安装标准依赖
```bash
pip install -r requirements_full.txt
```

### 4. 安装本地包 (重要!)

#### flamekit - 火焰分析工具包
```bash
# 方式1: 开发模式安装 (推荐)
pip install -e ./flame_package

# 方式2: 直接安装
pip install ./flame_package
```

#### modbus_multi_device - Modbus多设备通信包
```bash
# 方式1: 开发模式安装 (推荐)
pip install -e ./modbus_multi_device_package

# 方式2: 直接安装
pip install ./modbus_multi_device_package
```

### 5. 验证安装
```bash
# 查看已安装的包
pip list

# 验证本地包是否正确安装
python -c "import flamekit; print('flamekit:', flamekit.__version__)"
python -c "import modbus_multi_device; print('modbus_multi_device OK')"
```

**预期输出示例:**
```
Package                   Version     Editable project location
------------------------- ----------- ------------------------------------
...
flamekit                  0.1.0       D:\CPIE2\src\flame_package
modbus_multi_device       1.0.0       D:\CPIE2\modbus_multi_device_package
...
```

---

## 🚀 构建流程

### 方式1: 使用优化脚本 (推荐)

#### 基本构建
```bash
python build_release_optimized.py
```

#### 调试模式构建
```bash
python build_release_optimized.py --debug
```

#### 增量构建 (不清理)
```bash
python build_release_optimized.py --no-clean
```

#### 组合选项
```bash
python build_release_optimized.py --debug --no-clean
```

### 方式2: 使用原始脚本
```bash
python build_release.py
```

---

## 📊 构建输出

### 目录结构
```
CPIE2/
├── dist/                    # 构建输出目录
│   ├── CPIE/               # 应用程序目录
│   │   ├── CPIE.exe        # 主程序 (Windows)
│   │   ├── configs/        # 配置文件
│   │   ├── resources/      # 资源文件
│   │   │   └── styles/     # QSS样式文件
│   │   ├── data/           # 数据目录
│   │   ├── logs/           # 日志目录
│   │   └── exports/        # 导出目录
│   └── install.bat         # 安装脚本 (Windows)
├── build/                   # 临时构建文件
├── release/                 # 发布包目录
│   ├── CPIE_1.1.0_windows_amd64_20241208_143022.zip
│   └── CPIE_1.1.0_windows_amd64_20241208_143022_info.json
└── CPIE.spec               # PyInstaller 配置文件
```

### 发布包内容
- **应用程序**: 完整的可执行文件
- **配置文件**: configs/
- **资源文件**: resources/ (图标、样式、图片等)
- **文档**: README.md, requirements.txt, CHANGELOG.md
- **安装脚本**: install.bat (Windows) 或 install.sh (Unix)

---

## ⚠️ 常见问题

### 问题1: ModuleNotFoundError: No module named 'flamekit'
**原因**: 本地包未正确安装

**解决方案**:
```bash
# 重新安装本地包
pip install -e ./src/flame_package
pip install -e ./modbus_multi_device_package

# 验证安装
pip list | grep flamekit
pip list | grep modbus
```

### 问题2: PyInstaller 构建失败
**原因**: 缺少隐藏导入或数据文件

**解决方案**:
1. 检查 spec 文件中的 `hiddenimports` 列表
2. 确认所有数据文件路径正确
3. 使用 `--debug` 模式查看详细错误信息

### 问题3: 构建后程序无法启动
**可能原因**:
- 缺少必要的 DLL 文件 (Windows)
- 资源文件路径错误
- Python 版本不兼容

**排查步骤**:
```bash
# 1. 使用调试模式构建
python build_release_optimized.py --debug

# 2. 在命令行中运行程序查看错误
cd dist/CPIE
CPIE.exe  # 或 ./CPIE

# 3. 检查日志文件
cat logs/app.log
```

### 问题4: 样式文件 (QSS) 未加载
**检查清单**:
```bash
# 1. 验证样式文件是否存在
ls dist/CPIE/resources/styles/

# 2. 检查文件权限
# Windows: 右键 -> 属性 -> 安全
# Linux/macOS: ls -l dist/CPIE/resources/styles/

# 3. 确认 spec 文件中包含样式目录
# datas = [
#     ("resources", "resources"),
# ]
```

### 问题5: opencv-python 导入错误
**解决方案**:
```bash
# 重新安装 opencv-python
pip uninstall opencv-python
pip install opencv-python>=4.12.0

# 如果仍有问题,尝试无头版本
pip install opencv-python-headless
```

---

## 🎯 优化说明

### 相比原脚本的改进

#### 1. 完整的依赖检测
- ✅ 新增 matplotlib, scipy, opencv-python 检测
- ✅ 新增文档处理包检测 (python-docx, reportlab, lxml)
- ✅ 新增本地包检测和验证

#### 2. 增强的隐藏导入列表
```python
# 原脚本缺失的重要模块
"matplotlib",
"matplotlib.pyplot",
"matplotlib.backends.backend_qt5agg",
"scipy",
"scipy.signal",
"cv2",
"docx",
"reportlab",
"lxml",
"pymodbus",
"flamekit",              # 本地包
"modbus_multi_device",   # 本地包
```

#### 3. 本地包路径配置
```python
# 自动添加本地包到 pathex
local_packages = [
    str(project_root / "src" / "flame_package"),
    str(project_root / "modbus_multi_device_package")
]

# 在 Analysis 中使用
pathex=[str(project_root), str(src_dir)] + local_packages
```

#### 4. 改进的输出信息
- ✅ 更清晰的分隔线和标题
- ✅ 详细的构建统计 (文件数、大小、耗时)
- ✅ 彩色标记 (✓ ✗ ⚠)
- ✅ 进度提示

#### 5. 增强的验证功能
- ✅ 样式文件详细检查
- ✅ 文件大小统计
- ✅ 构建时间记录
- ✅ 发布包信息 JSON

---

## 📝 构建检查清单

构建前请确认:

- [ ] Python 版本 >= 3.10
- [ ] 虚拟环境已激活
- [ ] pip 已升级到最新版本
- [ ] requirements_full.txt 中的包全部安装
- [ ] flamekit 包已安装 (开发模式)
- [ ] modbus_multi_device 包已安装 (开发模式)
- [ ] configs/ 目录存在且包含 software.info
- [ ] resources/ 目录存在且包含必要资源
- [ ] resources/icons/cpie_logo_icon.ico 存在
- [ ] src/app.py 文件存在

---

## 🛠️ 高级用法

### 自定义 Spec 文件
如果需要更多控制,可以手动编辑生成的 `.spec` 文件:

```python
# CPIE.spec

# 添加额外的二进制文件
binaries=[
    ('path/to/custom.dll', '.'),
],

# 添加额外的隐藏导入
hiddenimports=[
    'custom_module',
],

# 修改可执行文件选项
exe = EXE(
    # ...
    console=True,  # 显示控制台 (调试用)
    # ...
)
```

### 条件构建
```bash
# 仅在有更改时构建
python build_release_optimized.py --no-clean

# 调试特定模块问题
python build_release_optimized.py --debug 2>&1 | tee build.log
```

### 清理构建缓存
```bash
# 手动清理
rm -rf build/ dist/ *.spec  # Linux/macOS
rmdir /s /q build dist & del *.spec  # Windows

# 或使用脚本
python -c "from build_release_optimized import CPIEBuilder; CPIEBuilder().clean_build()"
```

---

## 📞 技术支持

如遇到其他问题,请:
1. 查看构建日志文件
2. 检查 PyInstaller 官方文档
3. 搜索相关错误信息
4. 提交 Issue (附带完整错误日志)

---

## 📌 版本信息

- **脚本版本**: 2.0 (优化版)
- **更新日期**: 2024-12-08
- **适用项目**: CPIE 2.0
- **维护者**: Kevin

---

**祝构建顺利! 🎉**
