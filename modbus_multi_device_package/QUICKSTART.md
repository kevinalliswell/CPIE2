# 快速开始指南

5分钟快速上手 Modbus Multi-Device 包。

## 第1步: 安装

```bash
cd modbus_multi_device
pip install -e .
```

验证安装：
```bash
python verify_install.py
```

## 第2步: 配置设备

复制配置文件模板：
```bash
cd examples
cp example_config.yaml my_config.yaml
```

编辑 `my_config.yaml`，修改串口参数：

```yaml
serial:
  port: 'COM3'        # 改为你的串口号
  baudrate: 9600
  timeout: 1.0

devices:
  - name: '压力表1'
    type: 'pressure_sensor'
    address: 1        # 改为你的设备地址
    enabled: true
    poll_interval: 1.0
```

## 第3步: 运行第一个程序

创建 `test.py`：

```python
from modbus_multi_device import ModbusDeviceManager
import time

# 创建管理器
manager = ModbusDeviceManager(config_path='my_config.yaml')

# 连接并启动
if manager.connect():
    print("连接成功!")
    manager.start()
    
    # 运行5秒
    time.sleep(5)
    
    # 获取数据
    data = manager.get_latest_data()
    print(f"数据: {data}")
    
    # 停止
    manager.stop()
    manager.disconnect()
else:
    print("连接失败!")
```

运行：
```bash
python test.py
```

## 第4步: 添加回调函数

```python
def on_data(data):
    device_name = data.get('device_name')
    print(f"收到 {device_name} 的数据: {data}")

manager = ModbusDeviceManager(config_path='my_config.yaml')
manager.add_data_callback(on_data)  # 添加回调
manager.connect()
manager.start()

time.sleep(10)

manager.stop()
manager.disconnect()
```

## 第5步: 发送控制命令

```python
# 示例：控制继电器
manager.send_control(
    device_name='继电器模块',
    control_data={
        'set_relay': {
            'relay': 1,      # 继电器1
            'state': True    # 开启
        }
    },
    priority='high'
)
```

## 常用操作

### 查看设备列表
```python
devices = manager.list_devices()
for name in devices:
    print(name)
```

### 获取单个设备数据
```python
data = manager.get_latest_data('压力表1')
print(f"压力: {data['pressure']} kPa")
```

### 查看历史数据
```python
history = manager.get_data_history('压力表1', count=10)
for record in history:
    print(record)
```

### 启用/禁用设备
```python
manager.enable_device('温度模块')
manager.disable_device('温度模块')
```

## 完整示例

查看 `examples/example_usage.py` 获取更多示例。

## 支持的设备类型

| 配置类型 | 说明 |
|---------|------|
| `pressure_sensor` | 智能数显压力表 |
| `relay_controller` | DAM-3944A 继电器 |
| `temperature_sensor` | DAM-3138 温度模块 |
| `yudian_controller` | 宇电AI温控仪表 |

## 常见问题

**Q: 为什么安装失败？**
- pip install -e . 报错：
      Installing build dependencies ... error
      error: subprocess-exited-with-error
- 解决办法：  pip install setuptools wheel --upgrade

**Q: 找不到串口?**
- Windows: 查看设备管理器 (COM3, COM4 等)
- Linux: 通常是 /dev/ttyUSB0，需要权限：`sudo usermod -a -G dialout $USER`

**Q: 连接失败?**
- 检查串口号是否正确
- 检查设备地址是否正确
- 检查波特率等参数
- 确保设备已上电

**Q: 没有数据?**
- 检查 `enabled: true`
- 检查 `poll_interval` 设置
- 查看日志输出

## 下一步

- 📖 阅读完整文档: [readme.md](readme.md)
- 📚 查看API参考: [api_doc.md](api_doc.md)
- 🧪 运行测试: `python tests/test_config.py`
- 💡 查看更多示例: `examples/example_usage.py`

## 获取帮助

遇到问题？
1. 查看 [readme.md](readme.md) 的"常见问题"部分
2. 阅读 [INSTALL.md](INSTALL.md) 安装指南
3. 查看 [api_doc.md](api_doc.md) API文档

