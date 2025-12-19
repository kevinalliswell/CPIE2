# 着火点实验"新建实验"功能实现文档

## 概述

参考爆炸性实验的逻辑，为着火点实验页面添加了"新建实验"按钮，实现了完整的实验会话管理和按钮状态控制。

## 实现内容

### 1. 数据库优化 (ignition_database.py)

#### 更新 experiment_sessions 表结构
```sql
CREATE TABLE IF NOT EXISTS experiment_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    experiment_name TEXT,
    sample_names TEXT,          -- 新增：6个样品名称（JSON字符串）
    client TEXT,                -- 新增：委托单位
    operator TEXT,              -- 新增：操作员
    description TEXT,
    status TEXT DEFAULT 'running'
)
```

#### 新增/优化方法

1. **start_experiment_session()** - 创建实验会话
   - 新增参数：sample_names, client, operator
   - 初始状态改为 'prepared'（准备就绪，未启动）

2. **update_session()** - 更新会话信息
   - 可更新字段：experiment_name, sample_names, client, operator, description, status
   - 用于将会话从 'prepared' 状态更新为 'running'

3. **get_experiment_sessions()** - 查询会话列表
   - 返回完整的会话信息，包括新增字段

### 2. 对话框优化 (ignition_experiment_dialog.py)

#### 功能增强

1. **导入 json 模块**
   - 用于将样品名称列表序列化为 JSON 字符串存储

2. **on_confirm() 方法优化**
   - 构建描述信息，包含实验编号、委托单位、操作员、备注
   - 返回数据包含数据库所需字段和UI显示字段

3. **数据格式**
```python
config_data = {
    # 数据库所需字段
    'experiment_name': 'IGN-20251130-001',
    'sample_names': '["神东烟煤", "贫煤", ...]',  # JSON字符串
    'client': '北京科技大学',
    'operator': '实验员',
    'description': '实验编号：IGN-20251130-001 | 委托单位：北京科技大学 | ...',
    
    # 额外字段（用于UI显示）
    'experiment_id': 'IGN-20251130-001',
    'sample_names_list': ["神东烟煤", "贫煤", ...],  # 原始列表
    'note': '备注信息'
}
```

### 3. 着火点页面修改 (ignition_page.py)

#### 新增功能

1. **导入模块**
   - `from datetime import datetime` - 生成实验编号
   - `from views.dialogs.ignition_experiment_dialog import IgnitionExperimentDialog`

2. **新增属性**
   - `self.current_experiment_config` - 保存当前实验配置

3. **控制面板布局调整**
   - 添加"新建实验"按钮（第1行第2列）
   - 按钮重新排列：
     - 第1行：[连接设备] [新建实验] [启动实验]
     - 第2行：[停止实验] [采集数据] [状态标签]

4. **新增方法**

##### _on_new_experiment()
- 生成实验编号：IGN-YYYYMMDD-XXX
- 查询当天已有实验数量，自动递增编号
- 打开实验参数设置对话框
- 连接确认信号

##### _on_experiment_config_confirmed()
- 接收对话框返回的配置数据
- 创建数据库会话（状态：prepared）
- 保存会话ID和配置到当前实验
- 更新按钮状态和界面显示

5. **修改方法**

##### _on_start()
- 检查是否已创建实验（current_session_id）
- 将会话状态从 'prepared' 更新为 'running'
- 不再自动创建会话，使用已存在的会话

##### stop_experiment()
- 实验停止后保持会话ID（不清空）
- 允许再次启动同一个实验

## 按钮状态控制逻辑

按照以下状态机进行按钮控制：

### 状态1: 应用启动
```
[连接设备: enabled]
[新建实验: disabled]
[启动实验: disabled]
[停止实验: disabled]
```

### 状态2: 连接成功
```
[连接设备: disabled]
[新建实验: enabled]   ← 可以新建实验
[启动实验: disabled]  ← 需要先新建实验
[停止实验: disabled]
```

### 状态3: 新建实验完成
```
[连接设备: disabled]
[新建实验: enabled]   ← 可以新建另一个实验
[启动实验: enabled]   ← 可以启动当前实验
[停止实验: disabled]
```
状态显示：`状态: 实验已准备 (IGN-20251130-001)`

### 状态4: 实验运行中
```
[连接设备: disabled]
[新建实验: disabled]
[启动实验: disabled]
[停止实验: enabled]   ← 只能停止
```
状态显示：`状态: 实验中 (IGN-20251130-001)`

### 状态5: 实验完成/停止
```
[连接设备: disabled]
[新建实验: enabled]   ← 可以新建新实验
[启动实验: enabled]   ← 可以重新启动当前实验
[停止实验: disabled]
```
状态显示：`状态: 已停止 (IGN-20251130-001)`

## 实验编号生成规则

### 格式
```
IGN-YYYYMMDD-XXX
```

- `IGN`: 固定前缀（Ignition）
- `YYYYMMDD`: 日期（如 20251130）
- `XXX`: 当天的实验序号（001-999）

### 示例
```
IGN-20251130-001  第一个实验
IGN-20251130-002  第二个实验
IGN-20251201-001  第二天的第一个实验
```

## 数据库会话状态

| 状态 | 说明 |
|------|------|
| prepared | 实验已创建，准备就绪，未启动 |
| running | 实验运行中 |
| completed | 实验正常完成 |
| cancelled | 实验被取消 |
| error | 实验出错 |

## 工作流程

```
1. 启动应用
   └─> 状态1

2. 点击"连接设备"
   └─> 连接中...
       ├─> 成功 -> 状态2
       └─> 失败 -> 回到状态1

3. 点击"新建实验"
   └─> 打开对话框
       ├─> 输入实验信息
       │   ├─> 样品名称（至少一个）
       │   ├─> 委托单位（默认：北京科技大学）
       │   ├─> 操作员（默认：实验员）
       │   └─> 备注（可选）
       └─> 点击"确认启动"
           ├─> 验证数据
           ├─> 创建数据库会话（status='prepared'）
           ├─> 保存会话ID和配置
           └─> 状态3

4. 点击"启动实验"
   ├─> 检查是否有会话
   ├─> 更新会话状态为'running'
   ├─> 启动设备管理器
   ├─> 启动数据采集
   └─> 状态4

5. 点击"停止实验"
   ├─> 停止数据采集
   ├─> 停止设备管理器
   ├─> 更新会话状态为'completed'
   └─> 状态5

6. 可选：重新启动
   └─> 从状态5点击"启动实验"
       └─> 重新进入状态4（同一个会话）

7. 可选：新建下一个实验
   └─> 从状态5点击"新建实验"
       └─> 重复步骤3
```

## 日志输出示例

```
[12:30:15] 正在连接设备...
[12:30:18] ✓ 设备连接成功
[12:30:25] ✓ 实验已创建: IGN-20251130-001
[12:30:25]   会话ID: 1
[12:30:30] 启动实验...
[12:30:30] ✓ 实验会话已启动 (ID: 1)
[12:30:30] ✓ 实验已启动
[12:35:20] 停止实验...
[12:35:20] ✓ 实验会话已结束 (ID: 1)
[12:35:20] ✓ 实验已停止
```

## 数据库查询示例

```python
# 查询所有准备就绪的实验
prepared_sessions = db.get_experiment_sessions(status='prepared')

# 查询所有运行中的实验
running_sessions = db.get_experiment_sessions(status='running')

# 查询所有已完成的实验
completed_sessions = db.get_experiment_sessions(status='completed')

# 查询特定会话的详细信息
session = db.get_session_by_id(session_id)
print(f"实验名称: {session['experiment_name']}")
print(f"样品名称: {json.loads(session['sample_names'])}")
print(f"委托单位: {session['client']}")
print(f"操作员: {session['operator']}")
```

## 与爆炸性实验的对比

| 特性 | 爆炸性实验 | 着火点实验 |
|------|-----------|----------|
| 实验编号前缀 | EXP | IGN |
| 样品数量 | 1个 | 6个 |
| 样品名称存储 | sample_name (TEXT) | sample_names (JSON) |
| 对话框输入 | 实验名称 + 样品名称 | 6个样品名称 |
| 轮次测试 | 5或10轮 | 无轮次（连续监测） |
| 特殊功能 | 火焰长度分析 | 着火点检测 |

## 测试检查清单

- [ ] 连接设备后，"新建实验"按钮可用
- [ ] 新建实验对话框正常显示
- [ ] 实验编号自动生成且递增正确
- [ ] 样品名称验证（至少一个）
- [ ] 委托单位和操作员有默认值
- [ ] 实验创建后，"启动实验"按钮可用
- [ ] 启动实验前检查会话存在
- [ ] 实验运行中，只有"停止实验"可用
- [ ] 停止实验后，可以重新启动或新建实验
- [ ] 数据库正确记录会话信息
- [ ] 状态标签正确显示实验编号
- [ ] 日志输出完整且准确

## 注意事项

1. **会话持久性**
   - 实验停止后会话ID不清空，允许重新启动同一实验
   - 如需开始新实验，需点击"新建实验"

2. **状态同步**
   - 数据库会话状态与UI状态保持同步
   - prepared -> running -> completed

3. **错误处理**
   - 启动前检查会话是否存在
   - 对话框数据验证
   - 数据库操作异常处理

4. **用户体验**
   - 状态标签显示当前实验编号
   - 按钮状态清晰反映当前可执行的操作
   - 日志记录详细的操作过程

## 后续优化建议

1. **实验历史**
   - 添加实验历史查看功能
   - 可选择历史实验重新分析

2. **实验模板**
   - 保存常用的实验配置模板
   - 快速创建相似实验

3. **数据关联**
   - 实时数据与会话ID关联
   - 支持按会话查询历史数据

4. **报告生成**
   - 自动生成实验报告
   - 包含实验信息和结果

