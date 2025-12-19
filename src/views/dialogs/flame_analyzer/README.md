# 火焰分析仪优化版

## 项目概述

这是煤粉燃烧火焰图像分析系统的优化版本,用于分析高速相机拍摄的火焰图像,计算火焰尺寸并生成统计报告。

## 主要改进

### 1. **配置文件化** ✅
- 使用 YAML 配置文件管理所有参数
- `flame_threshold` 和 `pixel_scale` 从配置文件读取
- 支持动态更新配置

### 2. **架构优化** ✅
- **分离关注点**: UI逻辑与业务逻辑完全分离
- **配置管理类**: `FlameAnalyzerConfig` 统一管理配置
- **业务逻辑类**: `FlameImageProcessor` 处理图像分析
- **UI控件类**: `FlameAnalyzerWidget` 专注用户交互

### 3. **性能提升** ✅
- **流式处理**: 不再一次性加载所有图像到内存
- **优化进度更新**: 减少UI刷新频率,提升响应速度
- **处理性能**: 100张图像约0.65秒 (~6.5ms/张)

### 4. **代码质量** ✅
- **类型提示**: 使用 Python 类型标注
- **数据类**: 使用 `@dataclass` 管理数据结构
- **异常处理**: 完善的错误处理和日志记录
- **路径管理**: 使用 `pathlib.Path` 替代字符串拼接

### 5. **可维护性** ✅
- **日志系统**: 完整的日志记录功能
- **配置验证**: 自动验证配置参数合法性
- **单元测试友好**: 支持依赖注入,便于测试

## 文件结构

```
.
├── flame_analyzer_config.yaml   # 配置文件
├── config_manager.py            # 配置管理类
├── flame_processor.py           # 图像处理业务逻辑
├── flame_analyzer_widget.py     # UI控件
├── test_flame_analyzer.py       # 测试脚本
└── README.md                    # 说明文档
```

## 依赖安装

```bash
pip install pyyaml opencv-python numpy PySide6
```

## 配置文件说明

### flame_analyzer_config.yaml

```yaml
# 图像处理参数
image_processing:
  flame_threshold: 128     # 火焰检测阈值 (0-255)
  pixel_scale: 10.0        # 像素到毫米的转换比例

# 文件路径配置
paths:
  history_csv: "data/exp_explosion/history_explosion.csv"
  exp_data_json: "data/exp_explosion/explosion_experiment_data.json"

# 支持的图像格式
image_formats:
  - ".jpg"
  - ".jpeg"
  - ".png"

# UI配置
ui:
  window_title: "火焰图像分析"
  progress_update_interval: 10  # 每处理N张图片更新一次进度

# OpenCV绘图参数
opencv:
  font: "FONT_HERSHEY_SIMPLEX"
  font_scale: 0.5
  text_color: [0, 255, 0]     # BGR格式
  text_thickness: 2

# 性能配置
performance:
  stream_processing: true       # 启用流式处理
```

## 快速开始

### 1. 基本使用

```python
from config_manager import FlameAnalyzerConfig
from flame_processor import FlameImageProcessor

# 加载配置
config = FlameAnalyzerConfig("flame_analyzer_config.yaml")

# 创建处理器
processor = FlameImageProcessor(config)

# 批量处理图像
input_folder = "path/to/input/images"
output_folder = "path/to/output/images"

results = processor.batch_process_images(input_folder, output_folder)

# 计算统计数据
stats = processor.calculate_statistics(results)

print(f"最大火焰: {stats.max_flame_size} mm")
print(f"平均火焰: {stats.average_flame_size} mm")
```

### 2. UI使用

```python
from PySide6.QtWidgets import QApplication
from flame_analyzer_widget import FlameAnalyzerWidget
import sys

app = QApplication(sys.argv)

# 创建窗口
window = FlameAnalyzerWidget("path/to/input/folder")

# 连接信号
window.window_closed.connect(lambda results: print(f"分析完成: {results}"))

window.show()
sys.exit(app.exec())
```

### 3. 自定义配置

```python
from config_manager import FlameAnalyzerConfig

# 加载配置
config = FlameAnalyzerConfig()

# 修改参数
config.update_config('image_processing.flame_threshold', 150)
config.update_config('image_processing.pixel_scale', 12.0)

# 保存配置
config.save_config("custom_config.yaml")
```

## 测试

运行完整的测试套件:

```bash
python test_flame_analyzer.py
```

测试内容包括:
- ✅ 配置管理器功能
- ✅ YAML配置文件读取
- ✅ 图像处理器功能
- ✅ 批量处理性能
- ✅ UI控件创建

## 性能基准

| 图像数量 | 处理时间 | 平均耗时 |
|---------|---------|---------|
| 10张    | 0.06秒  | 6.2ms/张 |
| 50张    | 0.33秒  | 6.6ms/张 |
| 100张   | 0.65秒  | 6.5ms/张 |

## API文档

### FlameAnalyzerConfig

配置管理类,从YAML文件加载并验证配置参数。

**主要属性:**
- `flame_threshold: int` - 火焰检测阈值
- `pixel_scale: float` - 像素到毫米的转换比例
- `image_formats: Tuple[str]` - 支持的图像格式

**主要方法:**
- `update_config(key_path, value)` - 更新配置项
- `save_config(output_path)` - 保存配置到文件
- `print_config()` - 打印当前配置

### FlameImageProcessor

图像处理业务逻辑类。

**主要方法:**
- `detect_flame(img)` - 检测单张图像的火焰
- `process_single_image(path)` - 处理单张图像
- `batch_process_images(input_folder, output_folder)` - 批量处理
- `calculate_statistics(results)` - 计算统计数据

### FlameAnalyzerWidget

PySide6 UI控件类。

**信号:**
- `window_closed(dict)` - 窗口关闭时发出,携带分析结果

**主要方法:**
- `on_analyze_image_clicked()` - 开始分析
- `on_item_selection_changed()` - 列表选择变化

## 数据结构

### FlameAnalysisResult

```python
@dataclass
class FlameAnalysisResult:
    filename: str
    flame_size_mm: int
    flame_region: Tuple[int, int, int, int]
    success: bool
    error_message: str
```

### FlameStatistics

```python
@dataclass
class FlameStatistics:
    max_flame_size: int
    min_flame_size: int
    average_flame_size: float
    max_flame_index: int
    max_flame_file: str
    total_images: int
    failed_images: int
```

## 日志

日志文件位置: `logs/flame_analyzer.log`

日志级别: DEBUG, INFO, WARNING, ERROR

示例日志:
```
2025-11-27 01:24:58 - FlameImageProcessor - INFO - 在 /tmp/test 中找到 5 个图像文件
2025-11-27 01:24:58 - FlameImageProcessor - INFO - 已保存标注图像: /tmp/output/test_001.jpg
2025-11-27 01:24:58 - FlameImageProcessor - INFO - 统计完成: 最大=28mm, 最小=9mm, 平均=18.0mm
```

## 常见问题

### Q: 如何调整火焰检测阈值?

A: 修改配置文件中的 `image_processing.flame_threshold` 值,范围0-255。

### Q: 如何修改像素到毫米的转换比例?

A: 修改配置文件中的 `image_processing.pixel_scale` 值。

### Q: 如何支持更多图像格式?

A: 在配置文件的 `image_formats` 列表中添加格式,如 `".bmp"`。

### Q: 处理大量图像时内存占用过高?

A: 确保配置文件中 `performance.stream_processing` 设置为 `true`。

## 版本历史

### v2.0.0 (2024-11-27)
- ✨ 重构代码架构,分离业务逻辑和UI
- ✨ 添加YAML配置文件支持
- ✨ 实现流式处理,降低内存占用
- ✨ 添加完整的日志系统
- ✨ 添加数据类和类型提示
- ✨ 优化性能,减少UI更新频率
- ✨ 增强异常处理
- ✨ 添加完整的测试套件

### v1.0.0
- 初始版本

## 作者

Kevin / USTB

## 许可证

内部使用

## 联系方式

邮箱: shijinpeng06@126.com
