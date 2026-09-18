# 构建与发布指南

本指南对应 **1.2.1 候选版本**。正式目标平台为 Windows 10/11 64 位。Windows 自动化验证结果以当前 PR 的检查和构建证据为准；现场硬件验收须单独完成。构建成功只表示生成了候选包，是否可正式交付由自动化证据及 [实机验收记录](docs/HARDWARE_ACCEPTANCE.md) 共同决定。

## 1. 重建开发环境

使用独立检出目录和 64 位 Python 3.9。当前本机环境为 **Python 3.9.6**；Windows CI 使用 `actions/setup-python` 的 `3.9`，构建元数据记录实际补丁版本。不要直接复用原 dirty dev 工作区或旧虚拟环境作为发布输入。

在项目根目录执行 PowerShell 命令：

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -e modbus_multi_device_package
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe --version
```

`requirements.txt` 固定应用运行依赖；`requirements-dev.txt` 引入运行依赖，再增加 pytest、pytest-timeout 和 PyInstaller 等测试构建工具。只运行源码应用时安装前者。两种方式均需另外安装仓库中的 `modbus_multi_device_package`。

macOS 仅用于开发与软件验证：可用 `python3.9 -m venv .venv`，之后将 Windows 命令中的解释器路径替换为 `.venv/bin/python`。macOS 构建不能代替 Windows 构建。

### FlameKit 私有依赖

`requirements.txt` 使用以下不可变来源：

```text
flamekit @ git+https://github.com/kevinalliswell/flame-package.git@f0c3e65c0c68b28e41b3e195764a8f0d0a1ab4bd
```

本地 pip 调用 Git 拉取此源码，需要当前 Git 身份具备该私有仓库读取权限。不要在依赖文件中写入令牌或私钥，也不要改回本地 `flame_package/`。该提交是上游 Draft PR #1 的分支头，不是 release tag，其安装元数据仍为 `1.1.2`，因此必须用完整提交 SHA 核对来源，不能只比较包版本字符串。

CI 使用项目专用的只读 Deploy Key：公钥授权到 `kevinalliswell/flame-package`，私钥存为 CPIE2 Actions Secret `FLAMEKIT_DEPLOY_KEY`。**本仓库已完成配置并验证固定提交可读取。** 工作流先验证权限，再按固定 SHA 检出私有依赖；临时映射只作用于安装子进程，不修改全局 Git 配置。发布流程仅向验证工作流显式传递这一项 Secret。缺少授权会明确失败，不跳过依赖或测试。

更换或撤销权限时，维护者须同时核对 FlameKit 的 Deploy Key 与 CPIE2 的同名 Secret；公钥始终保持 `read_only=true`。新建密钥后先验证固定源码提交可读，再更新 Secret 并撤销旧公钥。私钥不写入仓库或操作日志。

## 2. 执行源码验证

```powershell
.\.venv\Scripts\python.exe -m compileall -q src scripts build_release.py modbus_multi_device_package/modbus_multi_device
.\.venv\Scripts\python.exe -m pytest --junitxml=artifacts/pytest-windows.xml
.\.venv\Scripts\python.exe scripts/smoke_check.py --source --output artifacts/source-smoke.json
```

pytest 默认收集 `tests/` 和 Modbus 包自动测试，并隔离应用数据路径。需要真实设备或人工交互的脚本位于 `tests/manual/`，不作为无人值守 CI 执行内容。

源码 smoke 使用显式 `--smoke-test` 模式，在临时目录中启动真实 Qt 窗口，检查七个页面、副屏、两类数据库异常恢复、同 ID 历史 CSV/Excel/Word 导出和关闭重开。检查禁止串口与相机初始化，不打开操作人员数据库。退出码非零或输出 JSON 的 `success` 不为 `true`，均视为失败。

这些检查验证软件流程，现场读写、校准、实际关断及相机采集仍按验收表执行。本机结果见 [收敛状态](docs/CLOSEOUT_STATUS.md)，不能把本机通过写成 Windows 已通过。

## 3. 构建并检查冻结程序

在 Windows 的同一环境运行：

```powershell
.\.venv\Scripts\python.exe build_release.py
.\.venv\Scripts\python.exe scripts/smoke_check.py --executable dist/CPIE/CPIE.exe --output artifacts/frozen-smoke.json
```

构建脚本读取 `configs/software.info` 的版本，默认清理临时构建输出，通过 PyInstaller 打包应用、已安装的 FlameKit 默认配置和包元数据。缺少必需文件或构建失败会返回非零，不应继续交付。确保有足够磁盘空间；排查可使用 `build_release.py --debug`，正式候选须重新执行完整默认构建。

输出包括：

| 输出 | 用途 |
|---|---|
| `dist/CPIE/` | 完整应用目录；Windows 入口为 `CPIE.exe` |
| `dist/install.bat` | 当前用户安装脚本 |
| `dist/CPIE/build_info.json` | 包内版本、源码、平台及依赖来源 |
| `release/CPIE_<版本>_<平台>_<架构>_<时间>.zip` | 包含应用目录和安装脚本的候选包 |
| 同名 `_info.json` | 构建信息、ZIP 文件名、大小及 SHA256 |
| 同名 `.zip.sha256` | ZIP SHA256 校验文件 |

在生成包的 Windows 环境检查冻结程序 smoke，然后在实际 Windows 普通用户环境验证安装器。安装目标为 `%LOCALAPPDATA%\Programs\CPIE`，升级保留 `data/`、`configs/`、`logs/`、`exports/` 的已有内容；配置仅补充缺失文件。不能仅复制一个 EXE，也不能把用户可写数据放进受限的系统程序目录。升级前备份及现场验证步骤见 [快速开始](QUICK_START.md)。

## 4. 校验构建来源

PowerShell 校验 ZIP，将占位文件名替换为本次产物：

```powershell
Get-FileHash .\release\实际包名.zip -Algorithm SHA256
git rev-parse HEAD
git status --short
```

确认计算值与 `.zip.sha256` 及 `_info.json` 的 `package_sha256` 一致；记录中的 `source_commit` 必须为实际构建提交。正式发布从干净检出构建，`source_dirty` 必须为 `false`。此字段仅反映已跟踪文件，仍需检查未跟踪文件和构建输入。

同时核对 `app_version`、平台、架构、实际 Python 版本、依赖版本及 `flamekit_commit`。FlameKit 必须等于固定 SHA，`pymodbus` 应为 `3.8.6`。源码 SHA 用于追溯构建来源，ZIP SHA256 用于确认交付文件未变化；两者应与验收记录一并保存。

## 5. Windows CI 和发行门禁

工作流定义：

- [windows-validation.yml](.github/workflows/windows-validation.yml)：main 的 PR、main push 及复用调用，依次执行依赖一致性、语法检查、全部自动测试、源码 smoke、构建、冻结程序 smoke、校验和来源验证。
- 成功后上传 `windows-candidate`（候选包、元数据、校验文件）；`windows-validation-evidence` 保存测试和 smoke 证据。候选 artifact 保留 30 天，长期验收材料需另行归档。
- [release.yml](.github/workflows/release.yml)：新 `v*` tag push 或手动指定已存在的版本 tag。先解析 tag 的确切提交，要求 tag 去掉 `v` 后与该提交的 `configs/software.info` 版本完全一致，再复用 Windows 验证。只有验证成功才发布同次工作流的候选文件，不另行重打包。

**现场硬件验收是人工发布前置条件，工作流不会自动证明它已完成。** 因 tag push 会触发正式发布，按以下顺序操作：

1. 完成收敛 PR、代码审查和候选 Windows 验证；私有依赖授权失败须先解决。
2. 用候选包完成实机验收，保存源码 SHA、ZIP SHA256、设备配置、现场日志及结果。
3. 合并后对最终 main 提交重新构建和验证；若源码 SHA 变化，按影响复验并更新记录，不能沿用不对应的验收结论。
4. 确认最终待标记提交已通过所需验收，使用与源码版本一致的新 tag 触发 Release，核对发布资产和构建证据。
5. 归档材料后按 [旧工作去向](docs/LEGACY_WORK_DISPOSITION.md) 整理分支；保留明确需要延续的独立包工作。

不要覆盖旧 `v1.1.2`：原本地与远端该标签指向不同提交，旧 Release 还包含不同来源的历史资产。本轮仅准备候选和 PR，不因文档出现 `1.2.1` 就表示已创建 tag、Windows CI 已成功或正式发布已完成。
