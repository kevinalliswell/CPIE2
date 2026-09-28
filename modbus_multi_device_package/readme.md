# Modbus Multi-Device Communication Package

一个用于管理多个Modbus设备通信的Python包，支持数据采集轮询和控制命令优先级队列。

## 特性

✅ **多设备管理**: 统一管理多个不同类型的Modbus设备  
✅ **自动轮询**: 每个设备独立线程定时采集数据  
✅ **控制优先级**: 支持高/中/低优先级控制队列  
✅ **灵活配置**: YAML配置文件或代码配置  
✅ **回调机制**: 支持自定义数据和控制结果回调  
✅ **历史数据**: 自动保存历史数据记录  
✅ **日志系统**: 完善的日志记录功能  
✅ **易于扩展**: 简单添加新设备类型

## 支持的设备

| 设备类型 | 型号 | 功能 |
|---------|------|------|
| 智能数显压力表 | MT-DPC50R | 压力监测、报警设置 |
| 继电器模块 | DAM-3944A | 4路继电器控制 |
| 温度采集模块 | DAM-3138 | 8通道温度采集 |
| 温控仪表 | 宇电516P | 温度控制、PID参数 |

## 安装

### 依赖要求

- Python 3.10+
- pyserial
- pymodbus
- PyYAML

### 安装步骤

**方式 1: 从源码安装（开发模式）**
```bash
# 克隆或下载包到本地
cd modbus_multi_device

# 安装依赖
pip install -r requirements.txt

# 开发模式安装（推荐）
pip install -e .
```

**方式 2: 手动安装依赖**
```bash
pip install "pyserial>=3.5" "pymodbus>=3.10.0,<4.0.0" "pyyaml>=6.0"
```

**方式 3: 使用 pip 安装（如果已发布）**
```bash
pip install modbus_multi_device
```

### 包结构

```
modbus_multi_device/
├── modbus_multi_device/     # 主包目录
│   ├── __init__.py          # 包初始化
│   ├── manager.py           # 设备管理器
│   ├── devices.py           # 设备驱动类
│   ├── poller.py            # 轮询器和执行器
│   └── config.py            # 配置加载器
├── examples/                # 示例文件
│   ├── example_config.yaml  # 配置文件示例
│   └── example_usage.py     # 使用示例
├── tests/                   # 测试文件
│   └── test_config.py       # 配置测试
├── pyproject.toml           # 项目配置
├── setup.py                 # 安装脚本
├── requirements.txt         # 依赖列表
├── LICENSE                  # 许可证
├── api_doc.md               # API文档
└── readme.md                # 本文件
```

## 快速开始

### 1. 创建配置文件

```python
from modbus_multi_device import ConfigLoader

# 创建配置模板
ConfigLoader.create_template('config.yaml')
```

### 2. 编辑配置文件

```yaml
serial:
  port: 'COM3'
  baudrate: 9600

devices:
  - name: '压力表1'
    type: 'pressure_sensor'
    address: 1
    enabled: true
    poll_interval: 1.0
```

### 3. 运行程序

```python
from modbus_multi_device import ModbusDeviceManager
import time

# 创建管理器
manager = ModbusDeviceManager(config_path='config.yaml')

# 连接并启动
if manager.connect():
    manager.start()
    
    # 获取数据
    time.sleep(2)
    data = manager.get_latest_data('压力表1')
    print(f"压力: {data['pressure']}")
    
    # 发送控制命令
    manager.send_control(
        device_name='继电器模块',
        control_data={'set_relay': {'relay': 1, 'state': True}},
        priority='high'
    )
    
    # 停止
    manager.stop()
    manager.disconnect()
```

## 使用示例

### 示例1: 基本数据采集

```python
manager = ModbusDeviceManager(config_path='config.yaml')
manager.connect()
manager.start()

# 运行5秒
time.sleep(5)

# 获取所有设备的最新数据
all_data = manager.get_latest_data()
for device_name, data in all_data.items():
    print(f"{device_name}: {data}")

manager.stop()
manager.disconnect()
```

### 示例2: 自定义回调处理

```python
def on_pressure_data(data):
    if data.get('type') == 'pressure_sensor':
        pressure = data['pressure']
        if pressure > 900:
            print(f"⚠️ 压力超限: {pressure}")

manager = ModbusDeviceManager(config_path='config.yaml')
manager.connect()
manager.add_data_callback(on_pressure_data)
manager.start()
```

### 示例3: 控制命令

```python
# 控制继电器
manager.send_control(
    device_name='继电器模块',
    control_data={
        'set_relay': {
            'relay': 1,
            'state': True
        }
    },
    priority='high'  # 高优先级
)

# 设置温控仪表
manager.send_control(
    device_name='温控仪表',
    control_data={
        'set_setpoint': {
            'value': 100.0
        }
    }
)
```

### 示例4: 历史数据查询

```python
# 获取最近10条压力数据
history = manager.get_data_history('压力表1', count=10)

# 计算平均值
pressures = [d['pressure'] for d in history]
avg_pressure = sum(pressures) / len(pressures)
print(f"平均压力: {avg_pressure:.2f}")
```

## 配置说明

### 串口配置

```yaml
serial:
  port: 'COM3'          # 串口号
  baudrate: 9600        # 波特率
  bytesize: 8           # 数据位
  parity: 'N'           # 校验位
  stopbits: 1           # 停止位
  timeout: 1.0          # 超时时间
```

### 设备配置

```yaml
devices:
  - name: '设备名称'
    type: 'device_type'      # 设备类型
    address: 1               # Modbus地址
    enabled: true            # 是否启用
    poll_interval: 1.0       # 轮询间隔(秒)
    parameters:              # 设备特定参数
      key: value
```

### 轮询配置

```yaml
polling:
  enabled: true              # 启用自动轮询
  default_interval: 1.0      # 默认间隔
  error_retry_delay: 5.0     # 错误重试延时
  max_retries: 3             # 最大重试次数
```

## 设备控制命令

### 压力表 (pressure_sensor)

```python
# 设置报警1
control_data = {
    'set_alarm1': {
        'threshold': 500.0,
        'hysteresis': 10.0
    }
}

# 设置报警2
control_data = {
    'set_alarm2': {
        'threshold': 800.0,
        'hysteresis': 20.0
    }
}
```

### 继电器 (relay_controller)

```python
# 控制单个继电器
control_data = {
    'set_relay': {
        'relay': 1,      # 1-4
        'state': True    # True=导通, False=断开
    }
}

# 控制所有继电器
control_data = {
    'set_all': {
        'states': [True, False, True, False]
    }
}
```

### 温控仪表 (yudian_controller)

```python
# 设置给定值
control_data = {
    'set_setpoint': {
        'value': 100.0
    }
}

# 设置运行状态
control_data = {
    'set_run_status': {
        'status': 'run'  # 'run', 'StoP', 'HoLd'
    }
}

# 设置PID参数
control_data = {
    'set_pid': {
        'P': 10.0,
        'I': 120,
        'D': 3.0
    }
}
```

## API文档

详细的API文档请参考 [api_doc.md](api_doc.md)

## 常见问题

### Q: 如何添加新的设备类型？

A: 参考 `devices.py` 中的设备类，继承 `BaseDevice` 并实现 `read_data()` 和 `write_control()` 方法，然后在 `DEVICE_TYPES` 中注册。

### Q: 为什么设备连接失败？

A: 请检查：
1. 串口号是否正确
2. 设备地址是否匹配
3. 波特率等参数是否正确
4. 设备是否上电

### Q: 如何调整轮询频率？

A: 在配置文件中设置每个设备的 `poll_interval` 参数。

### Q: 控制命令为什么没有立即执行？

A: 控制命令通过优先级队列执行，可能需要等待。使用 `priority='high'` 可以提高优先级。

## 性能说明

- **轮询机制**: 每个设备独立线程，互不干扰
- **控制优先级**: 控制命令队列优先级高于数据采集
- **历史数据**: 默认保存最近1000条记录
- **线程安全**: 所有操作线程安全

## 注意事项

1. 确保串口未被其他程序占用
2. 设备地址必须唯一且正确
3. 建议根据设备响应速度设置合理的轮询间隔
4. 及时处理错误回调，避免累积错误
5. 程序退出前务必调用 `disconnect()`

## 测试

运行测试套件：

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python tests/test_config.py

# 运行示例
python examples/example_usage.py
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 更新日志

### v1.0.0 (2024-11-26)
- 初始版本发布
- 支持4种常用Modbus设备
- 实现轮询机制和控制优先级
- 完善的日志和配置系统

## 技术支持

如有问题或建议，请联系技术支持团队。
