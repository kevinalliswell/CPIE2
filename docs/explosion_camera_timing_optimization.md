# 爆炸性实验拍摄时机优化

## 修改日期
2024-12-05

## 问题描述
原先的拍摄时机在实验启动时（时序控制开始前），导致拍摄太早，错过了火焰产生的瞬间。

## 解决方案
将拍摄时机调整为**打开喷吹阀的同时触发**，确保能够拍摄到火焰。

---

## 修改内容

### 1. 控制器新增信号 ✓

**文件**: `src/controllers/explosion_controller.py`

**新增信号定义**:
```python
spray_valve_opened = Signal()  # 喷吹阀打开（触发拍摄）
```

**修改时序执行逻辑**:
```python
if action == 'relay_on':
    relay = step['relay']
    # 如果是打开喷吹阀，发送信号触发拍摄
    if relay == 'spray_valve':
        self.spray_valve_opened.emit()
    self.control_relay(relay, True)
```

### 2. 页面连接信号并处理 ✓

**文件**: `src/views/pages/explosion_page.py`

**连接信号**:
```python
# 在 __init__ 中
self.controller.spray_valve_opened.connect(self._on_spray_valve_opened)
```

**新增处理方法**:
```python
def _on_spray_valve_opened(self):
    """处理喷吹阀打开事件 - 触发高速拍照"""
    if self.camera_enabled:
        self.log_message.emit("喷吹阀打开，开始高速拍照...")
        self._trigger_camera_capture()
    else:
        self.log_message.emit("⚠ 相机未初始化，跳过拍照")
```

**移除原拍摄调用**:
从 `_on_controller_experiment_started()` 中移除了拍摄代码。

---

## 优化后的时序流程

### 完整时序步骤

```
实验启动
   ↓
步骤1: 打开喷吹阀 ← ✨ 同时触发拍摄
   ├─ 发送 spray_valve_opened 信号
   ├─ 触发高速拍照（1秒内连续拍摄）
   └─ 控制喷吹阀打开
   ↓
步骤2: 喷吹延时（0.5秒）
   ↓
步骤3: 关闭喷吹阀
   ↓
步骤4: 等待延时（3.0秒）
   ↓
步骤5: 打开吹扫阀和吸尘器
   ↓
步骤6: 吹扫延时（5.0秒）
   ↓
步骤7: 关闭吹扫阀和吸尘器
   ↓
步骤8: 检查继电器状态
   ↓
时序完成 → 打开火焰分析器
```

### 拍摄时机详解

| 时间点 | 动作 | 说明 |
|--------|------|------|
| T0 | 发送喷吹阀信号 | 触发拍摄信号 |
| T0 | 开始高速拍摄 | 1秒内连续拍摄多帧 |
| T0 | 打开喷吹阀 | 喷吹煤粉到炉膛 |
| T0~T1 | 火焰产生 | 煤粉遇高温产生火焰 |
| T1 | 拍摄完成 | 图像保存到 temp_captures |
| T0.5 | 喷吹延时结束 | - |
| T0.5 | 关闭喷吹阀 | - |

**关键**：拍摄与喷吹阀同步启动，确保捕捉到火焰产生的完整过程。

---

## 信号流转机制

### 事件链

```
1. 用户点击"启动实验"
   ↓
2. ExplosionController.start_experiment()
   ↓
3. ExplosionController._execute_sequence() (后台线程)
   ↓
4. 执行到步骤1（打开喷吹阀）
   ↓
5. 检测到 relay == 'spray_valve'
   ↓
6. 发送信号: spray_valve_opened.emit()
   ↓
7. ExplosionExperimentPage._on_spray_valve_opened() 接收
   ↓
8. 检查相机状态
   ↓
9. 调用 _trigger_camera_capture()
   ↓
10. FlameKit.capture_one_second() 执行拍摄
   ↓
11. 图像保存到 data/temp_captures/
   ↓
12. 继续执行后续时序步骤
```

### 线程安全性

- **信号发送**：在后台线程（时序控制线程）中发送
- **信号接收**：Qt 自动调度到主线程（GUI线程）
- **拍摄执行**：在主线程中执行，确保线程安全

---

## 配置说明

### 时序配置（experiment_config.yaml）

```yaml
explosion_experiment:
  sequence_steps:
    - step: 1
      name: 打开喷吹阀
      action: relay_on
      relay: spray_valve  # ← 关键：检测此relay触发拍摄
      delay_after: 0.0
    
    - step: 2
      name: 喷吹延时
      action: delay
      duration: 0.5  # 可调整
    
    # ... 其他步骤
```

### 相机配置

```yaml
camera:
  enabled: true
  capture_duration: 1.0     # 拍摄持续时间（秒）
  trigger_delay: 0.5        # 触发延迟（保留，暂未使用）
```

---

## 验证要点

### 1. 日志检查

正确的日志输出顺序：
```
[步骤1] 打开喷吹阀
喷吹阀打开，开始高速拍照...
✓ 临时文件夹已清空
✓ 自动拍摄完成，共计拍摄：X 帧
✓ 图像保存完成，共计保存：X 帧到 data/temp_captures
  ✓ spray_valve -> 导通
[步骤2] 喷吹延时
  延时 0.5秒...
[步骤3] 关闭喷吹阀
  ✓ spray_valve -> 断开
...
```

### 2. 时间同步验证

- [ ] 日志中"喷吹阀打开"和"开始高速拍照"几乎同时出现
- [ ] 拍摄完成后才继续后续步骤
- [ ] `temp_captures` 文件夹中有图像文件

### 3. 火焰捕捉验证

- [ ] 打开 `temp_captures` 文件夹查看图像
- [ ] 图像中能看到火焰
- [ ] 至少有一张图像包含明显的火焰

---

## 常见问题

### 问题1：仍然拍不到火焰

**可能原因**：
1. 拍摄太快，火焰还未产生
2. 拍摄持续时间太短
3. 相机帧率设置不当

**解决方法**：
1. 调整 `sequence_steps[1].duration`（喷吹延时），延长喷吹时间
2. 调整 FlameKit 拍摄参数，增加拍摄帧数
3. 检查相机设置，确保曝光参数合适

### 问题2：图像太多或太少

**调整方法**：
- 修改 `FlameKit.capture_one_second()` 中的拍摄参数
- 或修改相机的帧率设置

### 问题3：拍摄没有触发

**检查清单**：
- [ ] 相机已初始化（`camera_enabled == True`）
- [ ] 信号正确连接（检查日志中是否有 "喷吹阀打开" 消息）
- [ ] 时序配置正确（`relay: spray_valve`）
- [ ] 没有异常报错

---

## 修改文件清单

1. `src/controllers/explosion_controller.py`
   - 新增 `spray_valve_opened` 信号
   - 修改 `_execute_sequence()` 方法，检测喷吹阀并发送信号

2. `src/views/pages/explosion_page.py`
   - 修改 `__init__()` 方法，连接喷吹阀信号
   - 修改 `set_controller()` 方法，连接喷吹阀信号
   - 修改 `_on_controller_experiment_started()` 方法，移除拍摄代码
   - 新增 `_on_spray_valve_opened()` 方法，处理拍摄触发

3. `docs/explosion_camera_timing_optimization.md`（本文件）
   - 新增拍摄时机优化说明文档

---

## 优势

1. **精准同步**：拍摄与喷吹阀同步，不会错过火焰
2. **灵活配置**：可通过配置文件调整时序参数
3. **线程安全**：使用Qt信号机制，确保线程安全
4. **易于调试**：日志清晰显示各步骤执行情况
5. **可扩展性**：其他继电器也可以使用相同机制触发动作

---

## 备注

- 此优化确保拍摄时机与火焰产生同步
- 如果火焰持续时间很短，可能需要调整拍摄参数
- 建议先进行几次测试，调整到最佳拍摄时机和参数
- 所有修改已完成并通过代码检查

