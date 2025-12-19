# 爆炸性实验对话框优化说明

## 优化内容

### 1. 新增字段

**实验名称 (experiment_name)** - 必填
- 位置：实验编号之后
- 用途：用于数据库存储，标识实验类型
- 示例：`煤粉爆炸性测试`、`粉尘爆炸实验`
- 占位符：`如：煤粉爆炸性测试`

### 2. 字段映射关系

#### 数据库所需字段 → 对话框字段

| 数据库字段 | 对话框字段 | 说明 |
|-----------|-----------|------|
| `experiment_name` | 实验名称 (新增) | 必填，实验类型标识 |
| `sample_name` | 样品名称 | 必填，样品标识 |
| `description` | 自动构建 | 包含：实验编号、委托单位、操作员、备注 |

#### description 字段自动构建规则

```python
description = "实验编号：EXP-20231129-001 | 委托单位：北京科技大学 | 操作员：张三 | 备注：首次测试"
```

### 3. 配置数据结构

```python
config = {
    # === 数据库所需字段 ===
    "experiment_name": "煤粉爆炸性测试",  # 实验名称
    "sample_name": "煤样A",              # 样品名称
    "description": "实验编号：EXP-20231129-001 | 委托单位：北京科技大学 | 操作员：张三",
    
    # === 额外字段（用于UI和报告） ===
    "experiment_id": "EXP-20231129-001",  # 实验编号
    "client": "北京科技大学",             # 委托单位
    "operator": "张三",                   # 操作员
    "note": "首次测试"                    # 备注
}
```

### 4. 字段顺序（从上到下）

1. **实验编号** (只读，自动生成)
2. **实验名称** (必填，新增)
3. **样品名称** (必填)
4. **委托单位** (可选，默认值)
5. **操作员** (可选，默认值)
6. **备注** (可选，多行文本)

### 5. 验证规则

必填项验证：
1. 实验名称不能为空
2. 样品名称不能为空

可选项默认值：
- 委托单位：`北京科技大学`
- 操作员：`实验员`

### 6. 数据库调用示例

```python
# 从对话框获取配置
config = dialog.get_config()

# 创建实验会话
session_id = db.start_experiment_session(
    experiment_name=config['experiment_name'],  # 实验名称
    sample_name=config['sample_name'],          # 样品名称
    description=config['description']           # 描述（自动构建）
)

# 额外字段可用于UI显示或报告生成
print(f"实验编号：{config['experiment_id']}")
print(f"委托单位：{config['client']}")
print(f"操作员：{config['operator']}")
```

## 优化前后对比

### 优化前

| 字段 | 类型 | 说明 |
|------|-----|------|
| experiment_id | 只读 | 实验编号 |
| sample_name | 必填 | 样品名称 |
| client | 可选 | 委托单位 |
| operator | 可选 | 操作员 |
| note | 可选 | 备注 |

**问题：**
- 缺少 `experiment_name`（数据库必需）
- 无法直接构建 `description` 字段

### 优化后

| 字段 | 类型 | 说明 |
|------|-----|------|
| experiment_id | 只读 | 实验编号 |
| **experiment_name** | **必填** | **实验名称（新增）** |
| sample_name | 必填 | 样品名称 |
| client | 可选 | 委托单位 |
| operator | 可选 | 操作员 |
| note | 可选 | 备注 |

**改进：**
- ✅ 新增 `experiment_name` 字段
- ✅ 自动构建 `description` 字段
- ✅ 配置数据同时包含数据库字段和扩展字段
- ✅ 完整支持数据库存储和报告生成

## 使用示例

```python
from views.dialogs.explosion_experiment_dialog import ExplosionExperimentDialog
from models.explosion_database import ExplostionDatabase

# 创建对话框
dialog = ExplosionExperimentDialog(experiment_id="EXP-20231129-001")

# 监听确认信号
def on_confirmed(config):
    # 数据库操作
    db = ExplostionDatabase()
    session_id = db.start_experiment_session(
        experiment_name=config['experiment_name'],
        sample_name=config['sample_name'],
        description=config['description']
    )
    
    print(f"✓ 实验会话已创建，ID: {session_id}")
    print(f"  实验编号: {config['experiment_id']}")
    print(f"  实验名称: {config['experiment_name']}")
    print(f"  样品名称: {config['sample_name']}")
    print(f"  委托单位: {config['client']}")
    print(f"  操作员: {config['operator']}")

dialog.confirmed.connect(on_confirmed)
dialog.exec()
```

## 总结

✅ **完全满足数据库要求**
- `experiment_name`: 必填字段，直接映射
- `sample_name`: 必填字段，直接映射
- `description`: 自动构建，包含所有补充信息

✅ **保留扩展功能**
- 实验编号、委托单位、操作员等信息仍然保留
- 可用于报告生成和UI显示

✅ **用户体验优化**
- 明确的必填项提示
- 合理的默认值
- 清晰的字段说明

