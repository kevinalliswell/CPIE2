# PR #5、#6、#7 收敛记录

核对日期：2026-09-29。远端 #6 于 2026-09-28 合入为 `3e3602f`，#7 合入为 `33bf6ac`。#5 将 `33bf6acf29db9fd701c98b34f4df0cf2ff84e354` 合入修复分支；不重写远端历史。原 dev 工作区和 stash 保留。

## 合并原则和去向

#6/#7 与 #5 均源自旧 main，包含不同的安全控制实现。先逐项吸收有效修复、执行回归，再解决 main 的冲突；不将两个控制链混用。下表中的“保留”均指最终 #5 的实现。

| 范围 | 最终处理及验证 |
| --- | --- |
| Modbus API、串口和部分连接 | 保留 Python 3.9、pymodbus 3.8.6 / slave 参数及共享串口锁。部分设备失败时保留串口用于 OFF 重试；不使用 #6 的全面断连。`test_hardware_safety`、`test_runtime_consolidation`。 |
| STOP、OFF、线程重启 | 保留 #5 执行器停止屏障：取消旧 ON、等待在途命令、确认四路 OFF、等待旧线程退出。覆盖 #6 后续 `41304d0` 的问题；不采用清空所有队列或冲刷旧 ON 的实现。失败保持 ERROR 和可重试资源。`test_hardware_safety::test_stop_waits_for_sequence_and_old_on_cannot_follow_off` 等。 |
| 离线退出 | 保留全生命周期无响应、无控制、无设备线程条件；有过响应/控制时仍要求关断。`test_offline_shutdown` 和源码/冻结 smoke。 |
| 实验完成与轮次 | 保留写库成功后清理、连续有效轮次校验、所有图片分析成功、永久最大图和失败证据；补充拒绝非终态完成。阶段阈值独立默认 20 mm，等级阈值默认 25 mm；非法配置不静默回退。`test_explosion_analysis_integrity`、`test_explosion_round_settings`、`test_round_manager_threshold`。 |
| 相机采集和延时 | 保留后台 CaptureWorker、每次尝试身份、停止取消、首帧/采集窗口与喷吹门控，覆盖 #7 后续 `42a3099` 的旧回调和同步采集问题。不采用喷吹后 GUI QTimer 才开始阻塞采集的路径；原 trigger_delay=0.5 仅作兼容保留且设置页禁用，不在本轮擅自改变喷吹关系；实际采用首帧门控，见专项审查。`test_camera_capture_worker`、`test_explosion_sequence_flow`、`test_explosion_page_flow`。 |
| 预览和标定 | 保留 `camera_workflow` 的后台预览及关闭等待，主相机资源直到工作线程退出才释放。不引入另一个未被调用的 CameraPreviewDialog。`test_calibration_lifecycle`、`test_camera_capture_worker`、`test_explosion_page_flow`。 |
| FlameKit | 使用外部不可变 `f0c3e65`，包含 capture_duration、落盘检查、取帧超时和标注契约。移除 main 恢复的两个内置副本文件；依赖仓库 94 项回归随 Windows CI 验证。 |
| 数据库/文件 | 吸收 WAL 一致性备份、先提交删除再删图片、真实会话温度和本地微秒时间。保留目录边界，外部图片不能删除。旧 schema 显式列查询和 Python 3.9 数据模型/导入修复纳入。`test_data_storage_integrity`、`test_ignition_data_integrity`、`test_services_database_columns`。 |
| 历史和报告 | 保留类型+ID 身份、排序/筛选一致；吸收会话曲线、稀疏样品位置、PDF 文本转义。修正最大火焰与平均值混用；空结论显示待确认。`test_history_identity`、`test_history_page_selection`、`test_data_storage_integrity`。 |
| 口令 | 吸收 PBKDF2 随机盐哈希和明文兼容迁移；补充原子文件替换、写失败保留旧口令、损坏配置禁止默认口令回退。确认对话框/修改入口统一。`test_password_security`。 |
| 温升速率 | 使用观测时间及单调时钟，缺少/重复/倒退时间不做速率判定；不由检测间隔或 UI 刷新间隔推测采样周期。绝对温度规则保持独立。`test_runtime_consolidation`。 |
| 切线分析 | 吸收 V3 峰顶拟合，补充有限值/严格递增时间/JSON 数值、真实会话保存、错误通道隔离。纯线性升温不报放热峰；合成曲线回归不代表标样或标准认证。`test_tangent_method_detector`、`test_tangent_analysis_dialog`。 |
| 配置/界面 | 吸收嵌套原地重置、副屏刷新、预设深拷贝、有限数值、日志处理器去重、资源定位、完整软件信息默认值；Esc 回传结果，失败图片不影响最大值行定位。`test_ui_consolidation`、`test_data_ui_boundaries`、`test_config_page_reset`。 |
| 安装和发布 | 保留 #5 普通用户安装、升级保留数据、构建失败非零、源码/冻结检查及 exact-source/SHA256 证据；不恢复硬编码旧版本和未经验证的 release 路径。`test_build_release` 和 Windows workflow。 |
| 文档和人工脚本 | 保留 #5 已核对的构建/操作指南、人工脚本隔离和测试运行时沙箱。历史优化文档以现行专项审查为准。 |

## 测试文件处理

main 新增的配置、历史身份、数据一致性、阶段阈值测试保留，并按最终接口调整。时间速率测试改用真实时间数组，文件删除测试使用应用管理目录，阶段阈值测试禁止回退到等级阈值。

以下旧实现测试不再单独保留，其行为由上述测试覆盖：`test_camera_preview_dialog.py`、`test_explosion_page_camera.py`、`test_explosion_state_machine.py`、`test_flamekit_capture_duration.py`。前两项依赖已替换的预览/GUI 定时器接口；状态机旧测试要求停止时冲刷队列、自动恢复等与安全屏障冲突；内置 FlameKit 测试改由固定依赖仓库的完整测试集承担。未以删除测试来接受旧实现的失败。

## 验收边界

本次交付为候选版本。Windows CI 必须覆盖合并后的最新提交；此前 `186dcfa` 包及其 SHA256 仅为历史证据。实机相机吞吐、继电器/仪表、异常关断、标样曲线和完整流程仍须按 HARDWARE_ACCEPTANCE.md 验收。2026-09-30 维护者明确授权先合并并发布 v1.2.1，暂时结束开发；此决定替代此前保持草稿和等待真机验收后发布的安排。真机验收状态保持待完成。
