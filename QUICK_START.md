# 快速开始

当前代码为 **1.2.1 候选版本**，Windows 冻结包和正式硬件验收仍待完成。实验操作人员应使用项目负责人明确验收的安装包；候选包仅用于受控验证。验收清单见 [Windows 实机验收记录](docs/HARDWARE_ACCEPTANCE.md)。

## Windows 安装

1. 获取同一构建的 ZIP、对应 `_info.json` 和 `.zip.sha256`。核对版本及源码提交，避免把旧版本同名资产当作本次候选包。
2. 在 PowerShell 执行以下命令，将 `实际包名.zip` 替换为下载文件名。结果应与 `.zip.sha256` 第一项及 `_info.json` 的 `package_sha256` 一致。

   ```powershell
   Get-FileHash .\实际包名.zip -Algorithm SHA256
   ```

3. 将 ZIP 完整解压到一个临时目录，确认同级存在 `install.bat` 和 `CPIE/` 文件夹。以普通用户运行 `install.bat`，无需管理员权限。
4. 安装位置为 `%LOCALAPPDATA%\Programs\CPIE`。从桌面 CPIE 快捷方式启动，或打开安装目录中的 `CPIE.exe`。

完整安装包运行不需要 Python。串口驱动、仪表参数和相机 SDK 按现场设备要求安装配置。便携运行可直接使用解压后的 `CPIE/CPIE.exe`，但须保留整个目录，并确保当前用户可以写入该目录。

## 首次检查和实验

1. 暂不开始实验，先打开各页面、历史查询和设置，确认无启动报错。
2. 根据已批准的现场配置检查串口、站号、仪表参数和相机设置，然后连接设备。只有必需设备确认就绪后才开始实验。
3. 对照仪表核验温度、压力和继电器状态。`--`、离线或未知表示没有可用读数，不能当作零值或全部关闭。
4. 按实验室规程建立会话、完成轮次并保存。历史查询中核对实验类型、编号、原始数据和导出内容。
5. 结束实验后正常退出。若提示停止或保存失败，保留窗口、查看日志并处理故障后重试；不要把关窗口等同于设备已经停止。

异常中止后再次启动，未结束会话会标为异常并保留已有数据。记录中的恢复说明会注明：自动补写的结束时间是**恢复检测时间**，不是测得的实验结束时刻。

## 升级与备份

先结束所有实验并关闭 CPIE，再备份安装目录中的 `data/`、`configs/`、`logs/`、`exports/`。相机配置可能位于运行目录的 `config.json`，或 Windows 用户目录 `%APPDATA%\flamekit\config.json`，也应保存。

新安装器保留以上四个目录的已有内容，仅补充缺失的配置文件。已有配置不会自动覆盖，因此升级后须按新版本要求检查新增配置项。保存原安装包、校验文件及备份，完成历史数据和设备复验后再投入使用。

## 开发者源码启动

在项目根目录使用 Git 和 Python 3.9。当前本机验证版本为 3.9.6；先取得 `kevinalliswell/flame-package` 私有仓库的 Git 读取权限。

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -e modbus_multi_device_package
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe src/app.py
```

测试和打包改用 `requirements-dev.txt`，具体命令见 [构建与发布指南](BUILD_GUIDE.md)。FlameKit 从外部固定提交安装，本项目不再提供 `flame_package/` 本地安装入口。

## 常见问题

| 现象 | 处理 |
|---|---|
| FlameKit 安装提示无权限或找不到仓库 | 用当前 Git 身份确认私有仓库读取权限，再重新安装固定依赖；不要跳过 FlameKit。 |
| 程序提示已有实例 | 先检查现有 CPIE 窗口；不要并行连接同一套实验设备。 |
| 配置、数据库或日志写入失败 | 确认应用在当前用户可写目录；推荐使用默认安装位置，并检查剩余磁盘空间。 |
| 数值变成 `--` / 继电器显示未知 | 检查连接、设备响应和日志，恢复有效读数后再继续。 |
| 停止或退出失败 | 窗口保留供重试；按现场规程确认设备状态，保留日志和故障时间供排查。 |
| CI 提示缺少 `FLAMEKIT_DEPLOY_KEY` | 由维护者完成专用只读授权；当前此项仍待授权，不代表应用测试已通过。 |
