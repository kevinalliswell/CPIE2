---
name: FlameKit 参数化优化
overview: 为 FlameKit 和 CameraCapture 添加初始化时的可选参数支持（分辨率、曝光时间、黑白模式等），并自动保存到配置文件
todos:
  - id: modify-camera-init
    content: 修改 CameraCapture.__init__ 方法，添加可选参数并存储为实例属性
    status: completed
  - id: modify-camera-initialize
    content: 修改 CameraCapture.initialize 方法，使用传入参数并保存到配置
    status: completed
    dependencies:
      - modify-camera-init
  - id: modify-flamekit-init
    content: 修改 FlameKit.__init__ 方法，添加参数并传递给 CameraCapture
    status: completed
    dependencies:
      - modify-camera-init
---

# FlameKit 参数化优化方案

## 概述

优化 FlameKit 包，使初始化时可以传入常用相机参数（分辨率索引、曝光时间、黑白模式等），传入的参数会覆盖配置文件并自动保存，成为新的默认值。

## 修改文件

### 1. [`camera.py`](e:/CursorWorkSpace/Projects/CPIE/CPIE2/src/flame_package/flamekit/camera.py)

**修改 `CameraCapture.__init__` 方法** (第20-26行)

添加可选参数：

- `resolution_index`: Optional[int] - 分辨率档位（0, 1, 2等）
- `exposure_us`: Optional[int] - 曝光时间（微秒）
- `force_mono`: Optional[bool] - 是否强制黑白模式
- `capture_duration`: Optional[float] - 采集时长（秒）

**修改 `initialize` 方法** (第28-75行)

修改参数读取逻辑：

- 优先使用 `__init__` 传入的参数
- 如果参数为 None，则从配置文件读取
- 如果传入了参数，调用 `config.set()` 保存到配置文件

当前代码示例：

```python
res_index = self.config.get('camera.resolution_index', 1)
```

修改为：

```python
res_index = self.resolution_index if self.resolution_index is not None else self.config.get('camera.resolution_index', 1)
if self.resolution_index is not None:
    self.config.set('camera.resolution_index', self.resolution_index, save=True)
```

### 2. [`core.py`](e:/CursorWorkSpace/Projects/CPIE/CPIE2/src/flame_package/flamekit/core.py)

**修改 `FlameKit.__init__` 方法** (第24-31行)

添加相同的可选参数，并传递给 `CameraCapture`：

```python
def __init__(self, 
             resolution_index: Optional[int] = None,
             exposure_us: Optional[int] = None,
             force_mono: Optional[bool] = None,
             capture_duration: Optional[float] = None):
    self.config = get_config()
    self.camera = CameraCapture(
        resolution_index=resolution_index,
        exposure_us=exposure_us,
        force_mono=force_mono,
        capture_duration=capture_duration
    )
    # ... 其余代码
```

## 使用示例

优化后的使用方式：

```python
# 方式1：使用默认配置
kit = FlameKit()

# 方式2：指定分辨率
kit = FlameKit(resolution_index=0)

# 方式3：指定多个参数
kit = FlameKit(resolution_index=2, exposure_us=5000, force_mono=True)

# 方式4：直接使用 CameraCapture
camera = CameraCapture(resolution_index=1, exposure_us=3000)
```

## 向后兼容性

所有参数都是可选的（默认为 None），不传参数时使用配置文件的默认值，保持完全向后兼容。

## 需要的依赖包

无需新增依赖包，使用现有的 typing 模块即可。