# FlameKit API 使用文档

本文档提供 FlameKit 的详细 API 说明和高级用法。

## 目录

- [快速开始](#快速开始)
- [核心API](#核心api)
- [配置管理](#配置管理)
- [高级用法](#高级用法)
- [示例代码](#示例代码)

## 快速开始

### 基本使用流程

```python
from flamekit import FlameKit

# 创建实例
kit = FlameKit()

try:
    # 初始化相机
    kit.initialize()
    
    # 采集图像
    images, count = kit.capture_one_second()
    
    # 分析火焰
    result, max_image = kit.analyze()
    
    # 保存结果
    kit.save_max_result()
finally:
    kit.release()
```

## 核心API

### FlameKit 类

#### `__init__()`

创建 FlameKit 实例。

```python
kit = FlameKit()
```

**说明**: 实例化时不会自动初始化相机，首次调用需要相机的操作时会自动初始化。

---

#### `initialize() -> bool`

初始化相机设备。

```python
success = kit.initialize()
```

**返回值**:
- `True`: 初始化成功
- `False`: 初始化失败

**说明**: 
- 如果相机已初始化，直接返回 `True`
- 失败时检查相机连接和驱动

---

#### `preview(seconds: float = 3.0, window_name: str = "Preview") -> None`

相机画面实时预览。

```python
kit.preview(seconds=5.0, window_name="My Preview")
```

**参数**:
- `seconds`: 预览时长（秒），默认 3.0
- `window_name`: 窗口名称，默认 "Preview"

**说明**:
- 按 `ESC` 键可提前退出
- 窗口可手动调整大小

---

#### `capture_one_second(temp_dir: Optional[str] = None) -> Tuple[List[str], int]`

高速采集1秒图像。

```python
images, count = kit.capture_one_second(temp_dir="./my_captures")
```

**参数**:
- `temp_dir`: 临时目录路径，默认使用配置中的 `paths.temp_dir`

**返回值**:
- `images`: 图像文件路径列表
- `count`: 采集的帧数

**说明**:
- 采集前会清空指定目录
- 图像以 JPG 格式保存
- 文件名包含时间戳和帧序号

---

#### `set_calibration(mm_per_pixel: float) -> None`

设置像素到毫米的标定参数。

```python
kit.set_calibration(0.3152)  # 0.3152 mm/pixel
```

**参数**:
- `mm_per_pixel`: 每像素对应的毫米数

**说明**:
- 参数会自动保存到配置文件
- 建议使用 `calibration_demo.py` 进行标定

---

#### `analyze(image_paths: Optional[List[str]] = None, save_annotated: bool = True) -> Tuple[Dict, str]`

批量分析火焰图像。

```python
result, max_image = kit.analyze(images, save_annotated=True)
```

**参数**:
- `image_paths`: 图像路径列表，默认使用最后一次采集的图像
- `save_annotated`: 是否保存标注图像，默认 `True`

**返回值**:
- `result`: 分析结果字典
- `max_image`: 最大火焰对应的图像路径

**结果字典结构**:
```python
{
    'success': bool,              # 是否分析成功
    'max_length_mm': float,       # 最大火焰长度(mm)
    'max_width_mm': float,        # 最大火焰宽度(mm)
    'area_mm2': float,            # 火焰面积(mm²)
    'contour_count': int,         # 检测到的轮廓数量
    'annotated_image': ndarray,    # 标注后的图像（numpy数组）
    'image_path': str             # 图像路径
}
```

---

#### `play_analyzed(image_paths: Optional[List[str]] = None, speed: float = 1.0, window_name: str = "Playback", target_fps: int = 240, duration_s: float = 1.0) -> None`

播放分析后的图像序列。

```python
kit.play_analyzed(images, speed=0.5, target_fps=240, duration_s=1.0)
```

**参数**:
- `image_paths`: 图像路径列表，默认使用最后一次采集的图像
- `speed`: 播放速度倍率（1.0=正常，0.5=慢速，2.0=快速）
- `window_name`: 窗口名称，默认 "Playback"
- `target_fps`: 目标帧率，默认 240
- `duration_s`: 播放时长（秒），默认 1.0

**说明**:
- 按 `ESC` 键可提前退出
- 可用于慢动作回放分析结果

---

#### `save_max_result(output_dir: Optional[str] = None) -> Optional[str]`

保存最大火焰长度的标注图。

```python
save_path = kit.save_max_result(output_dir="./results")
```

**参数**:
- `output_dir`: 输出目录，默认使用配置中的 `paths.output_dir`

**返回值**:
- 保存路径（成功）或 `None`（失败）

**说明**:
- 同时会在控制台打印原图路径
- 如果分析失败，返回 `None`

---

#### `release() -> None`

释放相机资源。

```python
kit.release()
```

**说明**:
- 必须在使用完毕后调用
- 建议在 `finally` 块中调用

---

## 配置管理

### 配置文件位置

FlameKit 使用三级配置优先级：

1. **当前目录**: `./config.json` (最高优先级)
2. **用户目录**: 
   - Windows: `%APPDATA%/flamekit/config.json`
   - Linux/Mac: `~/.flamekit/config.json`
3. **包内默认**: `flamekit/config_default.json` (只读)

### 访问配置

```python
# 获取配置值
exposure = kit.config.get('camera.exposure_us', 4000)

# 设置配置值
kit.config.set('camera.exposure_us', 5000, save=True)
```

### 配置项说明

#### 相机参数 (`camera`)

- `exposure_us`: 曝光时间（微秒），默认 4000
- `resolution_index`: 分辨率索引，默认 1
- `force_mono`: 强制单色模式，默认 `true`
- `capture_duration`: 采集时长（秒），默认 1.0

#### 标定参数 (`calibration`)

- `mm_per_pixel`: 每像素对应的毫米数，默认 0.3152
- `reference_length_mm`: 参考长度（毫米），默认 200.0

#### 分析参数 (`analysis`)

- `binary_threshold`: 二值化阈值，默认 0
- `min_flame_area`: 最小火焰面积（像素²），默认 1000
- `use_otsu`: 使用OTSU自动阈值，默认 `true`

#### 路径参数 (`paths`)

- `temp_dir`: 临时图像目录，默认 `./temp_captures`
- `output_dir`: 结果输出目录，默认 `./results`

## 高级用法

### 自定义采集参数

```python
# 修改曝光时间
kit.config.set('camera.exposure_us', 5000)

# 修改分辨率
kit.config.set('camera.resolution_index', 0)  # 使用更高分辨率

# 重新初始化以应用设置
kit.release()
kit.initialize()
```

### 批量处理

```python
# 多次采集和分析
results = []
for i in range(5):
    images, count = kit.capture_one_second()
    result, max_img = kit.analyze(images)
    if result['success']:
        results.append(result['max_length_mm'])

print(f"平均火焰长度: {sum(results)/len(results):.2f} mm")
```

### 自定义分析参数

```python
# 调整分析参数
kit.config.set('analysis.min_flame_area', 500)  # 降低最小面积阈值
kit.config.set('analysis.binary_threshold', 50)   # 调整二值化阈值
kit.config.set('analysis.use_otsu', False)        # 禁用OTSU

# 重新分析
result, max_img = kit.analyze()
```

### 图像后处理

```python
# 获取分析结果中的标注图像
result, max_img = kit.analyze()
annotated = result['annotated_image']

# 使用OpenCV进行进一步处理
import cv2
gray = cv2.cvtColor(annotated, cv2.COLOR_BGR2GRAY)
# ... 自定义处理
```

## 示例代码

### 示例1: 基本使用

```python
from flamekit import FlameKit

kit = FlameKit()
try:
    kit.initialize()
    images, count = kit.capture_one_second()
    result, max_img = kit.analyze()
    if result['success']:
        print(f"火焰长度: {result['max_length_mm']:.2f} mm")
    kit.save_max_result()
finally:
    kit.release()
```

### 示例2: 参数标定

```python
from flamekit import FlameKit

kit = FlameKit()
try:
    kit.initialize()
    # 使用已知长度的参考物进行标定
    # 假设100mm的参考物在图像中占317像素
    kit.set_calibration(100.0 / 317.0)
    print("标定完成")
finally:
    kit.release()
```

### 示例3: 连续监测

```python
from flamekit import FlameKit
import time

kit = FlameKit()
try:
    kit.initialize()
    for i in range(10):
        images, count = kit.capture_one_second()
        result, max_img = kit.analyze()
        if result['success']:
            print(f"第{i+1}次: {result['max_length_mm']:.2f} mm")
        time.sleep(1)
finally:
    kit.release()
```

## 错误处理

### 常见错误

1. **相机初始化失败**
   ```python
   if not kit.initialize():
       print("检查相机连接和驱动")
   ```

2. **采集失败**
   ```python
   images, count = kit.capture_one_second()
   if count == 0:
       print("未采集到图像，检查相机状态")
   ```

3. **分析失败**
   ```python
   result, max_img = kit.analyze()
   if not result['success']:
       print("未检测到火焰，调整分析参数")
   ```

## 性能优化

1. **降低分辨率**: 增大 `resolution_index` 可提高帧率
2. **调整曝光**: 合适的曝光时间可提高图像质量
3. **批量处理**: 一次性分析多张图像更高效

## 更多资源

- [简明使用手册.md](简明使用手册.md) - 快速上手指南
- [包说明.md](包说明.md) - 包的特性和介绍
- `examples/` - 更多示例代码

