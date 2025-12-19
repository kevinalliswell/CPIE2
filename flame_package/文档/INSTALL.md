# FlameKit 安装指南

本文档提供 FlameKit 的详细安装步骤和配置说明。

## 目录

- [系统要求](#系统要求)
- [步骤1: 安装相机SDK](#步骤1-安装相机sdk)
- [步骤2: 安装Python依赖](#步骤2-安装python依赖)
- [步骤3: 安装FlameKit](#步骤3-安装flamekit)
- [步骤4: 验证安装](#步骤4-验证安装)
- [常见问题](#常见问题)

## 系统要求

### 硬件要求

- 迈德威视工业相机（USB 3.0 或 GigE 接口）
- USB 3.0 接口或千兆网卡
- 至少 2GB 可用内存

### 软件要求

- **操作系统**:
  - Windows 7/10/11 (64位)
  - Linux (Ubuntu 18.04+ 或其他主流发行版)
  
- **Python**: 3.7 或更高版本

- **相机SDK**: 迈德威视 MVSDK

## 步骤1: 安装相机SDK

### Windows 系统

1. **下载SDK**
   - 访问迈德威视官网: http://www.mindvision.com.cn/
   - 下载对应相机型号的 Windows SDK
   - 通常文件名为 `MVSDK_Setup_*.exe`

2. **安装SDK**
   - 运行安装程序
   - 按照向导完成安装
   - 默认安装路径: `C:\Program Files\MindVision\MVSDK\`

3. **配置环境变量**（通常自动完成）
   - SDK的 `bin` 目录应添加到系统 PATH
   - 或确保 DLL 文件在系统可访问路径

4. **验证安装**
   - 打开设备管理器，确认相机已识别
   - 运行相机厂商提供的测试程序验证

### Linux 系统

1. **下载SDK**
   - 从官网下载 Linux 版本的 SDK
   - 通常为 `.tar.gz` 压缩包

2. **安装库文件**
   ```bash
   # 解压SDK
   tar -xzf MVSDK_*.tar.gz
   cd MVSDK_*/
   
   # 复制库文件到系统路径
   sudo cp lib/*.so* /usr/local/lib/
   
   # 更新库缓存
   sudo ldconfig
   ```

3. **验证安装**
   ```bash
   # 检查库文件
   ldconfig -p | grep mvsdk
   ```

## 步骤2: 安装Python依赖

### 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 安装依赖包

```bash
# 进入项目目录
cd flame_package

# 安装依赖
pip install -r requirements.txt
```

**核心依赖**:
- `numpy>=1.24.0` - 数值计算
- `opencv-python>=4.8.0` - 图像处理

**可选依赖**:
- `PySide6>=6.5.0` - GUI界面（如需要）

## 步骤3: 安装FlameKit

### 开发模式安装（推荐）

```bash
# 在项目根目录执行
pip install -e .
```

开发模式的优势：
- 修改代码后立即生效，无需重新安装
- 适合开发和调试

### 标准安装

```bash
pip install .
```

### 验证安装

```python
# 测试导入
python -c "from flamekit import FlameKit, __version__; print(f'FlameKit {__version__}')"
```

应该输出: `FlameKit 0.1.0` (或当前版本)

## 步骤4: 验证安装

### 快速测试

1. **运行快速开始示例**:
   ```bash
   cd examples
   python quick_start.py
   ```

2. **检查相机连接**:
   - 确保相机已连接并上电
   - 检查USB/网线连接
   - 确认驱动已正确安装

3. **测试基本功能**:
   ```python
   from flamekit import FlameKit
   
   kit = FlameKit()
   if kit.initialize():
       print("✅ 相机初始化成功")
       kit.release()
   else:
       print("❌ 相机初始化失败")
   ```

## 常见问题

### Q1: 找不到相机设备

**可能原因**:
- 相机未连接或未上电
- USB/网线连接不良
- 驱动未正确安装

**解决方法**:
1. 检查硬件连接
2. 重新安装相机驱动
3. 在设备管理器中确认相机状态
4. 尝试更换USB端口或网线

### Q2: ModuleNotFoundError: No module named 'mvsdk'

**可能原因**:
- 相机SDK未安装
- SDK库文件不在系统路径

**解决方法**:
1. 确认已安装相机SDK
2. Windows: 检查 `C:\Program Files\MindVision\MVSDK\bin` 是否在PATH
3. Linux: 确认库文件在 `/usr/local/lib` 或已设置 `LD_LIBRARY_PATH`

### Q3: 导入flamekit失败

**可能原因**:
- 未正确安装包
- Python环境不正确

**解决方法**:
```bash
# 重新安装
pip uninstall flamekit
pip install -e .
```

### Q4: 权限错误（Linux）

**可能原因**:
- 相机设备权限不足

**解决方法**:
```bash
# 添加用户到video组
sudo usermod -a -G video $USER
# 重新登录生效
```

### Q5: 图像采集失败

**可能原因**:
- 相机被其他程序占用
- 参数设置不当

**解决方法**:
1. 关闭其他使用相机的程序
2. 检查 `config.json` 中的相机参数
3. 尝试降低分辨率或调整曝光时间

## 下一步

安装完成后，建议：

1. 阅读 [简明使用手册.md](简明使用手册.md) 快速上手
2. 运行 `examples/quick_start.py` 验证功能
3. 运行 `examples/calibration_demo.py` 进行参数标定
4. 查看 [USAGE.md](USAGE.md) 了解详细API

## 技术支持

如遇到安装问题：

1. 查看本文档的常见问题部分
2. 检查相机厂商文档
3. 确认系统要求是否满足
4. 查看错误日志获取详细信息

