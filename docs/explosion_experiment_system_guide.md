# 爆炸性实验系统完整流程说明

## 1. 系统架构

### 核心组件
- **ExplosionExperimentPage** - 实验页面（UI + 逻辑）
- **ExplosionExperimentDialog** - 实验参数设置对话框
- **ExplostionDatabase** - 爆炸性实验数据库管理
- **FlameKit** - 火焰分析工具
- **ModbusDeviceManager** - 设备通讯管理

## 2. 按钮状态流转

```
应用启动
├─ [连接设备: enabled]
├─ [新建实验: disabled]
├─ [启动实验: disabled]
└─ [停止实验: disabled]

连接成功
├─ [连接设备: disabled]
├─ [新建实验: enabled] ← 可以创建实验
├─ [启动实验: disabled]
└─ [停止实验: disabled]

实验已创建
├─ [连接设备: disabled]
├─ [新建实验: enabled] ← 可以创建新实验
├─ [启动实验: enabled] ← 可以启动测试
└─ [停止实验: disabled]

实验运行中
├─ [连接设备: disabled]
├─ [新建实验: disabled]
├─ [启动实验: disabled]
└─ [停止实验: enabled] ← 可以停止

实验完成/停止
├─ [连接设备: disabled]
├─ [新建实验: enabled] ← 可以创建新实验
├─ [启动实验: enabled] ← 如果有活动会话
└─ [停止实验: disabled]

实验全部完成
├─ [连接设备: disabled]
├─ [新建实验: enabled] ← 可以创建新实验
├─ [启动实验: disabled] ← 会话已结束
└─ [停止实验: disabled]
```

## 3. 完整操作流程

### 3.1 启动和连接

```python
# 步骤1：启动应用
# 状态: 未连接

# 步骤2：点击"连接设备"
def _on_connect():
    1. 初始化数据库
    2. 创建设备管理器
    3. 连接设备
    4. 启动数据更新
    5. 启用"新建实验"按钮
```

### 3.2 创建实验

```python
# 步骤3：点击"新建实验"
def _on_new_experiment():
    1. 生成实验编号: EXP-YYYYMMDD-HHMMSS
    2. 弹出对话框收集参数:
       - 实验编号（只读）
       - 实验名称（必填）
       - 样品名称（必填）
       - 委托单位（可选，默认值）
       - 操作员（可选，默认值）
       - 备注（可选）
    
    3. 用户确认后:
       - 创建数据库会话
       - 保存实验配置
       - 启用"启动实验"按钮
       - 更新状态显示
```

### 3.3 执行测试轮次

```python
# 步骤4：点击"启动实验"
def _on_start_experiment():
    1. 检查是否有活动会话
    2. 显示确认对话框
    3. 用户确认后启动时序
    
def _start_sequence():
    1. 增加轮次计数器
    2. 重置数据缓存
    3. 启用"停止实验"按钮
    4. 在新线程执行时序控制
    
def _execute_sequence():
    1. 触发相机拍摄（如果启用）
    2. 执行时序步骤:
       - 控制继电器
       - 读取温度/压力
       - 延时等待
    3. 完成后:
       - 保存轮次数据
       - 询问是否继续
```

### 3.4 保存轮次数据

```python
def _save_test_round():
    1. 获取火焰分析结果:
       - max_flame_length (火焰长度)
       - max_flame_image_path (图片路径)
    
    2. 保存到数据库:
       db.add_test_round(
           session_id=当前会话ID,
           round_number=当前轮次,
           flame_length=火焰长度,
           max_flame_image_path=图片路径
       )
```

### 3.5 判断是否继续

```python
def _prompt_next_round():
    # 场景1: 完成5轮测试
    if total_rounds == 5:
        avg_length = 计算平均值
        if avg_length < 20:
            提示: "需要继续后5轮测试"
        else:
            询问: "是否完成实验?"
    
    # 场景2: 完成10轮测试
    elif total_rounds >= 10:
        询问: "是否完成实验?"
    
    # 场景3: 其他情况
    else:
        询问: "是否继续下一轮?"
```

### 3.6 完成实验

```python
def _ask_finalize_experiment():
    1. 计算平均火焰长度
    2. 分类爆炸性强弱
    3. 显示确认对话框
    4. 用户确认后:
       - 保存实验结果
       - 更新会话状态
       - 清除当前会话
       - 禁用"启动实验"按钮
```

## 4. 数据库表结构

### experiment_sessions
```sql
CREATE TABLE experiment_sessions (
    id INTEGER PRIMARY KEY,
    start_time DATETIME,
    end_time DATETIME,
    experiment_name TEXT,     -- 实验名称
    sample_name TEXT,         -- 样品名称
    description TEXT,         -- 包含编号、单位、操作员等
    status TEXT               -- running/completed
);
```

### test_rounds
```sql
CREATE TABLE test_rounds (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    round_number INTEGER,     -- 轮次编号 (1-10)
    flame_length REAL,        -- 火焰长度(mm)
    max_flame_image_path TEXT,-- 图片路径
    timestamp DATETIME,
    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id)
);
```

### experiment_results
```sql
CREATE TABLE experiment_results (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    total_rounds INTEGER,     -- 总轮次数
    avg_flame_length REAL,    -- 平均火焰长度
    explosion_level TEXT,     -- 爆炸性等级
    timestamp DATETIME,
    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id)
);
```

## 5. 爆炸性等级分类

```python
def classify_explosion_strength(avg_flame_length):
    if avg_flame_length < 20:
        return "无爆炸性"
    elif avg_flame_length < 400:
        return "弱爆炸性"
    elif avg_flame_length < 800:
        return "强爆炸性"
    else:
        return "超强爆炸性"
```

## 6. 实际使用示例

### 示例1: 标准5轮测试（平均值≥20mm）

```
1. 连接设备 ✓
2. 新建实验
   - 实验名称: "煤粉爆炸性测试"
   - 样品名称: "煤样A"
   ✓ 会话ID: 1

3. 第1轮测试
   - 启动实验 → 执行时序 → 拍摄分析
   - 火焰长度: 25.5mm ✓
   - 保存数据 ✓

4. 第2轮测试
   - 火焰长度: 28.3mm ✓

5. 第3轮测试
   - 火焰长度: 26.7mm ✓

6. 第4轮测试
   - 火焰长度: 27.1mm ✓

7. 第5轮测试
   - 火焰长度: 29.0mm ✓
   - 平均值: 27.32mm
   - 提示: "是否完成实验?"

8. 确认完成
   ✓ 爆炸性等级: 弱爆炸性
   ✓ 实验结果已保存
```

### 示例2: 10轮测试（前5轮平均值<20mm）

```
1. 连接设备 ✓
2. 新建实验
   - 实验名称: "煤粉爆炸性测试"
   - 样品名称: "煤样B"
   ✓ 会话ID: 2

3. 第1-5轮测试
   - 轮次1: 15.5mm
   - 轮次2: 18.2mm
   - 轮次3: 16.8mm
   - 轮次4: 17.5mm
   - 轮次5: 19.0mm
   - 平均值: 17.4mm < 20mm
   - 提示: "需要继续后5轮测试"

4. 第6-10轮测试
   - 轮次6: 22.5mm
   - 轮次7: 25.0mm
   - 轮次8: 23.8mm
   - 轮次9: 24.2mm
   - 轮次10: 26.5mm
   - 总平均值: 20.9mm
   - 提示: "是否完成实验?"

5. 确认完成
   ✓ 爆炸性等级: 弱爆炸性
   ✓ 实验结果已保存
```

## 7. 错误处理

### 用户操作错误
- **未连接设备就新建实验**: 按钮禁用，无法操作
- **未新建实验就启动**: 显示警告"请先新建实验"
- **实验运行中重复启动**: 显示警告"实验正在进行中"

### 数据保存错误
- **数据库连接失败**: 显示错误对话框
- **保存轮次失败**: 记录日志，提示用户
- **保存结果失败**: 显示错误，不清除会话

### 设备通讯错误
- **设备断开**: 停止实验，更新状态
- **相机故障**: 记录日志，继续实验（火焰长度为0）

## 8. 注意事项

1. **实验会话管理**
   - 一次只能有一个活动会话
   - 停止实验不会清除会话
   - 只有完成实验才清除会话

2. **轮次编号管理**
   - 轮次从1开始
   - 每次启动测试后自动递增
   - 数据库中保存实际轮次号

3. **数据完整性**
   - 每轮测试必须保存数据
   - 火焰分析结果实时更新
   - 图片路径相对于配置文件夹

4. **用户体验**
   - 关键操作需要确认
   - 实时显示状态和进度
   - 详细的日志记录

## 9. 未来扩展

- [ ] 支持实验暂停和恢复
- [ ] 历史实验数据查看和导出
- [ ] 实验报告自动生成
- [ ] 多样品批量测试
- [ ] 实验模板管理
- [ ] 数据统计和分析图表

