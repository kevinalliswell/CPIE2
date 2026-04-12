# CPIE2 项目开发文档（反向工程版）
# Multi-Agent 科学仪器软件开发模板

> **文档用途**：本文档从 CPIE 2.0 完成代码库反向推导出完整的开发流程、角色职责、任务分解和 Multi-Agent 协作框架，可直接作为同类工业科学仪器软件项目的开发模板。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构总览](#2-技术架构总览)
3. [代码库结构与模块规模](#3-代码库结构与模块规模)
4. [角色定义与 Agent 映射](#4-角色定义与-agent-映射)
5. [开发阶段与里程碑](#5-开发阶段与里程碑)
6. [模块任务分解（WBS）](#6-模块任务分解wbs)
7. [Multi-Agent 工作流设计](#7-multi-agent-工作流设计)
8. [Agent 提示词模板库](#8-agent-提示词模板库)
9. [模块间依赖关系](#9-模块间依赖关系)
10. [质量标准与验收准则](#10-质量标准与验收准则)
11. [同类项目复用指南](#11-同类项目复用指南)

---

## 1. 项目概述

### 1.1 项目基本信息

| 字段 | 内容 |
|------|------|
| **项目名称** | CPIE 2.0 — 煤粉着火点及爆炸性检测系统 |
| **项目类型** | 工业科学仪器控制软件（桌面 GUI） |
| **目标平台** | Windows 10/11、macOS 10.15+、Linux Ubuntu 20.04+ |
| **开发语言** | Python 3.10+ |
| **UI 框架** | PySide6（Qt6） |
| **数据库** | SQLite 3 |
| **通信协议** | RS-485 / Modbus RTU |
| **代码规模** | ~27,000 行源码（src/），~3,500 行测试 |
| **版本** | v1.1.251121 |

### 1.2 系统核心功能（从代码逆向）

```
CPIE 2.0
├── 着火点检测实验（Ignition）
│   ├── 6 路样品温度采集（200°C–500°C）
│   ├── 切线法 / 温升速率法自动检测着火点
│   ├── 实时曲线显示（PyQtGraph）
│   └── 实验报告生成（Word .docx）
│
├── 爆炸性实验（Explosion）
│   ├── 8 步时序继电器控制
│   ├── 工业相机火焰图像采集（MVS SDK）
│   ├── 火焰长度分析（OpenCV）
│   ├── 多轮次（5~10 轮）自动统计
│   └── 爆炸性等级判定（无/弱/强/超强）
│
├── 历史数据管理
│   ├── 实验会话查询 / 筛选
│   ├── 数据导出（CSV / Word 报告）
│   └── 切线法补充分析
│
└── 系统配置
    ├── 串口设备配置
    ├── 实验参数配置（YAML）
    └── 副屏（触摸屏）监控
```

### 1.3 硬件集成清单

| 设备 | 协议 | 地址 | 用途 |
|------|------|------|------|
| 宇电温控仪表（着火点） | Modbus RTU | addr 4 | PV/SV/MV 读取，程序段设置 |
| 6 路温度模块 | Modbus RTU | addr 5 | 样品温度采集 |
| 宇电温控仪表（爆炸） | Modbus RTU | addr 2 | 炉温控制 |
| 压力仪表 | Modbus RTU | addr 1 | 罐内压力采集 |
| 继电器模块 | Modbus RTU | addr 3 | 喷吹/清吹/抽真空控制 |
| 迈德威视工业相机 | USB (MVS SDK) | — | 火焰图像采集 |

---

## 2. 技术架构总览

### 2.1 分层架构（从代码推导）

```
┌─────────────────────────────────────────────────────┐
│                   View Layer（视图层）                 │
│  main_window → pages → dialogs → widgets → ui_components │
│               PySide6 / PyQtGraph / Matplotlib       │
├─────────────────────────────────────────────────────┤
│                Controller Layer（控制层）              │
│       ignition_controller  ←→  explosion_controller  │
│     状态机管理 / 信号发布 / 硬件调度 / 数据库代理        │
├─────────────────────────────────────────────────────┤
│                 Service Layer（服务层）                │
│  IgnitionDetectionService  FlameAnalysisHandler      │
│  DataCollectionService     RoundManager              │
│  TemperatureConditionValidator  ExperimentValidator  │
├─────────────────────────────────────────────────────┤
│                  Model Layer（模型层）                 │
│    IgnitionDatabase    ExplosionDatabase             │
│    IgnitionExperiment  ExplosionExperiment           │
│    ExperimentStates（状态枚举 + 转换规则）              │
├─────────────────────────────────────────────────────┤
│                  Utils Layer（工具层）                 │
│  PathManager  TangentMethodDetector  DataSaver       │
│  Logger  PasswordManager                             │
├─────────────────────────────────────────────────────┤
│               Hardware Packages（硬件包）              │
│   flamekit（MVS 相机 SDK 封装）                       │
│   modbus_multi_device（多设备 Modbus 管理器）          │
└─────────────────────────────────────────────────────┘
```

### 2.2 状态机设计（核心架构决策）

**着火点实验状态机：**
```
IDLE → CONNECTED → PREPARED → RUNNING → STOPPED → COMPLETED
                                     ↘ CANCELLED
                                     ↘ ERROR
```

**爆炸性实验状态机：**
```
IDLE → CONNECTED → SESSION_CREATED → SEQUENCE_RUNNING → WAITING_ANALYSIS → COMPLETED
                         ↑__________________↙              ↘ CANCELLED
                                                           ↘ ERROR
```

### 2.3 信号/槽通信模式

```python
# Controller 发出信号（解耦视图与控制）
controller.experiment_created.connect(page._on_experiment_created)
controller.state_changed.connect(page._update_ui_state)
controller.log_message.connect(page._append_log)
controller.sample_temps_updated.connect(panel._refresh_temps)
```

---

## 3. 代码库结构与模块规模

### 3.1 完整文件树

```
CPIE2/
├── src/                              # 主源码（~27,000 行）
│   ├── controllers/                  # 控制层 (2 文件, ~1,376 行)
│   │   ├── explosion_controller.py   # 701 行：爆炸实验控制器
│   │   └── ignition_controller.py    # 675 行：着火点实验控制器
│   │
│   ├── models/                       # 数据层 (6 文件, ~4,800 行)
│   │   ├── ignition_database.py      # 1,512 行：着火点数据库
│   │   ├── explosion_database.py     # 1,396 行：爆炸性数据库
│   │   ├── ignition_experiment.py    # 实验数据模型
│   │   ├── explosion_experiment.py   # 实验数据模型
│   │   ├── experiment_states.py      # 271 行：状态枚举
│   │   └── data_handler.py           # 通用数据处理
│   │
│   ├── services/                     # 服务层 (8 文件)
│   │   ├── ignition/
│   │   │   ├── data_collection_service.py
│   │   │   ├── ignition_detection_service.py
│   │   │   └── temperature_condition_validator.py
│   │   └── explosion/
│   │       ├── flame_analysis_handler.py
│   │       ├── round_manager.py
│   │       └── experiment_validator.py
│   │
│   ├── views/                        # 视图层 (71 文件, ~13,000 行)
│   │   ├── main_window.py            # 主窗口 (397 行)
│   │   ├── pages/
│   │   │   ├── explosion_page.py     # 1,816 行
│   │   │   ├── history_query_page.py # 1,626 行
│   │   │   ├── ignition_page.py      # 878 行
│   │   │   ├── config_page.py        # 1,008 行
│   │   │   ├── home_page.py
│   │   │   ├── help_page.py
│   │   │   └── about_page.py
│   │   ├── dialogs/
│   │   │   ├── generate_report_dialog.py  # 1,710 行
│   │   │   ├── tangent_analysis_dialog.py # 747 行
│   │   │   ├── manual_confirm_dialog.py   # 774 行
│   │   │   ├── flame_analyzer/            # 火焰分析器组件
│   │   │   ├── ignition_experiment_dialog.py
│   │   │   └── explosion_experiment_dialog.py
│   │   ├── widgets/
│   │   │   ├── ignition/              # 着火点专用控件
│   │   │   └── explosion/             # 爆炸性专用控件
│   │   └── ui_components/
│   │       └── monitor_panels/        # 实时监控面板
│   │
│   └── utils/                        # 工具层 (6 文件)
│       ├── tangent_method_detector.py # 821 行：切线算法
│       ├── path_manager.py           # 路径统一管理
│       ├── data_saver.py             # 数据持久化
│       └── logger.py
│
├── flame_package/                    # 本地包：相机 SDK 封装
│   └── flamekit/mvsdk.py             # 2,497 行
├── modbus_multi_device_package/      # 本地包：Modbus 多设备管理
├── tests/                            # 测试套件 (16 文件, ~3,500 行)
├── configs/                          # 配置文件 (5 文件)
│   ├── experiment_config.yaml        # 主实验参数
│   ├── flame_analyzer_config.yaml    # 火焰分析参数
│   └── system.yaml
├── resources/                        # UI 资源 (样式/图标/模板)
├── docs/                             # 技术文档 (26 篇)
└── plan/                             # 开发计划文档 (21 篇)
```

---

## 4. 角色定义与 Agent 映射

### 4.1 角色总览

| Agent ID | 角色名称 | 职责范围 | 产出物 |
|----------|----------|----------|--------|
| `agent-pm` | 产品经理 | 需求分析、用户故事、验收标准 | PRD、用户故事、功能清单 |
| `agent-arch` | 系统架构师 | 架构设计、数据库 schema、API 接口定义 | 架构文档、ER 图、接口规范 |
| `agent-hw` | 硬件集成工程师 | 串口/Modbus 通信、设备驱动封装 | 本地硬件包、设备配置 YAML |
| `agent-model` | 数据库/模型工程师 | SQLite 建表、ORM 方法、数据迁移 | models/ 目录 |
| `agent-service` | 业务服务工程师 | 核心算法、状态机、业务规则 | services/ + controllers/ |
| `agent-ui` | 前端/UI 工程师 | 页面布局、组件开发、信号/槽连接 | views/ 目录 |
| `agent-algo` | 算法工程师 | 科学计算算法（切线法等） | utils/ 中的算法文件 |
| `agent-test` | 测试工程师 | 单元测试、集成测试、测试数据 | tests/ 目录 |
| `agent-doc` | 技术文档工程师 | 接口文档、用户手册、帮助页面 | docs/ + help HTML |
| `agent-review` | 代码审查工程师 | 代码质量、架构合规、安全检查 | review 报告 + PR 修改 |
| `agent-build` | 构建/发布工程师 | 打包脚本、依赖管理、发布流程 | build_release.py、requirements.txt |

### 4.2 角色协作矩阵

```
                agent-pm
                    │
                    ▼
              agent-arch  ──────────────────┐
              │        │                    │
         agent-hw   agent-model          agent-algo
              │        │                    │
              └────────┴────────────────────┘
                        │
                   agent-service
                        │
                   agent-ui
                        │
                   agent-test ◄──── agent-review
                        │
                   agent-doc
                        │
                   agent-build
```

---

## 5. 开发阶段与里程碑

### Phase 0：项目启动（~3 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 需求调研与功能清单确认 | `agent-pm` | PRD v1.0 |
| 硬件清单与通信协议确认 | `agent-hw` | 硬件规格书 |
| 技术选型决策 | `agent-arch` | 技术栈文档 |
| 项目脚手架初始化 | `agent-arch` | 目录结构、.gitignore、requirements.txt |

### Phase 1：基础设施（~5 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 数据库 schema 设计 | `agent-arch` + `agent-model` | ER 图 + migrations |
| 路径管理工具 | `agent-model` | `utils/path_manager.py` |
| 日志系统 | `agent-model` | `utils/logger.py` |
| Modbus 多设备包 | `agent-hw` | `modbus_multi_device_package/` |
| 相机 SDK 封装 | `agent-hw` | `flame_package/` |
| YAML 配置文件设计 | `agent-arch` | `configs/*.yaml` |

### Phase 2：核心模型层（~7 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 着火点数据库实现 | `agent-model` | `models/ignition_database.py` |
| 爆炸性数据库实现 | `agent-model` | `models/explosion_database.py` |
| 实验状态机设计 | `agent-service` | `models/experiment_states.py` |
| 数据模型类 | `agent-model` | `models/ignition_experiment.py` 等 |
| 单元测试（数据库） | `agent-test` | `tests/test_*_database.py` |

### Phase 3：业务服务层（~10 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 着火点检测算法 | `agent-algo` | `utils/tangent_method_detector.py` |
| 着火点检测服务 | `agent-service` | `services/ignition/ignition_detection_service.py` |
| 数据采集服务 | `agent-service` | `services/ignition/data_collection_service.py` |
| 温度条件验证器 | `agent-service` | `services/ignition/temperature_condition_validator.py` |
| 火焰分析处理器 | `agent-service` | `services/explosion/flame_analysis_handler.py` |
| 多轮次管理器 | `agent-service` | `services/explosion/round_manager.py` |
| 实验验证器 | `agent-service` | `services/explosion/experiment_validator.py` |
| 单元测试（算法） | `agent-test` | `tests/test_tangent_*.py` |

### Phase 4：控制层（~7 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 着火点控制器 | `agent-service` | `controllers/ignition_controller.py` |
| 爆炸性控制器 | `agent-service` | `controllers/explosion_controller.py` |
| 状态机集成测试 | `agent-test` | `tests/test_ignition_experiment_logic.py` |
| 控制器信号/槽规范 | `agent-arch` | 信号接口文档 |

### Phase 5：视图层（~15 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 主窗口框架 | `agent-ui` | `views/main_window.py` |
| 着火点实验页面 | `agent-ui` | `views/pages/ignition_page.py` |
| 爆炸性实验页面 | `agent-ui` | `views/pages/explosion_page.py` |
| 历史数据查询页面 | `agent-ui` | `views/pages/history_query_page.py` |
| 配置页面 | `agent-ui` | `views/pages/config_page.py` |
| 实验新建对话框 | `agent-ui` | `views/dialogs/*_experiment_dialog.py` |
| 报告生成对话框 | `agent-ui` | `views/dialogs/generate_report_dialog.py` |
| 切线分析对话框 | `agent-ui` | `views/dialogs/tangent_analysis_dialog.py` |
| 着火点专用控件 | `agent-ui` | `views/widgets/ignition/` |
| 爆炸性专用控件 | `agent-ui` | `views/widgets/explosion/` |
| 副屏监控面板 | `agent-ui` | `views/ui_components/monitor_panels/` |
| 整体 UI 测试 | `agent-test` | `tests/test_*_button_states.py` |

### Phase 6：集成与优化（~7 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| 端到端流程测试 | `agent-test` | 集成测试报告 |
| 代码架构审查 | `agent-review` | review 报告 |
| 性能优化 | `agent-service` + `agent-ui` | 优化提交 |
| 报告模板制作 | `agent-doc` | `resources/templates/` |
| 帮助文档 HTML | `agent-doc` | `resources/help/` |

### Phase 7：打包发布（~3 天）

| 任务 | 负责 Agent | 产出 |
|------|-----------|------|
| PyInstaller 脚本 | `agent-build` | `build_release.py` |
| 依赖清单最终版 | `agent-build` | `requirements.txt` |
| 发布包测试 | `agent-test` | 安装验证 |
| README + 快速指南 | `agent-doc` | README.md、QUICK_START.md |

---

## 6. 模块任务分解（WBS）

### 6.1 数据库模块（`agent-model` 负责）

```yaml
DB-001: 初始化 SQLite 连接 + schema_version 检查
DB-002: experiment_sessions 表（id, experiment_id, start_time, status, ...）
DB-003: ignition_data 表（pv, ch1-ch6, session_id, timestamp）
DB-004: ignition_detection 表（session_id, channel, temperature, method, confidence）
DB-005: explosion_sessions 表（session_id, total_rounds, avg_flame_length, explosion_level）
DB-006: test_rounds 表（session_id, round_number, flame_length, image_path）
DB-007: CRUD 方法实现（start_session, insert_data, get_session, finalize）
DB-008: 聚合查询方法（calculate_average, classify_explosion_strength）
DB-009: 数据库迁移脚本
DB-010: 单元测试覆盖所有公开方法
```

### 6.2 控制器模块（`agent-service` 负责）

```yaml
CTRL-001: 设备连接（后台线程）
CTRL-002: create_experiment（创建 DB 会话 + 状态转换）
CTRL-003: start_experiment（前置条件检查 + 状态机）
CTRL-004: stop_experiment（停止采集，保持设备在线）
CTRL-005: 数据采集定时器（500ms 轮询）
CTRL-006: 设备数据轮询 + 信号发布
CTRL-007: 数据库代理方法（DB 操作不暴露给 View）
CTRL-008: cleanup（资源释放）
CTRL-009: 状态转换日志
CTRL-010: 异常处理 + 错误信号
```

### 6.3 着火点实验页面（`agent-ui` 负责）

```yaml
IGN-UI-001: 页面布局（左控制面板 + 右图表区）
IGN-UI-002: 新建实验按钮 + 对话框触发
IGN-UI-003: 启动/停止/完成按钮状态机
IGN-UI-004: 实时温度曲线（6 路 PyQtGraph）
IGN-UI-005: 样品温度显示面板（6 通道）
IGN-UI-006: 着火点标注（在曲线上标注检测点）
IGN-UI-007: 日志文本区域（实时追加）
IGN-UI-008: 数据采集定时器（500ms）
IGN-UI-009: 完成实验流程（确认 + finalize + reset）
IGN-UI-010: 副屏监控连接
```

### 6.4 爆炸性实验页面（`agent-ui` 负责）

```yaml
EXP-UI-001: 页面布局（控制区 + 轮次记录卡 + 监控区）
EXP-UI-002: 新建实验对话框
EXP-UI-003: 启动时序按钮 + 状态联动
EXP-UI-004: 火焰图像实时显示
EXP-UI-005: 轮次记录面板（round_number / flame_length / 图片预览）
EXP-UI-006: 会话恢复（从 DB 加载历史轮次 + 同步控制器计数）
EXP-UI-007: 5 轮决策弹窗（继续 or 完成）
EXP-UI-008: 完成实验弹窗（汇总 + finalize）
EXP-UI-009: 压力实时显示
EXP-UI-010: 继电器状态指示灯
```

### 6.5 切线法算法（`agent-algo` 负责）

```yaml
ALGO-001: 数据预处理（平滑滤波）
ALGO-002: 斜率计算（最小二乘拟合）
ALGO-003: 切线方程求解
ALGO-004: 着火点温度计算
ALGO-005: 置信度评估（R²）
ALGO-006: 低置信度回退（使用实时检测结果）
ALGO-007: 结果可视化（切线图像生成）
ALGO-008: 单元测试（已知数据集验证）
```

---

## 7. Multi-Agent 工作流设计

### 7.1 并行开发策略

以下模块可以**并行启动**（无上下游依赖）：

```
Phase 1 并行组：
├── agent-hw  ──── 硬件包开发
├── agent-arch ─── 配置文件设计
└── agent-model ── 路径/日志工具

Phase 2 并行组（Phase 1 完成后）：
├── agent-model ── 数据库实现
├── agent-service ─ 状态机设计
└── agent-algo ─── 算法预研

Phase 3 并行组（Phase 2 完成后）：
├── agent-service ─ 服务层 + 控制器
└── agent-test ─── 数据库单元测试

Phase 5 并行组（Phase 4 完成后）：
├── agent-ui ────── 各页面并行（不同文件）
│   ├── ignition_page.py
│   ├── explosion_page.py
│   └── history_query_page.py
├── agent-doc ───── 文档编写
└── agent-test ──── 持续测试
```

### 7.2 Agent 交接协议

每个 Agent 完成任务后，需提交以下交接物：

```markdown
## 交接清单
- [ ] 代码文件（路径 + 行数）
- [ ] 对外接口文档（类/方法签名）
- [ ] 配置项说明（YAML key 名称和类型）
- [ ] 已知限制 / TODO 项
- [ ] 测试覆盖情况
```

### 7.3 代码规范约定（Agent 间共识）

```python
# 1. 所有信号在 Controller 定义，View 只订阅
controller.data_updated.connect(view.refresh)

# 2. View 不直接访问数据库，通过 Controller 代理
# ❌ 错误
data = self.controller.db.get_sessions()
# ✅ 正确
data = self.controller.get_sessions()

# 3. 业务逻辑在 Service 层，不在 View 层
# ❌ 错误（在 Page 里判断着火）
if temp > 400 and rate > 0.5:
    mark_ignition()
# ✅ 正确
results = self.ignition_detector.check_ignition(history, flags, interval)

# 4. 硬编码值统一放 YAML，代码用 config.get() 读取
threshold = self.config.get('ignition_detection', {}).get('threshold', 400.0)

# 5. 状态转换必须通过状态机验证
if self.current_state.can_start():
    self._set_state(RunningState)
```

---

## 8. Agent 提示词模板库

### 8.1 产品经理 Agent（agent-pm）

```
你是一位工业科学仪器软件的产品经理。

【项目背景】
{项目名称} 是一款 {检测对象} 的自动化检测系统，部署在实验室环境。
目标用户：实验员（操作实验）、管理员（查询历史数据、生成报告）。

【硬件环境】
{列出硬件清单：设备名、协议、用途}

【你的任务】
请基于以下需求描述，生成：
1. 功能清单（带优先级 P0/P1/P2）
2. 用户故事（格式：作为[角色]，我希望[功能]，以便[价值]）
3. 实验流程图（Mermaid 格式）
4. 验收标准（可测试的具体条件）

【需求描述】
{用户需求原始描述}
```

### 8.2 系统架构师 Agent（agent-arch）

```
你是一位经验丰富的 Python 桌面应用架构师，专注于科学仪器控制软件。

【技术约束】
- 语言：Python 3.10+
- UI：PySide6（Qt6）
- 数据库：SQLite（离线，单机）
- 通信：Modbus RTU over RS-485
- 打包：PyInstaller（跨平台可执行文件）

【参考架构模式】
分层架构：View → Controller → Service → Model → Utils → Hardware Packages
状态机：每个实验类型维护独立状态枚举（含转换验证）
信号驱动：Controller 通过 PySide6 Signal 通知 View

【你的任务】
为 {项目名称} 设计：
1. 目录结构（包含文件名、行数估计、职责）
2. 数据库 ER 图（Mermaid）
3. 状态机定义（状态名、转换规则、UI 颜色）
4. 关键类的接口签名（不写实现）
5. YAML 配置文件结构

【功能清单】
{agent-pm 输出的功能清单}
```

### 8.3 硬件集成 Agent（agent-hw）

```
你是一位工业通信协议专家，擅长 Python + Modbus RTU 集成。

【任务】
为以下设备开发 Python 封装包，放在 {package_name}/ 目录：
- 包结构：setup.py + pyproject.toml + 主模块
- 核心类：{DeviceManager}，支持多设备并发轮询
- 数据格式：get_latest_data(device_name) 返回标准 dict
- 控制接口：send_control(device_name, control_data, priority)
- 线程安全：使用 threading.Lock 保护数据
- 配置驱动：设备参数从 dict（YAML 加载后传入）

【设备清单】
{设备名 | 协议 | 地址 | 寄存器映射}

【要求】
- 不依赖特定串口名（从配置读取）
- 连接失败有重试逻辑
- 每个设备独立轮询线程
- 提供 connect()、start()、stop()、close() 生命周期方法
```

### 8.4 数据库/模型 Agent（agent-model）

```
你是一位 Python SQLite 数据库专家。

【任务】
为 {实验类型} 实现数据库类 {ExperimentDatabase}，放在 src/models/{name}_database.py。

【技术要求】
- SQLite3，支持 WAL 模式和 Foreign Keys
- schema_version 表，支持未来升级
- 所有写操作带事务和 rollback
- SQL 注入防护（参数化查询，order_by 白名单）
- 类方法返回 dict 而非 Row（JSON 序列化友好）
- 异常记录到 logger，不上抛（返回 -1 或 None）

【需要实现的方法】
{列出方法签名和描述}

【表结构设计】
{ER 图或字段描述}

【配置参数】
{从 YAML 读取的阈值参数，如爆炸性等级阈值}
```

### 8.5 业务服务 Agent（agent-service）

```
你是一位 Python 后端工程师，负责业务逻辑层。

【架构规则】
- Service 类不依赖 Qt（纯 Python，可单元测试）
- Controller 类继承 QObject，管理 Signal + 状态机
- Controller 不直接被 View 调用数据库，提供代理方法
- 状态转换必须经过 _set_state() 并验证合法性

【任务】
实现 {ControllerName}（src/controllers/{name}_controller.py）：

必须包含：
1. 信号定义（device_connected, experiment_created, state_changed, log_message 等）
2. __init__（config 驱动，初始化 db + 状态机 + 定时器）
3. connect_devices()（后台线程）
4. create_experiment(config: dict)
5. start_experiment() / stop_experiment()
6. 数据库代理方法（不暴露 self.db 给外部）
7. cleanup()（停止所有资源）

【状态机】
{状态枚举名和转换规则}

【依赖的 Service 类】
{列出需要调用的 Service 类}
```

### 8.6 UI 工程师 Agent（agent-ui）

```
你是一位 PySide6 UI 工程师，专注于科学仪器控制软件的操作界面。

【UI 规范】
- 深色主题（背景 #1a1a2e，卡片 #16213e，强调 #0f3460）
- 实时数据用 PyQtGraph（不用 Matplotlib，性能更好）
- 大按钮（高度 >= 40px），操作员戴手套也能点
- 日志区域固定在页面底部，自动滚动
- 状态文字带颜色编码（运行=绿，停止=黄，错误=红）

【架构规则】
- View 不持有业务逻辑，只做显示和用户输入
- View 通过 controller.signal.connect() 接收数据
- View 调用 controller.method() 发起操作
- 不直接访问 controller.db

【任务】
实现 {PageName}（src/views/pages/{name}_page.py）：

页面功能：
{列出该页面需要展示的数据和用户操作}

需要连接的 Controller 信号：
{信号名 → 对应的 UI 更新方法}

需要调用的 Controller 方法：
{按钮 → 方法名}
```

### 8.7 算法工程师 Agent（agent-algo）

```
你是一位科学计算工程师，擅长 Python + NumPy/SciPy 数值算法。

【任务】
实现 {AlgorithmName}（src/utils/{name}.py）。

【算法描述】
{算法的物理/数学原理，输入输出规格}

【要求】
- 纯 Python（不依赖 Qt），可独立单元测试
- 输入：numpy array 或 list
- 输出：标准 dict（含结果值 + 置信度/质量指标）
- 边界情况处理（数据不足、全零、NaN）
- 提供 visualize() 方法返回 matplotlib Figure（供 UI 展示）
- 每个公开方法写 docstring（参数/返回/异常）

【测试数据】
{已知输入 → 预期输出，用于验证}
```

### 8.8 测试工程师 Agent（agent-test）

```
你是一位 Python 测试工程师。

【测试规范】
- 使用 unittest（无需 pytest，减少依赖）
- 数据库测试使用内存数据库（:memory:）
- UI 测试使用 QApplication + mock 硬件
- 测试文件命名：test_{module_name}.py

【任务】
为以下模块编写完整测试（src → tests/test_{name}.py）：

{被测模块的类名和公开方法列表}

必须覆盖：
1. 正常流程（happy path）
2. 边界值（空输入、最大值、零值）
3. 异常流程（数据库错误、硬件断线）
4. 状态机非法转换

每个测试方法命名格式：test_{method}_{scenario}_{expected}
例：test_create_experiment_with_valid_config_returns_true
```

### 8.9 代码审查 Agent（agent-review）

```
你是一位资深 Python 代码审查工程师，专注于工业软件质量。

【审查清单】
架构合规：
- [ ] View 层没有直接访问数据库（搜索 controller.db.）
- [ ] 业务逻辑没有写在 View 层（搜索页面文件中的算法代码）
- [ ] 所有硬编码数值来自 config.get()
- [ ] 状态转换通过 _set_state() 并有合法性验证

安全性：
- [ ] SQL 使用参数化查询，没有字符串拼接
- [ ] order_by 字段有白名单验证
- [ ] 用户输入有长度/类型验证

健壮性：
- [ ] 所有 DB 写操作有 try/except + rollback
- [ ] 所有硬件调用有超时和异常处理
- [ ] 定时器和线程在 cleanup() 中正确释放

【任务】
审查以下文件，对每个问题给出：
- 问题位置（文件:行号）
- 问题描述
- 修复建议（含代码示例）

{待审查文件列表}
```

---

## 9. 模块间依赖关系

### 9.1 导入依赖图

```
main.py
 └── views/main_window.py
      ├── views/pages/ignition_page.py
      │    ├── controllers/ignition_controller.py
      │    │    ├── models/ignition_database.py
      │    │    │    └── utils/path_manager.py
      │    │    └── models/experiment_states.py
      │    ├── services/ignition/ignition_detection_service.py
      │    ├── services/ignition/data_collection_service.py
      │    ├── services/ignition/temperature_condition_validator.py
      │    └── utils/tangent_method_detector.py
      │
      ├── views/pages/explosion_page.py
      │    ├── controllers/explosion_controller.py
      │    │    ├── models/explosion_database.py
      │    │    ├── models/experiment_states.py
      │    │    ├── flamekit  (本地包)
      │    │    └── modbus_multi_device  (本地包)
      │    └── services/explosion/*
      │
      └── views/pages/history_query_page.py
           ├── controllers/ignition_controller.py
           └── controllers/explosion_controller.py
```

### 9.2 配置文件依赖

```
configs/experiment_config.yaml
 ├── explosion_experiment section → ExplosionController, ExplosionDatabase
 ├── ignition_experiment section → IgnitionController, IgnitionDatabase
 └── ui section → MainWindow

configs/flame_analyzer_config.yaml
 └── FlameAnalyzerConfig → explosion_page, flame_analyzer_widget

configs/system.yaml
 └── MainWindow → 全局设置
```

---

## 10. 质量标准与验收准则

### 10.1 代码质量指标

| 指标 | 要求 |
|------|------|
| 测试覆盖率 | 核心 Model + Service 层 ≥ 80% |
| 函数长度 | 单函数 ≤ 80 行（超出须拆分） |
| 文件长度 | 单文件建议 ≤ 800 行（超出需说明） |
| 硬编码数值 | 0 个（全部通过 config.get() 读取） |
| 直接 DB 访问 | View 层 0 个 `controller.db.*` 调用 |
| SQL 拼接 | 0 个（全部参数化） |

### 10.2 功能验收标准

**着火点实验**
- [ ] 能成功新建实验会话并写入数据库
- [ ] 6 路温度曲线实时刷新（≤ 600ms 延迟）
- [ ] 切线法在置信度 ≥ 0.85 时自动标注着火点
- [ ] 低置信度时回退到实时检测结果
- [ ] 实验完成后生成 Word 报告（含温度曲线截图）

**爆炸性实验**
- [ ] 8 步时序完整执行，继电器状态正确
- [ ] 每轮次火焰图像保存到指定路径
- [ ] 5 轮后根据配置阈值自动询问是否继续
- [ ] 会话恢复后轮次计数从 DB 同步（不重置为 0）
- [ ] finalize 后爆炸性等级正确写入数据库

**历史数据管理**
- [ ] 支持按实验名称/日期/操作员筛选
- [ ] 表格不可直接编辑（只读模式）
- [ ] 能为历史会话补充生成切线分析和报告

### 10.3 发布标准

- [ ] `pyinstaller` 打包成功，可在干净机器运行
- [ ] Windows / macOS 均测试通过
- [ ] 启动时间 < 5 秒
- [ ] 运行 10 轮实验无内存泄漏（任务管理器验证）
- [ ] requirements.txt 无冗余子依赖

---

## 11. 同类项目复用指南

### 11.1 可直接复用的模块

| 模块 | 复用方式 | 需修改项 |
|------|----------|----------|
| `modbus_multi_device_package/` | 直接复制 | 设备配置 YAML |
| `utils/path_manager.py` | 直接复制 | 无 |
| `utils/logger.py` | 直接复制 | 日志文件名 |
| `models/experiment_states.py` | 参考状态机模式 | 状态名和转换规则 |
| `views/main_window.py` | 参考结构 | 页面列表和布局 |
| Agent 提示词模板库（第 8 节） | 直接使用 | 填入具体项目参数 |

### 11.2 新项目启动清单

```bash
# 1. 复制目录结构模板
cp -r CPIE2/src/utils/path_manager.py  新项目/src/utils/
cp -r CPIE2/src/models/experiment_states.py  新项目/src/models/  # 改状态名
cp -r CPIE2/modbus_multi_device_package/  新项目/  # 如需 Modbus

# 2. 用 agent-pm 生成 PRD
# 输入：硬件清单 + 检测目标描述
# 输出：功能清单 + 用户故事

# 3. 用 agent-arch 生成架构文档
# 输入：PRD
# 输出：目录结构 + DB schema + 状态机

# 4. 并行启动 agent-hw + agent-model
# agent-hw：硬件封装包
# agent-model：数据库模型

# 5. agent-service 实现控制器
# agent-algo 实现算法（如有）

# 6. agent-ui 实现页面
# agent-test 编写测试

# 7. agent-review 审查 → agent-build 打包
```

### 11.3 同类项目类型参考

本架构适合以下类型的工业/科学仪器软件：

| 项目类型 | 主要差异 | 复用度 |
|----------|----------|--------|
| 其他检测仪器（水质、土壤、空气） | 换传感器模块 + 检测算法 | 85% |
| 生产线质检系统 | 换相机视觉算法，增加 PLC 通信 | 70% |
| 环境监测站 | 去掉实验控制，强化数据展示 | 65% |
| 材料力学测试机 | 换力/位移传感器，加载曲线分析 | 75% |
| 热分析仪（DSC/TGA） | 只需着火点侧，换热流传感器 | 80% |

---

*文档生成于 2026-03-03，基于 CPIE 2.0 v1.1.251121 代码库反向工程。*
*适用于：`claude/review-cpie2-codebase-U2UAQ` 分支。*
