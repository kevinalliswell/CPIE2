# 爆炸性实验完整流程修复总结

## 修复日期
2024-12-04

## 修复内容

### 1. 在时序控制开始前添加高速拍照功能 ✓

**文件**: `src/views/pages/explosion_page.py`

**位置**: `_on_controller_experiment_started()` 方法

**修改内容**:
```python
# 在时序控制开始前触发高速拍照
if self.camera_enabled:
    self._trigger_camera_capture()
else:
    self.log_message.emit("⚠ 相机未初始化，跳过拍照")
```

**说明**: 
- 在实验启动时（时序控制开始前）自动触发高速拍照
- 拍摄的图像保存到 `data/temp_captures` 文件夹
- 如果相机未初始化，会记录警告日志但不影响实验继续

---

### 2. 修复路径配置不一致问题 ✓

**文件**: `src/views/dialogs/flame_analyzer/flame_analyzer_config.yaml`

**修改内容**: 将所有路径从 `datas/` 改为 `data/`

```yaml
paths:
  history_csv: "data/exp_explosion/history_explosion.csv"
  exp_data_json: "data/exp_explosion/explosion_experiment_data.json"
  temp_folder: "data/temp_captures"
  flame_output_folder: "data/flame_results"
  max_flame_save_folder: "data/max_flame_images"
```

**说明**:
- 确保火焰分析器使用的路径与 PathManager 保持一致
- 所有数据统一存储在项目根目录下的 `data/` 文件夹

---

### 3. 实现关闭分析器后清空临时文件夹 ✓

**文件**: `src/views/pages/explosion_page.py`

**新增方法**: `_cleanup_temp_folders()`

```python
def _cleanup_temp_folders(self):
    """清理临时文件夹：temp_captures 和 flame_results"""
    try:
        # 清理 temp_captures 文件夹
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    self.log_message.emit(f"⚠ 删除文件失败: {file} - {e}")
            self.log_message.emit(f"✓ 已清空临时文件夹: {self.temp_dir}")
        
        # 清理 flame_results 文件夹
        if os.path.exists(self.result_dir):
            for item in os.listdir(self.result_dir):
                item_path = os.path.join(self.result_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    self.log_message.emit(f"⚠ 删除项目失败: {item} - {e}")
            self.log_message.emit(f"✓ 已清空分析结果文件夹: {self.result_dir}")
        
    except Exception as e:
        self.log_message.emit(f"✗ 清理临时文件夹失败: {e}")
```

**调用位置**: `_on_flame_analysis_complete()` 方法末尾

**说明**:
- 在火焰分析完成并接收结果后自动清理临时文件夹
- 清理 `data/temp_captures` 中的所有图像文件
- 清理 `data/flame_results` 中的分析结果文件和子文件夹
- 即使清理失败也不会影响实验数据的保存

---

### 4. 最大火焰图片路径传递 ✓

**文件**: `src/views/dialogs/flame_analyzer/flame_analyzer_widget.py`

**说明**: 该功能已在原代码中正确实现

```python
def _copy_max_flame_image(self, source_path: str):
    """复制最大火焰图片到指定文件夹"""
    # ... 复制逻辑 ...
    
    # 更新结果字典
    self.exp_results['max_flame_saved_path'] = str(target_path)
    self.exp_results['max_flame_saved_time'] = timestamp
    
    return target_path
```

**explosion_page 接收**:
```python
self.max_flame_image_path = results.get('max_flame_saved_path', '')
```

**说明**:
- 最大火焰图片会被复制到 `data/max_flame_images` 文件夹
- 文件名格式: `原文件名_YYYYMMDD_HHMMSS_max.扩展名`
- 路径会通过 `exp_results` 正确传递给 explosion_page
- 数据库中保存的是最终保存在 max_flame_images 中的文件路径

---

## 完整工作流程

### 流程图

```
[用户点击"启动实验"]
         ↓
[检查实验条件：温度、压力]
         ↓
[实验启动事件触发]
         ↓
[自动触发高速拍照] ← 新增
  图像 → data/temp_captures/
         ↓
[执行时序控制]
  - 喷吹阀控制
  - 吹扫阀控制
  - 吸尘器控制
  - 延时等待
         ↓
[时序完成事件触发]
         ↓
[自动打开火焰分析器窗口]
  读取 data/temp_captures/
         ↓
[用户点击"分析图片"]
  处理图像 → data/flame_results/analysis_TIMESTAMP/
         ↓
[分析完成，显示结果]
  - 最大火焰长度
  - 最小火焰长度
  - 平均火焰长度
         ↓
[保存最大火焰图片] ← 已有功能
  复制到 → data/max_flame_images/图片_TIMESTAMP_max.jpg
         ↓
[用户关闭分析器窗口]
         ↓
[接收分析结果]
  - 火焰长度数据
  - 最大火焰图片路径
         ↓
[保存轮次数据到数据库]
         ↓
[清理临时文件夹] ← 新增
  - 清空 data/temp_captures/
  - 清空 data/flame_results/
         ↓
[询问是否继续下一轮]
```

### 文件夹用途说明

| 文件夹 | 用途 | 清理时机 |
|--------|------|---------|
| `data/temp_captures/` | 存储每轮实验拍摄的原始图像 | 火焰分析完成后立即清空 |
| `data/flame_results/` | 存储分析后的标注图像 | 火焰分析完成后立即清空 |
| `data/max_flame_images/` | 永久保存每轮的最大火焰图片 | 不清理，长期保存 |

### 数据库保存的内容

每轮实验在数据库中保存：
- `round_number`: 轮次编号 (1-10)
- `flame_length`: 火焰长度 (mm)
- `max_flame_image_path`: 最大火焰图片路径（指向 max_flame_images 文件夹）
- `test_time`: 测试时间

---

## 验证要点

### 1. 拍照功能测试
- [ ] 启动实验前确保相机已初始化
- [ ] 启动实验时日志显示拍照成功
- [ ] `data/temp_captures/` 中有图像文件

### 2. 路径一致性测试
- [ ] 火焰分析器能正确读取 `data/temp_captures/` 中的图像
- [ ] 分析结果保存到 `data/flame_results/analysis_TIMESTAMP/`
- [ ] 最大火焰图片保存到 `data/max_flame_images/`

### 3. 数据传递测试
- [ ] 关闭分析器后，explosion_page 收到正确的结果
- [ ] `max_flame_saved_path` 指向 `data/max_flame_images/` 中的文件
- [ ] 数据库中保存了正确的图片路径

### 4. 清理功能测试
- [ ] 火焰分析完成后，`data/temp_captures/` 被清空
- [ ] 火焰分析完成后，`data/flame_results/` 被清空
- [ ] `data/max_flame_images/` 中的图片未被删除

---

## 常见问题排查

### 问题：临时文件夹中没有图像文件

**可能原因**:
1. 相机未初始化 → 检查日志中是否有"相机未初始化"警告
2. 拍照失败 → 检查相机连接和flamekit配置
3. 路径配置错误 → 确认 PathManager 路径配置正确

**解决方法**:
- 启动实验前先点击"初始化相机"按钮
- 使用"手动拍摄"功能测试相机是否正常
- 检查日志中的拍照相关信息

### 问题：分析器窗口打不开

**可能原因**:
1. `data/temp_captures/` 文件夹不存在
2. 文件夹中没有图像文件
3. 图像格式不支持

**解决方法**:
- 确保文件夹存在且有权限访问
- 支持的格式：.jpg, .jpeg, .png, .bmp
- 检查相机拍摄功能是否正常

### 问题：最大火焰图片未保存

**可能原因**:
1. `data/max_flame_images/` 文件夹不存在或无权限
2. 磁盘空间不足
3. 文件名冲突

**解决方法**:
- 确保文件夹存在且有写权限
- 检查磁盘空间
- 文件名包含时间戳，不应有冲突

---

## 修改文件清单

1. `src/views/pages/explosion_page.py`
   - 修改 `_on_controller_experiment_started()` 方法
   - 修改 `_on_flame_analysis_complete()` 方法
   - 新增 `_cleanup_temp_folders()` 方法

2. `src/views/dialogs/flame_analyzer/flame_analyzer_config.yaml`
   - 修改所有路径配置（datas → data）

3. `docs/explosion_experiment_fixed_workflow.md` (本文件)
   - 新增完整流程文档

---

## 备注

- 所有修改已完成并经过代码检查
- 路径管理统一使用 PathManager 类
- 临时文件自动清理，永久文件妥善保存
- 数据库记录完整的实验数据和图片路径

