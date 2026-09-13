# CPIE 2.0 打包构建指南

## 📋 目录
- [环境准备](#环境准备)
- [依赖安装](#依赖安装)
- [自动化 Release（Windows）](#自动化-releasewindows)
- [构建流程](#构建流程)
- [构建输出](#构建输出)
- [常见问题](#常见问题)
- [版本与 Tag 约定](#版本与-tag-约定)
- [自动化 Release 验证建议](#自动化-release-验证建议)
- [优化说明](#优化说明)
- [构建检查清单](#构建检查清单)

---

## 🔧 环境准备

### 系统要求
- **操作系统**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python 版本**: 3.10+ (推荐 3.11；pymodbus 3.10+ 不支持 Python 3.9)
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
pip install -r requirements.txt
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
flamekit                  0.1.1       D:\CPIE2\flame_package
modbus_multi_device       1.0.0       D:\CPIE2\modbus_multi_device_package
...
```

---

## 自动化 Release（Windows）
仓库内置 GitHub Actions release workflow：
- 正式发布从 `main` 产出
- 通过推送 `v*` tag 触发
- 首版只构建 Windows 产物

典型流程：
```bash
# 1. 确保 dev 已经通过 PR 合并到 main
# 2. 切换到 main 并同步远端
git checkout main
git pull origin main

# 3. 创建并推送 release tag
git tag v1.1.0
git push origin v1.1.0
```

workflow 会自动：
- 安装依赖和本地包
- 运行 `build_release.py`
- 收集 `release/` 下的 zip 与 info 文件
- 创建 GitHub Release 并上传产物

如需先验证 workflow 逻辑，可先在 `dev` 分支检查 `.github/workflows/release.yml` 内容，确认后再合并到 `main`。

---

## 🚀 构建流程

### 使用构建脚本

#### 基本构建
```bash
python build_release.py
```

#### 调试模式构建
```bash
python build_release.py --debug
```

#### 增量构建 (不清理)
```bash
python build_release.py --no-clean
```

#### 组合选项
```bash
python build_release.py --debug --no-clean
```

> 当前仓库以 `build_release.py` 作为唯一维护中的构建入口。

---

## 📊 构建输出

### 目录结构
```text
CPIE2/
├── dist/                    # 构建输出目录
│   ├── CPIE/                # 应用程序目录
│   └── install.bat          # 安装脚本 (Windows)
├── build/                   # 临时构建文件
├── release/                 # 发布包目录
│   ├── CPIE_1.1.0_windows_amd64_<timestamp>.zip
│   └── CPIE_1.1.0_windows_amd64_<timestamp>_info.json
└── CPIE.spec                # PyInstaller 配置文件
```

### 发布包内容
- **应用程序**: 完整的可执行文件
- **配置文件**: configs/
- **资源文件**: resources/ (图标、样式、图片等)
- **文档**: README.md, requirements.txt, LICENSE
- **安装脚本**: install.bat (Windows) 或 install.sh (Unix)

---

## ⚠️ 常见问题

### 问题1: ModuleNotFoundError: No module named 'flamekit'
**原因**: 本地包未正确安装

**解决方案**:
```bash
# 重新安装本地包
pip install -e ./flame_package
pip install -e ./modbus_multi_device_package

# 验证安装
pip list | grep flamekit
pip list | grep modbus
```

### 问题1.1: 无相机环境下导入失败 (`libMVSDK.so` / 相机 SDK)
**原因**: 工业相机 SDK 未安装或当前机器无对应驱动

**说明**:
- 现在非硬件测试与基本启动 smoke check 已做延迟加载处理
- 真正使用相机时，仍然需要本机具备厂商 SDK/驱动
- 自动化 Windows release 只负责打包，不会为你安装本地相机驱动

**建议**:
- 在实验机上安装迈德威视 SDK 和驱动
- 在 CI / 开发机上把相机相关验证限制为非硬件 smoke check

---

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
python build_release.py --debug

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
pip install "opencv-python>=4.12.0"

# 如果仍有问题,尝试无头版本
pip install opencv-python-headless
```

### 问题6: Release workflow 没有产出文件
**排查步骤**:
1. 检查 tag 是否从 `main` 推送，格式是否匹配 `v*`
2. 检查 GitHub Actions 日志里依赖安装、本地包安装、`build_release.py` 三个阶段
3. 确认 `release/` 目录下至少生成：
   - `*.zip`
   - `*_info.json`
4. 若 workflow 成功但 Release 无附件，检查 `softprops/action-gh-release` 的 `files` 路径是否与构建输出一致

---

## 📦 版本与 Tag 约定
- 应用内版本：`configs/software.info`
- Release tag：`v1.1.0`
- GitHub Actions 从 tag 去掉前缀 `v` 后，写回构建时的 `configs/software.info`，确保发布产物显示的版本与 tag 一致

---

## 🧪 自动化 Release 验证建议
在正式推送 `v1.1.0` 前，建议先确认：
1. `dev` 已通过 PR 合并到 `main`
2. `main` 工作树干净
3. 本地手动运行过一次：
   ```bash
   python build_release.py --debug
   ```
4. 推送 tag：
   ```bash
   git checkout main
   git pull origin main
   git tag v1.1.0
   git push origin v1.1.0
   ```
5. 到 GitHub Actions 页面查看 release workflow 是否成功产出 Windows 安装包

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
    str(project_root / "flame_package"),
    str(project_root / "modbus_multi_device_package")
]
```

#### 4. Release workflow 支持
- ✅ 新增 `.github/workflows/release.yml`
- ✅ 监听 `v*` tag 自动构建 Windows 发布包
- ✅ 自动创建 GitHub Release 并上传 `release/` 目录产物
- ✅ 构建前同步 `configs/software.info` 中的版本为 tag 去掉 `v` 后的值

---

## ✅ 构建检查清单
发布前建议确认：
- [ ] `requirements.txt` 已安装
- [ ] `flame_package` 已可导入
- [ ] `modbus_multi_device_package` 已可导入
- [ ] `configs/software.info` 版本正确
- [ ] `resources/icons/cpie_logo_icon.ico` 存在
- [ ] `resources/styles/*.qss` 存在
- [ ] 本地 `python build_release.py` 至少成功运行一次
- [ ] GitHub Actions release workflow 已合并到 `main`
- [ ] 推送 tag 格式为 `v*`

---

## 🔚 总结
当前推荐的正式发布方式是：
1. `dev` 完成功能与验证
2. PR 合并到 `main`
3. 在 `main` 推送 `v1.1.0` 这类 tag
4. GitHub Actions 自动构建 Windows 产物并创建 GitHub Release

这样可以让发布流程可重复、可审计，也能减少手工打包失误。
