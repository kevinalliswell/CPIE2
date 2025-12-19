# Modbus多设备通信包 API 文档

## 目录
- [概述](#概述)
- [快速开始](#快速开始)
- [核心类](#核心类)
  - [ModbusDeviceManager](#modbusdevicemanager)
  - [ConfigLoader](#configloader)
  - [DataPoller](#datapoller)
  - [ControlExecutor](#controlexecutor)
- [设备类](#设备类)
- [配置文件](#配置文件)
- [使用示例](#使用示例)

---

## 概述

`modbus_multi_device` 是一个用于管理多个Modbus设备通信的Python包。支持：

- **多设备管理**: 统一管理多个不同类型的Modbus设备
- **自动轮询**: 独立线程定时采集各设备数据
- **控制优先级**: 控制命令支持优先级队列
- **灵活配置**: 支持YAML配置文件或代码配置
- **可扩展**: 易于添加新的设备类型

### 支持的设备类型

| 设备类型 | 配置类型标识 | 说明 |
|---------|------------|------|
| 智能数显压力表 | `pressure_sensor` | 读取压力值、设置报警参数 |
| DAM-3944A继电器 | `relay_controller` | 控制继电器开关 |
| DAM-3138温度模块 | `temperature_sensor` | 读取8通道温度数据 |
| 宇电AI温控仪表 | `yudian_controller` | 读取温度、控制PID参数 |

---

## 快速开始

### 安装

**从源码安装：**
```bash
cd modbus_multi_device
pip install -e .
```

**手动安装依赖：**
```bash
pip install pyserial>=3.5 pymodbus>=3.0.0 pyyaml>=6.0
```

### 基本使用

```python
from modbus_multi_device import ModbusDeviceManager

# 1. 创建管理器
manager = ModbusDeviceManager(config_path='config.yaml')

# 2. 连接设备
if manager.connect():
    # 3. 启动数据采集
    manager.start()
    
    # 4. 获取数据
    data = manager.get_latest_data('压力表1')
    print(f"压力: {data['pressure']}")
    
    # 5. 发送控制命令
    manager.send_control(
        device_name='继电器模块',
        control_data={'set_relay': {'relay': 1, 'state': True}},
        priority='high'
    )
    
    # 6. 停止并断开
    manager.stop()
    manager.disconnect()
```

---

## 核心类

### ModbusDeviceManager

主管理类，负责统一管理所有Modbus设备。

#### 初始化

```python
ModbusDeviceManager(config_path=None, config_dict=None)
```

**参数:**
- `config_path` (str, optional): 配置文件路径
- `config_dict` (dict, optional): 配置字典

**注意:** `config_path` 和 `config_dict` 二选一。

**示例:**
```python
# 使用配置文件
manager = ModbusDeviceManager(config_path='config.yaml')

# 使用配置字典
config = {
    'serial': {'port': 'COM3', 'baudrate': 9600},
    'devices': [...]
}
manager = ModbusDeviceManager(config_dict=config)
```

#### 方法

##### connect()

连接到串口并初始化所有设备。

```python
manager.connect() -> bool
```

**返回:** 
- `bool`: 是否连接成功

**示例:**
```python
if manager.connect():
    print("连接成功")
else:
    print("连接失败")
```

---

##### disconnect()

断开串口连接并停止所有操作。

```python
manager.disconnect()
```

**示例:**
```python
manager.disconnect()
```

---

##### start()

启动数据轮询和控制执行器。

```python
manager.start() -> bool
```

**返回:**
- `bool`: 是否启动成功

**示例:**
```python
manager.start()
```

---

##### stop()

停止数据轮询和控制执行器。

```python
manager.stop()
```

**示例:**
```python
manager.stop()
```

---

##### send_control()

发送控制命令到指定设备。

```python
manager.send_control(
    device_name: str,
    control_data: dict,
    priority: str = 'normal'
) -> bool
```

**参数:**
- `device_name` (str): 设备名称
- `control_data` (dict): 控制数据字典
- `priority` (str): 优先级 ('high', 'normal', 'low')

**返回:**
- `bool`: 是否成功加入控制队列

**示例:**
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
    priority='high'
)

# 设置温控仪表给定值
manager.send_control(
    device_name='温控仪表',
    control_data={
        'set_setpoint': {
            'value': 100.0
        }
    }
)
```

---

##### get_latest_data()

获取最新采集的数据。

```python
manager.get_latest_data(device_name: str = None) -> dict
```

**参数:**
- `device_name` (str, optional): 设备名称，None返回所有设备

**返回:**
- `dict`: 设备数据字典

**示例:**
```python
# 获取单个设备数据
data = manager.get_latest_data('压力表1')
print(f"压力: {data['pressure']}")

# 获取所有设备数据
all_data = manager.get_latest_data()
for device, data in all_data.items():
    print(f"{device}: {data}")
```

---

##### get_data_history()

获取历史数据记录。

```python
manager.get_data_history(
    device_name: str = None,
    count: int = None
) -> list
```

**参数:**
- `device_name` (str, optional): 设备名称，None返回所有设备
- `count` (int, optional): 返回数量，None返回全部

**返回:**
- `list`: 数据字典列表

**示例:**
```python
# 获取最近10条压力表数据
history = manager.get_data_history('压力表1', count=10)

# 获取所有历史数据
all_history = manager.get_data_history()
```

---

##### get_device_status()

获取设备状态信息。

```python
manager.get_device_status(device_name: str = None) -> dict
```

**参数:**
- `device_name` (str, optional): 设备名称，None返回所有设备

**返回:**
- `dict`: 状态字典

**示例:**
```python
# 单个设备状态
status = manager.get_device_status('压力表1')
print(f"错误次数: {status['error_count']}")

# 所有设备状态
all_status = manager.get_device_status()
```

---

##### get_system_status()

获取系统整体状态。

```python
manager.get_system_status() -> dict
```

**返回:**
- `dict`: 包含以下字段
  - `connected`: 是否已连接
  - `started`: 是否已启动
  - `devices_count`: 设备总数
  - `enabled_devices`: 启用的设备数
  - `latest_data_count`: 最新数据数量
  - `history_count`: 历史数据数量
  - `poller`: 轮询器状态
  - `executor`: 执行器状态

**示例:**
```python
status = manager.get_system_status()
print(f"系统状态: {status}")
```

---

##### add_data_callback()

添加自定义数据接收回调函数。

```python
manager.add_data_callback(callback: Callable)
```

**参数:**
- `callback` (function): 回调函数，参数为数据字典

**示例:**
```python
def my_callback(data):
    device = data.get('device')
    print(f"收到数据: {device}")
    
manager.add_data_callback(my_callback)
```

---

##### add_control_callback()

添加自定义控制结果回调函数。

```python
manager.add_control_callback(callback: Callable)
```

**参数:**
- `callback` (function): 回调函数，参数为结果字典

**示例:**
```python
def my_callback(result):
    if result['success']:
        print(f"控制成功: {result['device_name']}")
    else:
        print(f"控制失败: {result['error']}")

manager.add_control_callback(my_callback)
```

---

### ConfigLoader

配置文件加载和管理类。

#### 初始化

```python
ConfigLoader(config_path: str = None)
```

**参数:**
- `config_path` (str, optional): 配置文件路径

#### 方法

##### load()

加载YAML配置文件。

```python
loader.load(config_path: str) -> dict
```

##### save()

保存配置到YAML文件。

```python
loader.save(config: dict, config_path: str = None)
```

##### create_template()

创建配置文件模板。

```python
ConfigLoader.create_template(save_path: str)
```

**示例:**
```python
ConfigLoader.create_template('my_config.yaml')
```

---

### DataPoller

数据轮询器，负责定时采集设备数据。

**特点:**
- 每个设备独立线程轮询
- 可配置独立的轮询间隔
- 自动错误处理和回调

---

### ControlExecutor

控制命令执行器，负责执行控制命令。

**特点:**
- 优先级队列（高/中/低）
- 控制命令优先于数据采集
- 超时处理机制

---

## 设备类

### 通用接口

所有设备类继承自 `BaseDevice`，提供统一接口：

```python
class BaseDevice:
    def read_data(self) -> dict
    def write_control(self, control_data: dict) -> bool
    def get_status(self) -> dict
```

---

### PressureSensorDevice (智能数显压力表)

#### 数据格式

```python
{
    'device': '压力表1',
    'type': 'pressure_sensor',
    'raw_value': 1000,
    'pressure': 100.0,
    'unit': 'KPa',
    'decimal_point': 1,
    'timestamp': 1234567890.0
}
```

#### 控制命令

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

---

### RelayControllerDevice (继电器模块)

#### 数据格式

```python
{
    'device': '继电器模块',
    'type': 'relay_controller',
    'relays': {
        'relay_1': True,
        'relay_2': False,
        'relay_3': True,
        'relay_4': False
    },
    'timestamp': 1234567890.0
}
```

#### 控制命令

```python
# 控制单个继电器
control_data = {
    'set_relay': {
        'relay': 1,  # 1-4
        'state': True  # True=导通, False=断开
    }
}

# 控制所有继电器
control_data = {
    'set_all': {
        'states': [True, False, True, False]
    }
}
```

---

### TemperatureSensorDevice (温度采集模块)

#### 数据格式

```python
{
    'device': '温度采集模块',
    'type': 'temperature_sensor',
    'channels': [
        {
            'channel': 0,
            'raw_value': 3686,
            'temperature': 35.0,
            'unit': '°C'
        },
        # ... 其他7个通道
    ],
    'timestamp': 1234567890.0
}
```

#### 控制命令

温度传感器不支持控制命令（只读设备）。

---

### YudianControllerDevice (宇电温控仪表)

#### 数据格式

```python
{
    'device': '温控仪表',
    'type': 'yudian_controller',
    'pv': 25.5,  # 测量值
    'sv': 100.0,  # 给定值
    'mv': 45.2,  # 输出值(%)
    'timestamp': 1234567890.0
}
```

#### 控制命令

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
        'P': 10.0,  # 比例带
        'I': 120,   # 积分时间(秒)
        'D': 3.0    # 微分时间(0.1秒)
    }
}
```

---

## 配置文件

### YAML配置格式

```yaml
# 串口配置
serial:
  port: 'COM3'
  baudrate: 9600
  bytesize: 8
  parity: 'N'
  stopbits: 1
  timeout: 1.0

# 设备配置
devices:
  - name: '压力表1'
    type: 'pressure_sensor'
    address: 1
    enabled: true
    poll_interval: 1.0
    parameters: {}

  - name: '继电器模块'
    type: 'relay_controller'
    address: 3
    enabled: true
    poll_interval: 2.0
    parameters: {}

# 轮询配置
polling:
  enabled: true
  default_interval: 1.0
  error_retry_delay: 5.0
  max_retries: 3

# 日志配置
logging:
  enabled: true
  level: 'INFO'
  save_to_file: true
  log_dir: 'logs'
```

---

## 使用示例

### 示例1: 监控压力并自动控制

```python
from modbus_multi_device import ModbusDeviceManager

def pressure_monitor(data):
    """监控压力，超限时自动关闭继电器"""
    if data.get('type') == 'pressure_sensor':
        pressure = data['pressure']
        print(f"当前压力: {pressure}")
        
        if pressure > 900:
            print("⚠️ 压力超限，关闭继电器")
            manager.send_control(
                device_name='继电器模块',
                control_data={'set_relay': {'relay': 1, 'state': False}},
                priority='high'
            )

manager = ModbusDeviceManager(config_path='config.yaml')
manager.connect()
manager.add_data_callback(pressure_monitor)
manager.start()

# 持续运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    manager.stop()
    manager.disconnect()
```

### 示例2: 温度控制循环

```python
def temperature_control(data):
    """根据温度自动调整PID参数"""
    if data.get('type') == 'yudian_controller':
        pv = data['pv']  # 当前温度
        sv = data['sv']  # 给定温度
        
        error = sv - pv
        
        if abs(error) > 50:
            # 偏差较大，增大比例带
            manager.send_control(
                device_name='温控仪表',
                control_data={'set_pid': {'P': 20.0}}
            )

manager = ModbusDeviceManager(config_path='config.yaml')
manager.connect()
manager.add_data_callback(temperature_control)
manager.start()
```

### 示例3: 数据记录与分析

```python
import json
from datetime import datetime

manager = ModbusDeviceManager(config_path='config.yaml')
manager.connect()
manager.start()

# 运行一段时间
time.sleep(60)

# 获取历史数据
history = manager.get_data_history('压力表1')

# 计算统计数据
pressures = [d['pressure'] for d in history]
avg_pressure = sum(pressures) / len(pressures)
max_pressure = max(pressures)
min_pressure = min(pressures)

print(f"平均压力: {avg_pressure:.2f}")
print(f"最大压力: {max_pressure:.2f}")
print(f"最小压力: {min_pressure:.2f}")

# 保存到文件
with open(f'pressure_log_{datetime.now():%Y%m%d}.json', 'w') as f:
    json.dump(history, f, indent=2)

manager.stop()
manager.disconnect()
```

---

## 错误处理

### 常见错误

1. **连接失败**
   - 检查串口号是否正确
   - 确认设备已上电并连接
   - 验证波特率等参数

2. **设备读取失败**
   - 检查设备地址是否正确
   - 确认设备通讯正常
   - 查看日志中的详细错误信息

3. **控制命令失败**
   - 确认控制数据格式正确
   - 检查设备是否支持该控制命令
   - 查看控制结果回调中的错误信息

### 错误回调

```python
def on_error(device_name, error):
    print(f"设备错误 [{device_name}]: {error}")
    # 可以在这里实现错误恢复逻辑

manager.add_data_callback(...)
# 添加错误处理回调需要访问poller对象
if manager.poller:
    manager.poller.add_error_callback(on_error)
```

---

## 最佳实践

1. **合理设置轮询间隔**: 根据设备响应速度和数据变化频率设置
2. **使用优先级**: 关键控制命令使用高优先级
3. **添加回调函数**: 实现业务逻辑的最佳方式
4. **日志记录**: 启用日志以便故障排查
5. **错误处理**: 实现错误回调以便及时响应
6. **资源清理**: 使用try-finally确保正确关闭连接

---

## 扩展开发

### 添加新设备类型

1. 创建设备类，继承 `BaseDevice`
2. 实现 `read_data()` 和 `write_control()` 方法
3. 在 `devices.py` 的 `DEVICE_TYPES` 中注册
4. 更新配置文件和文档

```python
class MyDevice(BaseDevice):
    def read_data(self):
        # 实现数据读取逻辑
        pass
    
    def write_control(self, control_data):
        # 实现控制逻辑
        pass

# 注册设备类型
DEVICE_TYPES['my_device'] = MyDevice
```

---

---

## 测试

包含完整的单元测试：

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python tests/test_config.py

# 查看测试覆盖率（需要安装 pytest-cov）
python -m pytest tests/ --cov=modbus_multi_device
```

---

## 示例代码

查看 `examples/` 目录获取完整的使用示例：

- `example_config.yaml` - 配置文件示例
- `example_usage.py` - 完整的使用示例代码

运行示例：
```bash
python examples/example_usage.py
```

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 技术支持

如有问题或建议，请提交 Issue 或联系技术支持团队。
