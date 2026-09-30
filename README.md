# CPIE 2.0 — 煤粉着火点及爆炸性检测系统

CPIE 为 CPIE-3000A 实验设备提供 PySide6 桌面界面，包含着火点温度采集、爆炸实验时序、火焰分析、SQLite 历史记录以及 CSV、Excel、Word 导出。

**v1.2.1 软件发布，真机验收待完成。** 维护者于 2026-09-30 决定先合并发版、暂时结束本阶段开发，后续再进行现场验收。目标平台为 Windows 10/11 64 位；自动化验证不代表仪表、相机和完整实验流程已通过验收。

[下载与更新记录](https://github.com/kevinalliswell/CPIE2/releases/tag/v1.2.1) · [发布说明](docs/releases/v1.2.1.md) · [副屏开关待办 #8](https://github.com/kevinalliswell/CPIE2/issues/8)

## 从哪里开始

- 实验操作人员：[快速开始](QUICK_START.md)，使用经过验收的完整 Windows 安装包。
- 开发与交付人员：[构建与发布指南](BUILD_GUIDE.md)，重建环境、测试并生成候选包。
- 当前剩余工作：[收敛状态](docs/CLOSEOUT_STATUS.md) 和 [Windows 实机验收记录](docs/HARDWARE_ACCEPTANCE.md)。
- 相机和完整轮次的本轮修复、参数边界见 [专项审查](docs/CAMERA_EXPLOSION_AUDIT.md)。
- 变更与历史材料：[更新记录](CHANGELOG.md) 和 [旧工作去向](docs/LEGACY_WORK_DISPOSITION.md)。

## 源码运行

在项目根目录执行以下 PowerShell 命令。需要 Git、64 位 Python 3.9 和 FlameKit 私有仓库的读取权限。本机验证使用 **Python 3.9.6**，CI 使用 **Python 3.9** 并记录实际补丁版本；其他 Python 版本不属于当前验证范围。

```powershell
git clone https://github.com/kevinalliswell/CPIE2.git
cd CPIE2
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -e modbus_multi_device_package
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe src/app.py
```

请检出明确的版本标签（本次为 `v1.2.1`）或需要验证的提交后安装依赖。上述命令无需激活虚拟环境。只运行应用安装 `requirements.txt`；需要测试或打包时，改装包含运行依赖的 `requirements-dev.txt`，并同样安装本地 Modbus 包。

FlameKit 已移出本仓库，通过 `requirements.txt` 固定到外部源码提交 `f0c3e65c0c68b28e41b3e195764a8f0d0a1ab4bd`。不要再安装本地 `flame_package/`。访问失败时先配置该私有仓库的 Git 读取权限；不能通过删除依赖继续安装。本仓库 CI 已配置专用只读 Deploy Key，详见构建指南。

首次启动先检查页面、配置和历史功能，再按现场规程连接设备。真实实验还需要相应串口设备、驱动及相机 SDK；它们不由 pip 自动完成现场配置。

## 验证命令

以下命令使用已安装 `requirements-dev.txt` 的环境，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/smoke_check.py --source --output artifacts/source-smoke.json
```

自动测试使用临时数据路径；源码 smoke 启动真实窗口，检查页面、异常会话恢复、两类历史数据及导出、关闭重开，并禁止硬件访问。它不代表实际加热、继电器关断、压力测量或相机采集已通过验收。现场项目及证据要求见 [实机验收记录](docs/HARDWARE_ACCEPTANCE.md)。

## 数据与项目结构

Windows 安装器以普通用户身份安装到 `%LOCALAPPDATA%\Programs\CPIE`，升级保留已有 `data/`、`configs/`、`logs/`、`exports/`。升级前先结束实验、关闭应用并备份这些目录；相机用户配置也需单独备份。便携使用应保留完整 `CPIE/` 文件夹，并放在当前用户可写的位置。

| 路径 | 用途 |
|---|---|
| `src/app.py` | 应用入口、单实例保护、启动恢复 |
| `src/controllers/`、`src/services/` | 实验流程、采集和分析 |
| `src/models/` | 两类实验数据库及状态 |
| `src/views/` | 主窗口、实验页、历史查询及副屏 |
| `modbus_multi_device_package/` | 本地 Modbus 通信实现及测试 |
| `configs/`、`resources/` | 配置、样式与静态资源 |
| `tests/`、`scripts/smoke_check.py` | 自动回归及无设备启动检查 |
| `build_release.py`、`.github/workflows/` | 候选构建、Windows 验证及发布 |

维护变更通过 PR 审查。软件发布须核对最终源码 SHA、自动化证据及包 SHA256；现场验收状态独立记录，不得沿用旧标签覆盖发布。本轮不会仅凭测试通过就把设备验收标为完成。
