# 着火点实验数据库结构与逻辑梳理

## 一、数据库概览

### 基本信息
- **文件名**: `ignition_experiment.db`
- **类型**: SQLite3
- **编码**: UTF-8
- **外键支持**: 已启用 (`PRAGMA foreign_keys = ON`)

### 数据库类
- **类名**: `IgnitionDatabase`
- **模块**: `src/models/ignition_database.py`
- **设计模式**: 单例连接 + CRUD操作

---

## 二、数据表结构

### 2.1 实时温度数据表 (ignition_realtime_data)

**用途**: 存储实验过程中采集的温度数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 记录ID |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | 采集时间 |
| pv | REAL | NOT NULL | 炉膛温度（Process Value） |
| ch1 | REAL | NOT NULL | 样品1温度 |
| ch2 | REAL | NOT NULL | 样品2温度 |
| ch3 | REAL | NOT NULL | 样品3温度 |
| ch4 | REAL | NOT NULL | 样品4温度 |
| ch5 | REAL | NOT NULL | 样品5温度 |
| ch6 | REAL | NOT NULL | 样品6温度 |

**索引**:
- `idx_timestamp` - 按时间戳索引，提高时间范围查询性能

**数据特点**:
- 高频数据采集（每秒多次）
- 数据量大，需要定期清理或导出
- 用于实时图表显示和历史数据分析

**示例数据**:
```sql
INSERT INTO ignition_realtime_data (pv, ch1, ch2, ch3, ch4, ch5, ch6)
VALUES (450.5, 125.3, 126.1, 124.8, 125.9, 126.5, 125.1);
```

---

### 2.2 实验会话表 (experiment_sessions)

**用途**: 存储实验的元数据和会话信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 会话ID |
| start_time | DATETIME | NOT NULL | 实验开始时间 |
| end_time | DATETIME | NULL | 实验结束时间 |
| experiment_name | TEXT | NULL | 实验名称/编号 (如 IGN-20251130-001) |
| sample_names | TEXT | NULL | 样品名称（JSON字符串） |
| client | TEXT | NULL | 委托单位 |
| operator | TEXT | NULL | 操作员 |
| description | TEXT | NULL | 实验描述 |
| status | TEXT | DEFAULT 'running' | 实验状态 |

**状态值说明**:
| 状态 | 说明 | 触发时机 |
|------|------|----------|
| prepared | 实验已创建，未启动 | 点击"新建实验"完成 |
| running | 实验运行中 | 点击"启动实验" |
| completed | 实验正常完成 | 点击"停止实验" |
| cancelled | 实验被取消 | 手动取消 |
| error | 实验出错 | 异常情况 |

**sample_names JSON 格式**:
```json
["神东烟煤", "贫煤", "褐煤", "", "", ""]
```
- 固定6个元素
- 空字符串表示该通道无样品

**示例数据**:
```sql
INSERT INTO experiment_sessions 
(start_time, experiment_name, sample_names, client, operator, description, status)
VALUES (
    '2025-11-30 14:30:00',
    'IGN-20251130-001',
    '["神东烟煤", "贫煤", "褐煤", "", "", ""]',
    '北京科技大学',
    '实验员',
    '实验编号：IGN-20251130-001 | 委托单位：北京科技大学 | 操作员：实验员',
    'prepared'
);
```

---

### 2.3 着火点检测表 (ignition_detection)

**用途**: 记录检测到的着火点信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 检测记录ID |
| session_id | INTEGER | FOREIGN KEY | 关联会话ID |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | 检测时间 |
| channel | INTEGER | NOT NULL | 通道号 (1-6) |
| ignition_temperature | REAL | NOT NULL | 着火温度 (°C) |

**外键关系**:
- `session_id` → `experiment_sessions(id)`
- 级联操作: 删除会话时，相关检测记录也会被删除

**示例数据**:
```sql
INSERT INTO ignition_detection (session_id, channel, ignition_temperature)
VALUES (1, 1, 180.5);
```

---

## 三、数据关系图

```
┌─────────────────────────┐
│ experiment_sessions     │
│ ─────────────────────── │
│ id (PK)                 │
│ start_time              │
│ end_time                │
│ experiment_name         │
│ sample_names (JSON)     │
│ client                  │
│ operator                │
│ description             │
│ status                  │
└────────────┬────────────┘
             │
             │ 1:N
             │
             ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│ ignition_detection      │       │ ignition_realtime_data  │
│ ─────────────────────── │       │ ─────────────────────── │
│ id (PK)                 │       │ id (PK)                 │
│ session_id (FK)         │       │ timestamp (IDX)         │
│ timestamp               │       │ pv                      │
│ channel                 │       │ ch1 ~ ch6               │
│ ignition_temperature    │       └─────────────────────────┘
└─────────────────────────┘
```

**说明**:
- 一个会话可以有多个着火点检测记录
- 实时数据表独立存储，不直接关联会话（高频数据）
- 通过时间戳可以间接关联会话和实时数据

---

## 四、CRUD 操作分类

### 4.1 创建 (Create)

| 方法 | 表 | 说明 |
|------|-----|------|
| `insert_ignition_data()` | ignition_realtime_data | 插入单条温度数据 |
| `insert_batch_data()` | ignition_realtime_data | 批量插入温度数据 |
| `start_experiment_session()` | experiment_sessions | 创建实验会话 |
| `record_ignition_detection()` | ignition_detection | 记录着火点检测 |

**调用时机**:
```python
# 新建实验时
session_id = db.start_experiment_session(
    experiment_name="IGN-20251130-001",
    sample_names='["神东烟煤", "贫煤", ...]',
    client="北京科技大学",
    operator="实验员"
)

# 实验运行中（定时采集）
db.insert_ignition_data(pv=450.5, ch1=125.3, ...)

# 检测到着火点时
db.record_ignition_detection(
    session_id=1,
    channel=1,
    ignition_temperature=180.5
)
```

---

### 4.2 读取 (Read)

| 方法 | 用途 | 典型场景 |
|------|------|----------|
| `get_data_by_id()` | 查询单条温度数据 | 数据详情查看 |
| `get_latest_data()` | 获取最新N条数据 | 实时显示 |
| `get_data_by_time_range()` | 时间范围查询 | 历史数据分析 |
| `get_all_data()` | 查询所有数据 | 数据导出 |
| `get_data_count()` | 获取数据总数 | 统计信息 |
| `get_statistics()` | 通道统计信息 | 数据分析 |
| `get_experiment_sessions()` | 查询会话列表 | 实验历史 |
| `get_ignition_detections()` | 查询着火点记录 | 结果查看 |

**查询示例**:
```python
# 查询今天的所有实验
sessions = db.get_experiment_sessions()
today_sessions = [
    s for s in sessions 
    if s['start_time'].startswith('2025-11-30')
]

# 查询某个会话的所有着火点
detections = db.get_ignition_detections(session_id=1)

# 获取最新100条温度数据用于图表
latest_data = db.get_latest_data(limit=100)
```

---

### 4.3 更新 (Update)

| 方法 | 用途 | 典型场景 |
|------|------|----------|
| `update_data_by_id()` | 更新温度数据 | 数据修正 |
| `update_session()` | 更新会话信息 | 修改实验信息/状态 |
| `end_experiment_session()` | 结束实验会话 | 停止实验 |

**状态更新流程**:
```python
# 1. 新建实验（status='prepared'）
session_id = db.start_experiment_session(...)

# 2. 启动实验（prepared → running）
db.update_session(session_id, status='running')

# 3. 停止实验（running → completed）
db.end_experiment_session(session_id, status='completed')
```

---

### 4.4 删除 (Delete)

| 方法 | 用途 | 风险级别 |
|------|------|----------|
| `delete_data_by_id()` | 删除单条数据 | 低 |
| `delete_data_by_time_range()` | 删除时间范围数据 | 中 |
| `delete_all_data()` | 清空所有数据 | 高 ⚠️ |

**删除建议**:
- 生产环境禁用 `delete_all_data()`
- 删除前务必备份数据
- 建议使用归档策略而非直接删除

---

## 五、数据库生命周期管理

### 5.1 初始化流程

```python
def __init__(self, db_path: str = "ignition_data.db"):
    self._connect()                  # 1. 连接数据库
    self._check_and_upgrade_schema() # 2. 检查并升级表结构
    self._create_tables()            # 3. 创建数据表
```

**升级机制**:
```python
# 检测旧表结构
required_columns = ['sample_names', 'client', 'operator']

# 如果缺少字段，删除旧数据库并重建
if missing_columns:
    os.remove(self.db_path)
    # 重新连接并创建新表
```

---

### 5.2 连接管理

**特性**:
- 单例连接，线程安全 (`check_same_thread=False`)
- 启用外键约束
- 支持上下文管理器

**使用方式**:
```python
# 方式1: 手动管理
db = IgnitionDatabase()
try:
    db.insert_ignition_data(...)
finally:
    db.close()

# 方式2: 上下文管理器（推荐）
with IgnitionDatabase() as db:
    db.insert_ignition_data(...)
```

---

### 5.3 数据维护

| 操作 | 方法 | 说明 |
|------|------|------|
| 备份 | `backup()` | 复制数据库文件 |
| 优化 | `vacuum()` | 压缩数据库，回收空间 |
| 导出 | `export_to_csv()` | 导出为CSV文件 |

**维护建议**:
```python
# 每周备份
db.backup(f"backup/ignition_data_{datetime.now().strftime('%Y%m%d')}.db")

# 每月优化
db.vacuum()

# 定期导出归档
db.export_to_csv("archive/data_2025_11.csv", 
                 start_time="2025-11-01 00:00:00",
                 end_time="2025-11-30 23:59:59")
```

---

## 六、实验工作流程中的数据库操作

### 6.1 新建实验

```python
# UI: 用户点击"新建实验"
# 1. 生成实验编号
experiment_id = "IGN-20251130-001"

# 2. 打开对话框，用户输入信息
config = {
    'experiment_name': 'IGN-20251130-001',
    'sample_names': '["神东烟煤", "贫煤", ...]',
    'client': '北京科技大学',
    'operator': '实验员',
    'description': '...'
}

# 3. 创建会话（status='prepared'）
session_id = db.start_experiment_session(**config)

# 数据库状态: 1条prepared会话记录
```

---

### 6.2 启动实验

```python
# UI: 用户点击"启动实验"
# 1. 更新会话状态为running
db.update_session(session_id, status='running')

# 2. 启动定时器，开始采集数据
timer.start(interval=1000)  # 每秒采集

# 数据库状态: 会话状态更新为running
```

---

### 6.3 实验运行中

```python
# 定时器回调（每秒执行）
def on_timer():
    # 1. 读取设备数据
    pv = get_controller_pv()
    ch1, ch2, ... = get_temperature_channels()
    
    # 2. 插入数据库
    db.insert_ignition_data(pv, ch1, ch2, ch3, ch4, ch5, ch6)
    
    # 3. 检测着火点
    if detect_ignition(channel=1, temp=ch1):
        db.record_ignition_detection(
            session_id=session_id,
            channel=1,
            ignition_temperature=ch1
        )

# 数据库状态:
# - ignition_realtime_data: 持续增加记录（每秒1条）
# - ignition_detection: 检测到着火点时增加记录
```

---

### 6.4 停止实验

```python
# UI: 用户点击"停止实验"
# 1. 停止定时器
timer.stop()

# 2. 结束会话
db.end_experiment_session(session_id, status='completed')

# 数据库状态:
# - 会话状态更新为completed
# - 记录end_time
```

---

## 七、数据查询场景

### 7.1 实时显示

```python
# 图表更新（每秒）
latest_data = db.get_latest_data(limit=200)

for data in latest_data:
    plot_curve_pv.setData(times, [d['pv'] for d in latest_data])
    plot_curve_ch1.setData(times, [d['ch1'] for d in latest_data])
    # ...
```

---

### 7.2 历史数据分析

```python
# 查询某个时间段的数据
data = db.get_data_by_time_range(
    start_time="2025-11-30 14:00:00",
    end_time="2025-11-30 16:00:00"
)

# 统计分析
stats = db.get_statistics('ch1')
print(f"最高温度: {stats['max']}°C")
print(f"平均温度: {stats['avg']:.2f}°C")
```

---

### 7.3 实验历史查看

```python
# 查询所有已完成的实验
completed_sessions = db.get_experiment_sessions(status='completed')

for session in completed_sessions:
    print(f"实验: {session['experiment_name']}")
    print(f"时间: {session['start_time']} ~ {session['end_time']}")
    
    # 查询该实验的着火点
    detections = db.get_ignition_detections(session['id'])
    for d in detections:
        print(f"  通道{d['channel']}: {d['ignition_temperature']}°C")
```

---

## 八、性能优化建议

### 8.1 批量插入

```python
# ❌ 不推荐：逐条插入
for pv, ch1, ch2, ch3, ch4, ch5, ch6 in data_list:
    db.insert_ignition_data(pv, ch1, ch2, ch3, ch4, ch5, ch6)

# ✅ 推荐：批量插入
db.insert_batch_data(data_list)  # 使用executemany()
```

---

### 8.2 索引优化

```python
# 已有索引
CREATE INDEX idx_timestamp ON ignition_realtime_data(timestamp);

# 建议新增索引（如果频繁按会话查询）
CREATE INDEX idx_session_id ON ignition_detection(session_id);
```

---

### 8.3 数据分区

```python
# 按月分表（大数据量场景）
# ignition_realtime_data_2025_11
# ignition_realtime_data_2025_12
```

---

## 九、数据安全与备份策略

### 9.1 自动备份

```python
# 每次启动实验前备份
def before_start_experiment():
    backup_path = f"backup/auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    db.backup(backup_path)
```

---

### 9.2 事务处理

```python
# 数据库类已内置事务管理
# 所有写操作都有commit和rollback

try:
    db.insert_ignition_data(...)
    db.conn.commit()  # ✅ 成功提交
except Exception as e:
    db.conn.rollback()  # ❌ 失败回滚
```

---

### 9.3 数据导出归档

```python
# 按会话导出
def export_session_data(session_id):
    session = db.get_session_by_id(session_id)
    filename = f"{session['experiment_name']}_data.csv"
    
    # 导出温度数据
    db.export_to_csv(
        filename,
        start_time=session['start_time'],
        end_time=session['end_time']
    )
```

---

## 十、常见问题与解决方案

### 10.1 表结构不匹配

**问题**: `no such column: sample_names`

**原因**: 使用了旧版本数据库

**解决**: 自动检测并重建
```python
# _check_and_upgrade_schema() 会自动处理
# 检测缺少字段 → 删除旧库 → 重建
```

---

### 10.2 数据库锁定

**问题**: `database is locked`

**原因**: 多线程并发访问

**解决**: 
```python
# 已设置 check_same_thread=False
# 使用线程安全的连接
```

---

### 10.3 外键约束失败

**问题**: 插入着火点记录时找不到会话

**解决**:
```python
# 确保会话存在
if session_id:
    db.record_ignition_detection(session_id, channel, temp)
else:
    print("错误: 未找到有效会话")
```

---

## 十一、数据库监控与日志

### 11.1 操作日志

所有数据库操作都有日志输出：
```
✓ 数据库连接成功: ignition_experiment.db
✓ 数据表创建成功
✓ 实验会话已创建，ID: 1, 实验名称: IGN-20251130-001
✓ 着火点检测记录已保存: 通道1, 温度180.5°C
✓ 实验会话已结束，ID: 1, 状态: completed
```

---

### 11.2 性能监控

```python
# 监控数据量
total_records = db.get_data_count()
print(f"总记录数: {total_records}")

# 监控数据库大小
import os
db_size = os.path.getsize(db.db_path) / 1024 / 1024  # MB
print(f"数据库大小: {db_size:.2f} MB")
```

---

## 十二、总结

### 数据库设计特点

✅ **优点**:
- 三表分离，职责明确
- 支持会话管理，数据可追溯
- 自动升级机制，向后兼容
- 完整的CRUD操作
- 支持事务和外键约束

⚠️ **注意事项**:
- 实时数据表会快速增长，需定期归档
- 批量操作优于单条操作
- 备份策略要完善

🔧 **优化方向**:
- 考虑数据分区（大数据量时）
- 增加数据压缩（历史数据）
- 实现软删除（保留历史）

### 使用建议

1. **开发阶段**: 使用测试数据库，频繁重建
2. **生产环境**: 定期备份，谨慎删除
3. **性能优化**: 批量操作，合理使用索引
4. **数据安全**: 事务管理，错误处理

---

**文档版本**: v1.0  
**更新日期**: 2025-11-30  
**维护者**: CPIE项目组

