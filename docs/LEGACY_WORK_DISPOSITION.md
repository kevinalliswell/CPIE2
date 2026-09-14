# 旧工作去向与收尾边界

盘点日期：2026-09-13。收敛基线为 `origin/main` 的 `b0c31bc2358b0e8222b0f36d47d07d4b6e7761f9`（v1.2.0），收敛分支为 `codex/closeout-stabilization`。本表记录工作去向，不代表 Windows 实机、相机或完整实验已验收。

## 备份与恢复入口

原仓库同级保留本地目录 `CPIE2-closeout-backup-20260913-174209`。同级的 `CPIE2-closeout-backup-latest.txt` 是本机定位文件；这些备份不上传到项目仓库。

- `repository.bundle` 保存当时的分支、标签和 `refs/stash`，已通过 `git bundle verify`；stash 的第三父提交包含当时未跟踪文件。
- `working-tree.patch`、`index.patch`、`refs.txt`、`status.txt`、`stash.txt` 保存迁移差异和引用状态。
- `untracked-audit-documents.tar.gz` 保存原工作区未跟踪的审计文档。
- `configs/` 和 `databases/` 保存配置及通过 SQLite backup API 生成的数据库副本。
- `SHA256SUMS.json` 是校验清单，`RESTORE.md` 说明恢复方式。恢复应使用独立目录，先核验清单，再核对引用和差异。

原 dev 工作区、stash、数据、环境和旧产物仍保留。没有为清空列表删除分支、覆盖远端标签或丢弃 stash。虚拟环境和旧构建产物不作为源码迁移内容。

## dev 独有的三个提交

审计时 `origin/main...origin/dev` 为 main 独有 5 个提交、dev 独有 3 个提交。应用收敛直接建立在 main 上，保留 PR #4 的修复；不把旧 dev 的应用快照覆盖到 main。

| 提交 | 独有内容 | 当前去向 |
|---|---|---|
| `b0b6d07` | `flame_package/flamekit/camera.py` 的全帧内存缓冲采集 | 9 月 13 日以外部 FlameKit 提交 `114f457c46689180a33fa1122809e926ec46de12` 核对，与 dev 文件字节相同。9 月 14 日在此外部版本之上修复采集完整性、内存预算、落盘及生命周期问题，当前不可变提交见 requirements.txt 和专项审查；保留采集后落盘方式，不重新合入内置副本。 |
| `19c0b4b` | 嵌套 `CPIE2/flame_package/` 下的 `.github/workflows/release.yml`、`.gitignore`、`CHANGELOG.md` | 独立包整理时的遗留副本，不在 main 基线，也不带入收敛分支；内容保存在 dev 和 bundle。 |
| `9b7567f` | `flame_package/` 下的 release workflow、gitignore、changelog、README、license 调整和 `__version__=1.1.2` | 属于 FlameKit 独立包发行材料。应用使用外部固定提交，不保留一套独立包发行流程；旧材料保存在 dev 和 bundle。未据此声称这些材料已在上游发布。 |

所选外部 FlameKit 源码对应原上游 `v1.1.3` 引用，但其安装元数据实际仍为 **1.1.2**。应用以不可变提交固定依赖并记录来源，不能把 tag 名直接写成运行时包版本。

## 原工作区未提交的 FlameKit 迁移

原 dev 工作区有 36 个已跟踪文件改动（+101 / -7,268 行），其中删除 30 个 `flame_package/` 文件，修改以下 6 个应用文件。当前分支按迁移目的重新整合，未直接套用旧 dev 的整包 diff。

| 原改动 | 收敛处理 |
|---|---|
| `requirements.txt`：改用上游 FlameKit | 已纳入，并将依赖固定到完整提交 SHA；与本次经过安装验证的运行依赖版本一起管理。 |
| `build_release.py`：从已安装包定位 FlameKit | 已纳入，并补充构建失败阻断、依赖/源码来源记录和产物验证。 |
| `.github/workflows/release.yml`：取消 editable 安装内置 FlameKit | 已纳入应用构建与验证流程；本地 Modbus 包仍属于应用交付依赖。 |
| `README.md`、`QUICK_START.md`、`BUILD_GUIDE.md` | 安装说明纳入当前交付文档；以当前固定提交和实际版本为准，不保留旧构建指南中的对话残片或“运行时版本一定是 1.1.3”的说法。 |
| 删除内置 `flame_package/` | 已纳入。main 的内置包原有 26 个文件，dev 的 30 个文件包括上述独有发行材料，因此两个分支的删除数量不同。 |
| 未跟踪 `.venv-migration-check/` | 只作原机迁移验证环境保留，不提交或作为用户安装输入；收敛分支使用独立重建的验证环境。 |

## stash 逐项去向

`stash@{0}` 的说明是 `pre-push cleanup before publishing dev`，固定提交为 `9f026385da058b16cf6788929ef82f6db911b7d2`；未跟踪文件父提交为 `3e25d87b461f4df3ea16ca74f12e100fda8d83c2`。后续新增 stash 可能改变序号，恢复时应使用固定 SHA 核对。

这批变更是 **Modbus 独立包的发布准备**，未全部合入 CPIE 应用。当前应用修复了内置 Modbus 运行逻辑、依赖接口与硬件安全测试；这不等于已完成 Modbus 的独立 PyPI 发布。以下文件均保留在 stash 和 bundle 中，独立包维护可另行恢复审查。

| stash 类别 | 文件 | 内容与处理 |
|---|---|---|
| 已跟踪修改 | `.gitignore` | 忽略临时 `flame-package/` 提取目录；该目录不是当前应用构建输入，原规则保留在备份。 |
| 已跟踪修改 | `modbus_multi_device_package/.gitignore` | 增加 ruff、coverage、Python 环境忽略规则；独立包维护材料，未整批套入应用。 |
| 已跟踪修改 | `modbus_multi_device_package/CHANGELOG.md` | 独立包 Unreleased / 1.0.1 条目；内容不作为已发布证明，保留备份。 |
| 已跟踪修改 | `modbus_multi_device_package/MANIFEST.in` | readme 文件名改为 README.md；须与独立包文档和打包元数据一起恢复，不能单独套入。 |
| stash 新增已跟踪树文件 | `modbus_multi_device_package/README.md` | 新的包级说明；保留备份，不替代本次 CPIE 操作说明。 |
| 已跟踪修改 | `modbus_multi_device_package/pyproject.toml` | 动态版本、PyPI 元数据、dev 依赖、pytest/coverage 配置；独立包发布准备，保留备份。当前应用依赖锁定不直接复用其宽泛兼容范围。 |
| 已跟踪修改 | `modbus_multi_device_package/readme.md` | 缩减原说明并引导新 README；必须与上项文档配套，保留备份。 |
| 未跟踪文件 | `.github/workflows/modbus-package-ci.yml` | 独立包级 CI 草稿；本次 CPIE 使用应用级 Windows 验证工作流，不将草稿当作已经执行的检查。 |
| 未跟踪文件 | `.github/workflows/modbus-package-publish.yml` | `modbus-v*`/手动触发并上传 PyPI 的草稿；不纳入应用 Release，也不启用发布凭证。 |
| 未跟踪文件 | `modbus_multi_device_package/CONTRIBUTING.md` | 独立包贡献说明，保留备份。 |
| 未跟踪文件 | `modbus_multi_device_package/tests/test_package_metadata.py` | 版本号格式测试；保留独立包工作，不能代替本次设备协议和关断回归测试。 |

## 标签和已合并分支

| 对象 | 核实状态 | 去向 |
|---|---|---|
| 本地 `v1.1.2` | `19c0b4b1d75d600d86c61f93595f4091f7a85e06` | 原引用已保存到 bundle/refs 清单；不推送此本地标签覆盖远端。 |
| 远端 `v1.1.2` | `db124d5df2615b9653e432b87b9a2d459c3efa92` | 保持远端；旧 Release 同名版本包含两次不同 SHA 的构建资产（另一次为 `5bbd431`），使用前须核对具体构建时间和来源。后续发布使用新版本号，不复用旧标签。 |
| `claude/zealous-dijkstra-j1cv24` | `7678238`，已通过 [PR #4](https://github.com/kevinalliswell/CPIE2/pull/4) 合入 main | 内容已在收敛基线。待当前变更合并、验收和保全完成后可清理；本轮未删远端分支。 |
| `claude/review-cpie2-codebase-U2UAQ` | 远端已删除，内容已在历史合并中 | fetch 已清理旧远端跟踪引用，无需重新创建分支。 |
| 本地 `backup/main-before-msg-fix` | 初始提交 `bb71b8a` | 作为历史保留，不视为未交付功能。 |
| dev | 仍保留 `9b7567f` 及原 dirty 工作区 | 三个独有提交和迁移去向已在本表记录；不会在当前修复未验收前删除或重置。 |

本表的收口标准是每项旧工作有可追溯的保留或整合位置。独立包发布准备不阻塞 CPIE 应用本身的结项；设备控制、数据正确性、可重复构建和 Windows 实机验收仍必须完成。
