# FlameKit

工业相机火焰长度测试工具包（最小可用版本）

## 功能特性

- ✅ 相机画面预览
- ✅ 高速采集（1秒，存入临时文件夹）
- ✅ 参数标定（设置 mm_per_pixel）
- ✅ 火焰长度分析（批量，自动标注）
- ✅ 分析后图像预览播放（1秒，约240帧，可调速度）
- ✅ 保存最大火焰长度的标注图及原图路径

## 安装

### 方式1：pip 安装（推荐）

```bash
# 开发模式安装（可编辑模式，修改代码立即生效）
pip install -e .

# 或标准安装
pip install .
```

**注意：** 
- `flamekit/mvsdk.py` 已内置包装，但仍需安装厂商运行库（DLL/so）并可被系统加载（放在系统路径或当前目录）
- 首次使用前，请确保已安装相机SDK（详见 [安装指南](../文档/INSTALL.md)）

## 依赖

核心依赖：
- `numpy>=1.24.0`
- `opencv-python>=4.8.0`

可选依赖（GUI 相关）：
- `PySide6>=6.5.0`（如需 GUI 功能）

## 快速开始

### 方法1：运行示例脚本

安装完成后，进入 `examples` 目录运行示例：

```bash
# 进入示例目录
cd examples

# 快速开始示例（推荐首次使用）
python quick_start.py

# 完整功能演示
python full_demo.py

# 参数标定工具
python calibration_demo.py
```

### 方法2：嵌入到自己的脚本

```python
from flamekit import FlameKit, __version__

print(f"FlameKit version: {__version__}")

kit = FlameKit()

# 1) 预览
kit.preview(seconds=3)

# 2) 采集 1 秒到临时目录（会清空目录）
images, n = kit.capture_one_second()
print("采集帧数:", n)

# 3) 设置标定（mm_per_pixel）
kit.set_calibration(mm_per_pixel=0.3152)

# 4) 分析（自动标注并替换原图）
max_result, max_img_path = kit.analyze(images, save_annotated=True)
print("最大火焰长度(mm):", max_result.get("max_length_mm"))
print("对应图片:", max_img_path)

# 5) 播放约 1 秒（可调速度倍率）
kit.play_analyzed(images, speed=1.0, target_fps=240, duration_s=1.0)

# 6) 保存最大火焰标注图，并打印原图路径
kit.save_max_result()

# 7) 释放资源
kit.release()
```

## 主要接口

### `initialize() -> bool`
初始化相机（其他方法会自动调用，通常无需手动调用）

### `preview(seconds=3.0, window_name='Preview')`
相机画面预览
- `seconds`: 预览时长（秒）
- `window_name`: 窗口名称
- 按 ESC 键可提前退出

### `capture_one_second(temp_dir=None) -> (List[str], int)`
高速采集1秒图像
- `temp_dir`: 临时目录（默认 `./temp_captures`）
- 返回: `(图像路径列表, 帧数)`
- 注意: 会清空临时目录

### `set_calibration(mm_per_pixel: float)`
设置标定参数
- `mm_per_pixel`: 每像素对应的毫米数
- 配置会自动保存到用户配置文件

### `analyze(image_paths=None, save_annotated=True) -> (dict, str)`
批量分析火焰图像
- `image_paths`: 图像路径列表（默认使用最后一次采集的图像）
- `save_annotated`: 是否保存标注图像并替换原图
- 返回: `(最大结果字典, 对应图像路径)`

结果字典包含：
```python
{
    'success': bool,           # 是否分析成功
    'max_length_mm': float,    # 最大火焰长度(mm)
    'max_width_mm': float,     # 最大火焰宽度(mm)
    'area_mm2': float,         # 火焰面积(mm²)
    'annotated_image': ndarray # 标注后的图像
}
```

### `play_analyzed(image_paths=None, speed=1.0, window_name='Playback', target_fps=240, duration_s=1.0)`
播放分析后的图像
- `image_paths`: 图像路径列表（默认使用最后一次采集的图像）
- `speed`: 播放速度倍率（1.0=正常，0.5=慢速，2.0=快速）
- `target_fps`: 目标帧率
- `duration_s`: 播放时长（秒）
- 按 ESC 键可提前退出

### `save_max_result(output_dir=None) -> Optional[str]`
保存最大火焰长度的标注图
- `output_dir`: 输出目录（默认 `./results`）
- 返回: 保存路径
- 同时会打印原图路径到控制台

### `release()`
释放相机资源

## 文档导航

根据您的需求，选择合适的文档：

- **👋 初次使用** - 从这里开始！
  - [简明使用手册.md](../文档/简明使用手册.md) - 5分钟快速上手（强烈推荐！）
  - [INSTALL.md](../文档/INSTALL.md) - 详细的安装步骤和SDK配置

- **📖 深入学习**
  - [USAGE.md](../文档/USAGE.md) - 详细的API文档和高级用法
  - [包说明.md](../文档/包说明.md) - 包的特性和总体介绍

- **💡 示例代码**
  - `examples/quick_start.py` - 最简单的使用方式
  - `examples/full_demo.py` - 完整的功能演示
  - `examples/calibration_demo.py` - 参数标定工具

## 目录结构

```
flame_package/
├── flamekit/                    # 核心包
│   ├── __init__.py              # 包初始化，导出 FlameKit 和 __version__
│   ├── core.py                  # 主类 FlameKit
│   ├── config.py                 # 配置管理
│   ├── camera.py                 # 相机采集封装
│   ├── analyzer.py               # 火焰图像分析
│   ├── mvsdk.py                  # 工业相机 SDK 的 Python 封装（已内置）
│   ├── config_default.json       # 包内默认配置文件
│   └── README.md                 # 本文档
│
├── examples/                     # 示例代码
│   ├── quick_start.py            # 快速开始
│   ├── full_demo.py              # 完整演示
│   └── calibration_demo.py      # 参数标定
│
├── 文档/                         # 文档目录
│   ├── INSTALL.md                # 安装指南
│   ├── USAGE.md                  # API文档
│   ├── 简明使用手册.md            # 快速手册
│   └── 包说明.md                  # 包介绍
│
├── setup.py                      # 安装脚本
├── requirements.txt              # 依赖列表
├── config.example.json           # 配置示例
├── LICENSE                       # MIT许可证
└── README_FIRST.txt              # 首次使用指南
```

## 配置文件

FlameKit 使用三级配置优先级策略：

1. **当前目录配置**（最高优先级）：`./config.json`
   - 如果当前工作目录存在 `config.json`，优先使用
   - 适用于项目特定的配置

2. **用户目录配置**：`~/.flamekit/config.json`（Linux/Mac）或 `%APPDATA%/flamekit/config.json`（Windows）
   - 首次运行时自动从包内默认配置创建
   - 适用于用户全局配置

3. **包内默认配置**（最低优先级）：`flamekit/config_default.json`
   - 包内资源文件，只读
   - 作为后备配置

配置文件示例：

```json
{
    "camera": {
        "exposure_us": 4000,
        "resolution_index": 1,
        "force_mono": true,
        "capture_duration": 1.0
    },
    "calibration": {
        "mm_per_pixel": 0.3152,
        "reference_length_mm": 200.0
    },
    "analysis": {
        "binary_threshold": 0,
        "min_flame_area": 1000,
        "use_otsu": true
    },
    "paths": {
        "temp_dir": "./temp_captures",
        "output_dir": "./results"
    }
}
```

## 常见问题

### Q: ModuleNotFoundError: No module named 'flamekit'

**A:** 使用 pip 安装：
```bash
# 在 flame_package 目录下执行
pip install -e .
```

详细安装步骤请查看 [INSTALL.md](../文档/INSTALL.md)

### Q: 相机初始化失败

**A:** 检查：
1. 相机硬件连接
2. 相机驱动已安装
3. 相机厂商运行库（DLL/so）可被系统加载（例如 DLL 位于系统 PATH 或当前目录）

### Q: 如何调整采集参数？

**A:** 通过代码修改（推荐）：
```python
kit.config.set('camera.exposure_us', 5000)
```

或直接编辑配置文件（按优先级查找：当前目录 > 用户目录 > 包内默认配置）

### Q: 标定参数如何确定？

**A:** 推荐使用交互式标定工具：
```bash
cd examples
python calibration_demo.py
```

或手动计算：
1. 放置已知长度的参考物在相机视野中
2. 测量参考物在图像中的像素长度
3. 计算: `mm_per_pixel = 实际长度(mm) / 像素长度(px)`
4. 使用 `kit.set_calibration(mm_per_pixel)` 设置

## 设计原则

遵循 **Less is More** 和 **最小可用原则**：

- ✅ 提供简洁的高层接口
- ✅ 避免过度封装和复杂依赖
- ✅ 专注核心功能实现
- ✅ 代码即文档，接口清晰
- ✅ 标准包结构，易于集成

## 技术支持

如遇问题：

1. **安装问题**: 查看 [INSTALL.md](../文档/INSTALL.md) 安装指南
2. **使用问题**: 查看 [简明使用手册.md](../文档/简明使用手册.md) 快速上手
3. **API问题**: 查看 [USAGE.md](../文档/USAGE.md) 详细文档
4. **运行示例**: 参考 `examples/` 目录下的示例代码

## 版本信息

- **当前版本**: 0.1.0
- **Python要求**: >= 3.7
- **许可证**: MIT License

## 快速参考

| 操作 | 代码 |
|------|------|
| 初始化 | `kit.initialize()` |
| 预览 | `kit.preview(seconds=3.0)` |
| 采集 | `images, count = kit.capture_one_second()` |
| 分析 | `result, max_img = kit.analyze()` |
| 保存 | `kit.save_max_result()` |
| 释放 | `kit.release()` |

---

**开始使用**: 查看 [简明使用手册.md](../文档/简明使用手册.md) 或运行 `examples/quick_start.py`
