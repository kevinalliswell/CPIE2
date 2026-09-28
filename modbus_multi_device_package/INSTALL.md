# 安装指南

## 系统要求

- Python 3.10 或更高版本（pymodbus 3.10+ 不支持更低版本）
- Windows / Linux / macOS
- 串口设备（用于Modbus通信）

## 依赖包

- pyserial >= 3.5
- pymodbus >= 3.10.0, < 4.0.0（devices.py 使用 device_id= 参数）
- PyYAML >= 6.0

## 安装方法

### 方法 1: 从源码安装（推荐用于开发）

```bash
# 1. 进入项目目录
cd modbus_multi_device

# 2. 安装依赖
pip install -r requirements.txt

# 3. 以开发模式安装（可编辑安装）
pip install -e .

# 或者直接安装
pip install .
```

### 方法 2: 使用 pip 安装

如果包已发布到 PyPI：

```bash
pip install modbus_multi_device
```

### 方法 3: 手动安装依赖

如果你只想使用源码而不安装包：

```bash
# 安装依赖
pip install "pyserial>=3.5" "pymodbus>=3.10.0,<4.0.0" "pyyaml>=6.0"

# 然后将 modbus_multi_device 目录添加到 Python 路径
```

## 验证安装

安装完成后，运行以下命令验证：

```python
python -c "import modbus_multi_device; print(modbus_multi_device.__version__)"
```

应该输出版本号：`1.0.0`

## 运行示例

```bash
# 1. 配置设备参数
cd examples
cp example_config.yaml my_config.yaml
# 编辑 my_config.yaml，设置正确的串口和设备参数

# 2. 运行示例程序
python example_usage.py
```

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行单个测试文件
python tests/test_config.py

# 查看测试覆盖率
python -m pytest tests/ --cov=modbus_multi_device
```

## 开发环境设置

如果你想参与开发：

```bash
# 1. 克隆项目
git clone <repository_url>
cd modbus_multi_device

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装开发依赖
pip install -r requirements.txt
pip install -e .[dev]

# 4. 运行测试确保一切正常
python -m pytest tests/
```

## 常见问题

### 问题1: 找不到串口

**Windows:**
- 在设备管理器中查看串口号（如 COM3）
- 确保串口驱动已正确安装

**Linux:**
- 通常是 `/dev/ttyUSB0` 或 `/dev/ttyS0`
- 需要串口访问权限：`sudo usermod -a -G dialout $USER`
- 重新登录使权限生效

**macOS:**
- 通常是 `/dev/cu.usbserial-*`
- 使用 `ls /dev/cu.*` 查看可用设备

### 问题2: 权限错误

Linux/macOS 需要串口访问权限：

```bash
# 添加用户到 dialout 组
sudo usermod -a -G dialout $USER

# 或临时使用 sudo
sudo python your_script.py
```

### 问题3: ModuleNotFoundError

确保已正确安装包：

```bash
pip install -e .
```

或将项目路径添加到 PYTHONPATH：

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/modbus_multi_device"
```

### 问题4: 依赖冲突

建议使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## 卸载

```bash
pip uninstall modbus_multi_device
```

## 技术支持

如遇到安装问题，请：
1. 查看本文档的常见问题部分
2. 阅读 [README.md](readme.md)
3. 查看 [API文档](api_doc.md)
4. 提交 Issue（如果使用 Git）

