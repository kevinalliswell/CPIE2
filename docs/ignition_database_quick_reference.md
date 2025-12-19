# 着火点实验数据库快速参考

## 数据表速查

### 1. ignition_realtime_data (实时温度数据)
```
id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
```
- 用途：存储高频采集的温度数据
- 频率：每秒1次或更高
- 索引：timestamp

### 2. experiment_sessions (实验会话)
```
id, start_time, end_time, experiment_name, 
sample_names(JSON), client, operator, description, status
```
- 用途：实验元数据和管理
- 状态：prepared → running → completed
- 编号格式：IGN-YYYYMMDD-XXX

### 3. ignition_detection (着火点检测)
```
id, session_id(FK), timestamp, channel, ignition_temperature
```
- 用途：记录检测到的着火点
- 外键：关联experiment_sessions

---

## 常用操作速查

### 创建操作

```python
# 新建实验会话
session_id = db.start_experiment_session(
    experiment_name="IGN-20251130-001",
    sample_names='["神东烟煤", "贫煤", ...]',
    client="北京科技大学",
    operator="实验员",
    description="实验描述"
)

# 插入温度数据
db.insert_ignition_data(pv=450.5, ch1=125.3, ch2=126.1, 
                       ch3=124.8, ch4=125.9, ch5=126.5, ch6=125.1)

# 批量插入
data_list = [(pv, ch1, ch2, ch3, ch4, ch5, ch6), ...]
db.insert_batch_data(data_list)

# 记录着火点
db.record_ignition_detection(session_id=1, channel=1, 
                             ignition_temperature=180.5)
```

### 查询操作

```python
# 最新数据（图表显示）
latest = db.get_latest_data(limit=200)

# 时间范围查询
data = db.get_data_by_time_range("2025-11-30 14:00:00", 
                                 "2025-11-30 16:00:00")

# 查询所有会话
sessions = db.get_experiment_sessions()

# 查询特定状态会话
running = db.get_experiment_sessions(status='running')

# 查询着火点记录
detections = db.get_ignition_detections(session_id=1)

# 统计信息
stats = db.get_statistics('ch1')  # max, min, avg, count
```

### 更新操作

```python
# 更新会话状态（启动实验时）
db.update_session(session_id, status='running')

# 更新会话信息
db.update_session(session_id, 
                 experiment_name="新名称",
                 description="新描述")

# 结束实验
db.end_experiment_session(session_id, status='completed')
```

### 删除操作

```python
# 删除单条数据
db.delete_data_by_id(record_id)

# 删除时间范围数据
db.delete_data_by_time_range("2025-11-01 00:00:00", 
                             "2025-11-30 23:59:59")
```

### 数据维护

```python
# 备份
db.backup("backup/ignition_data_20251130.db")

# 优化
db.vacuum()

# 导出CSV
db.export_to_csv("export.csv")
db.export_to_csv("export.csv", 
                start_time="2025-11-30 00:00:00",
                end_time="2025-11-30 23:59:59")
```

---

## 状态转换流程

```
新建实验 → prepared
   ↓
启动实验 → running
   ↓
停止实验 → completed
```

---

## 实验编号生成

```python
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
prefix = f"IGN-{today}"

# 查询今天已有实验数
sessions = db.get_experiment_sessions()
today_count = sum(1 for s in sessions 
                 if s['experiment_name'] and 
                    s['experiment_name'].startswith(prefix))

# 生成编号
experiment_id = f"{prefix}-{today_count + 1:03d}"
# 结果: IGN-20251130-001
```

---

## 样品名称处理

```python
import json

# 存储到数据库
sample_names_list = ["神东烟煤", "贫煤", "褐煤", "", "", ""]
sample_names_json = json.dumps(sample_names_list, ensure_ascii=False)
db.start_experiment_session(sample_names=sample_names_json, ...)

# 从数据库读取
session = db.get_experiment_sessions()[0]
sample_names_list = json.loads(session['sample_names'])
print(sample_names_list[0])  # "神东烟煤"
```

---

## 错误处理

```python
# 所有写操作都返回ID或布尔值
session_id = db.start_experiment_session(...)
if session_id <= 0:
    print("创建会话失败")

success = db.update_session(session_id, status='running')
if not success:
    print("更新失败")
```

---

## 上下文管理器

```python
# 自动关闭连接
with IgnitionDatabase() as db:
    db.insert_ignition_data(...)
    # 退出时自动调用 db.close()
```

---

## 性能建议

✅ **推荐**:
- 批量插入而非逐条插入
- 使用时间范围查询而非全表扫描
- 定期导出归档旧数据
- 及时关闭数据库连接

❌ **避免**:
- 在循环中频繁创建连接
- 不使用索引的大范围查询
- 长时间持有数据库锁

---

## 典型使用场景

### 场景1：实验数据采集

```python
# 初始化
db = IgnitionDatabase("ignition_experiment.db")

# 创建会话
session_id = db.start_experiment_session(...)

# 更新状态为运行中
db.update_session(session_id, status='running')

# 定时采集（每秒执行）
def collect_data():
    pv, channels = read_from_device()
    db.insert_ignition_data(pv, *channels)
    
    # 检测着火点
    for i, temp in enumerate(channels):
        if is_ignition(temp):
            db.record_ignition_detection(
                session_id, channel=i+1, 
                ignition_temperature=temp
            )

# 停止实验
db.end_experiment_session(session_id, status='completed')
```

### 场景2：历史数据分析

```python
# 查询某个实验的所有数据
session = db.get_experiment_sessions()[0]
data = db.get_data_by_time_range(
    session['start_time'],
    session['end_time']
)

# 分析数据
temps_ch1 = [d['ch1'] for d in data]
max_temp = max(temps_ch1)
avg_temp = sum(temps_ch1) / len(temps_ch1)

# 查询着火点
detections = db.get_ignition_detections(session['id'])
for d in detections:
    print(f"通道{d['channel']}: {d['ignition_temperature']}°C")
```

### 场景3：数据导出报告

```python
# 导出实验数据
sessions = db.get_experiment_sessions(status='completed')

for session in sessions:
    # 导出温度数据
    filename = f"{session['experiment_name']}_data.csv"
    db.export_to_csv(filename, 
                    session['start_time'],
                    session['end_time'])
    
    # 生成着火点报告
    detections = db.get_ignition_detections(session['id'])
    # ... 生成报告逻辑
```

---

## 数据库维护计划

| 频率 | 操作 | 命令 |
|------|------|------|
| 每天 | 无 | - |
| 每周 | 备份 | `db.backup(...)` |
| 每月 | 优化 + 归档 | `db.vacuum()` + `export_to_csv()` |
| 每季度 | 清理旧数据 | `delete_data_by_time_range()` |

---

## 故障排查

### 问题1: 表结构不匹配
```
错误: no such column: sample_names
解决: 程序会自动检测并重建数据库
```

### 问题2: 数据库锁定
```
错误: database is locked
解决: 检查是否有其他进程占用，或使用 check_same_thread=False
```

### 问题3: 外键约束
```
错误: FOREIGN KEY constraint failed
解决: 确保 session_id 存在于 experiment_sessions 表中
```

---

## 字段映射表

```python
COLUMN_HEADERS = {
    'pv': '炉膛温度',
    'ch1': '样品1',
    'ch2': '样品2',
    'ch3': '样品3',
    'ch4': '样品4',
    'ch5': '样品5',
    'ch6': '样品6'
}
```

---

**快速参考版本**: v1.0  
**更新日期**: 2025-11-30

