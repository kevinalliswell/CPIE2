# FlameKit 示例和测试说明

本目录包含 FlameKit 的各种示例和测试脚本，展示如何使用新增的参数化功能。

## 📋 文件列表

### 基础示例

1. **quick_start.py** - 快速开始示例
   - 最简单的使用方式
   - 展示完整的工作流程
   - 新增：显示相机支持的分辨率

2. **full_demo.py** - 完整功能演示
   - 展示所有高级功能
   - 详细的配置和参数说明
   - 新增：分辨率查询演示

3. **calibration_demo.py** - 参数标定工具
   - 交互式标定工具
   - 计算像素到毫米的转换参数
   - 新增：支持命令行指定分辨率

### 新增示例

4. **parameters_demo.py** - 参数化功能演示 ⭐ 新增
   - 展示如何使用自定义参数初始化
   - 分辨率查询功能演示
   - 6个完整的演示案例

### 测试脚本

5. **test_flamekit_complete.py** - 完整功能测试
   - 测试所有主要功能
   - 需要真实相机连接

6. **test_flamekit_unit.py** - 单元测试
   - 测试各个模块的独立功能
   - 更新：新增分辨率查询方法检查

7. **test_parameters.py** - 参数化功能测试 ⭐ 新增
   - 专门测试参数化初始化功能
   - 8个独立测试用例
   - 不需要相机也能运行部分测试

## 🚀 快速开始

### 方式1：使用默认配置

```python
from flamekit import FlameKit

kit = FlameKit()
kit.initialize()
kit.preview()
```

### 方式2：自定义分辨率

```python
from flamekit import FlameKit

# 0=最高分辨率，1=中等，2=最低
kit = FlameKit(resolution_index=0)
kit.initialize()
```

### 方式3：自定义多个参数

```python
from flamekit import FlameKit

kit = FlameKit(
    resolution_index=1,
    exposure_us=5000,      # 曝光时间（微秒）
    force_mono=True,       # 强制黑白模式
    capture_duration=1.0   # 采集时长（秒）
)
kit.initialize()
```

### 方式4：查询支持的分辨率

```python
from flamekit import FlameKit

kit = FlameKit()
kit.initialize()

# 打印所有支持的分辨率
kit.print_available_resolutions()

# 或获取分辨率列表
resolutions = kit.get_available_resolutions()
for idx, width, height in resolutions:
    print(f"索引 {idx}: {width}x{height}")
```

## 📖 运行示例

### 参数化功能演示（推荐先运行）

```bash
cd examples
python parameters_demo.py
```

这个演示展示了6个完整的使用案例，是了解新功能的最佳起点。

### 快速开始

```bash
cd examples
python quick_start.py
```

### 完整功能演示

```bash
cd examples
python full_demo.py
```

### 参数标定

```bash
cd examples
# 默认分辨率
python calibration_demo.py

# 指定分辨率索引
python calibration_demo.py 0  # 使用最高分辨率
```

### 运行测试

```bash
cd examples

# 参数化功能测试（推荐）
python test_parameters.py

# 单元测试
python test_flamekit_unit.py

# 完整功能测试（需要相机）
python test_flamekit_complete.py --full

# 最小测试（不需要相机）
python test_flamekit_complete.py --minimal
```

## 🆕 新增功能说明

### 1. 参数化初始化

现在可以在创建 FlameKit 或 CameraCapture 实例时直接传入参数：

**支持的参数：**
- `resolution_index` (int): 分辨率档位索引（0, 1, 2...）
- `exposure_us` (int): 曝光时间（微秒）
- `force_mono` (bool): 是否强制黑白模式
- `capture_duration` (float): 采集时长（秒）

**特性：**
- 所有参数都是可选的
- 传入的参数会自动保存到配置文件
- 不传参数时使用配置文件的默认值
- 参数优先级：传入参数 > 配置文件

### 2. 分辨率查询

新增两个方法用于查询相机支持的分辨率：

**`get_available_resolutions()`**
- 返回：`[(索引, 宽度, 高度), ...]`
- 用于编程方式获取分辨率列表

**`print_available_resolutions()`**
- 打印格式化的分辨率表格
- 用于交互式查看

### 3. 向后兼容

所有现有代码无需修改，完全向后兼容：

```python
# 旧代码仍然可以正常工作
kit = FlameKit()
kit.initialize()
```

## 💡 使用建议

1. **首次使用**：运行 `parameters_demo.py` 了解所有功能
2. **查看分辨率**：初始化后调用 `print_available_resolutions()` 查看相机支持的档位
3. **选择分辨率**：根据需求选择合适的索引（0=最高，数字越大分辨率越低）
4. **调整曝光**：火焰太亮时降低曝光时间，太暗时增加
5. **参数持久化**：传入的参数会自动保存，下次默认使用新参数

## 🔧 故障排除

### 问题1：相机初始化失败

```python
# 检查相机连接
kit = FlameKit()
if not kit.initialize():
    print("请检查：")
    print("1. 相机是否连接")
    print("2. 驱动是否安装")
    print("3. 其他程序是否占用相机")
```

### 问题2：分辨率索引无效

```python
# 先查询支持的分辨率
kit = FlameKit()
kit.initialize()
kit.print_available_resolutions()

# 然后使用有效的索引
```

### 问题3：参数没有保存

参数需要在调用 `initialize()` 后才会保存到配置文件：

```python
kit = FlameKit(resolution_index=0)
kit.initialize()  # 这时参数才会保存
```

## 📝 更多信息

- 查看 `parameters_demo.py` 了解详细用法
- 运行 `test_parameters.py` 测试所有功能
- 参考主目录的 `README.md` 获取完整文档


