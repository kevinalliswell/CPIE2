# CPIE 2.0 - 煤粉着火点及爆炸性检测系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**CPIE-3000A 煤粉着火点及爆炸性检测系统**

一个基于 PySide6 的可燃性实验数据采集、分析与管理系统

[功能特性](#功能特性) • [快速开始](#快速开始) • [系统要求](#系统要求) • [安装](#安装) • [使用文档](#使用文档)

</div>

---

## 📖 项目简介

CPIE 2.0 是一套专业的煤粉可燃性实验系统，用于测试和分析煤粉的着火特性与爆炸性能。系统集成了数据采集、实时监控、火焰分析、报告生成等功能，为实验人员提供完整的实验流程管理解决方案。

### 主要应用场景
- 煤粉着火点温度测定
- 煤粉爆炸性能评估
- 燃烧特性分析
- 实验数据管理与报告生成

---

## ✨ 功能特性

### 🔬 实验模块
- **着火点检测实验**
  - 自动温度监测与记录
  - 多种着火点判定方法（切线法、固定温差法）
  - 实时温度曲线显示
  - 样品温度条件验证

- **爆炸性检测实验**
  - 多轮次实验管理
  - 实时压力曲线监测
  - 火焰图像自动捕获与分析
  - 爆炸性等级判定

### 📊 数据管理
- 实验数据本地存储（SQLite）
- 历史数据查询与筛选
- 实验数据导出（Excel、Word）
- 数据备份与恢复

### 🎥 图像分析
- 集成工业相机控制（迈德威视）
- 火焰面积自动计算
- 最大火焰图像识别
- 图像序列分析与存档

### 📈 可视化
- 实时数据曲线绘制（温度、压力）
- 多通道数据同步显示
- 副屏监控支持
- 实验过程回放

### 📝 报告生成
- 自动生成实验报告（Word格式）
- 包含完整实验数据与图表
- 自定义报告模板
- 批量导出功能

---

## 🖥️ 系统要求

### 硬件要求
- **处理器**: Intel i5 或更高
- **内存**: 8GB RAM（推荐 16GB）
- **存储**: 至少 2GB 可用空间
- **显示器**: 1920x1080 或更高分辨率
- **相机**: 支持迈德威视工业相机（可选）
- **通信接口**: RS485/Modbus（用于温度、压力传感器）

### 软件要求
- **操作系统**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python 版本**: 3.9 或更高
- **其他依赖**: 见 `requirements.txt`

---

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/kevinalliswell/CPIE2.git
cd CPIE2
```

### 2. 创建虚拟环境
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖
```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装标准依赖
pip install -r requirements.txt

# 安装本地包
pip install -e flame_package
pip install -e modbus_multi_device_package
```

### 4. 运行应用
```bash
python src/app.py
```

说明：入口脚本会补充项目根目录与 `src/` 到 `sys.path`，优先使用 `src.*` 导入，减少开发环境与打包环境下的路径差异。

---

## 📦 安装

### 方式一：从源码运行（开发）
详见上方[快速开始](#快速开始)部分

### 方式二：使用打包版本（生产）

#### 构建可执行文件
```bash
# 安装依赖后，运行构建脚本
python build_release.py

# 打包文件位于
# - dist/CPIE/ (应用程序目录)
# - release/ (压缩包)
```

构建脚本会检查以下本地包目录：
- `flame_package/`
- `modbus_multi_device_package/`

详细构建说明请参考 [BUILD_GUIDE.md](BUILD_GUIDE.md)

---

## 📚 使用文档

### 快速指南
- [快速开始指南](QUICK_START.md) - 3分钟快速上手
- [构建指南](BUILD_GUIDE.md) - 详细构建说明

### 技术文档
项目包含详细的技术文档，位于 `docs/` 目录：
- 实验流程文档
- 数据库结构说明
- 功能实现总结
- 优化与修复记录

### 配置文件
系统配置文件位于 `configs/` 目录：
- `experiment_config.yaml` - 实验参数配置
- `flame_analyzer_config.yaml` - 火焰分析参数
- `system.yaml` - 系统设置
- `presets.json` - 预设值

---

## 🗂️ 项目结构

```
CPIE2/
├── src/                        # 源代码目录
│   ├── app.py                  # 应用入口
│   ├── controllers/            # 业务逻辑控制器
│   ├── models/                 # 数据模型
│   ├── views/                  # 用户界面
│   │   ├── pages/              # 主要页面
│   │   ├── dialogs/            # 对话框
│   │   ├── widgets/            # 自定义控件
│   │   └── ui_components/      # UI组件
│   ├── services/               # 业务服务
│   │   ├── ignition/           # 着火点实验服务
│   │   └── explosion/          # 爆炸性实验服务
│   └── utils/                  # 工具函数
├── configs/                    # 配置文件
├── data/                       # 数据目录
│   ├── experiments/            # 实验数据
│   ├── flame_results/          # 火焰分析结果
│   └── backups/                # 数据备份
├── resources/                  # 资源文件
│   ├── icons/                  # 图标
│   ├── images/                 # 图片
│   ├── styles/                 # QSS样式
│   └── templates/              # 报告模板
├── docs/                       # 文档
├── tests/                      # 测试文件
├── flame_package/              # 火焰分析本地包
├── modbus_multi_device_package/ # Modbus通信本地包
├── requirements.txt            # 依赖清单
├── BUILD_GUIDE.md              # 构建指南
├── QUICK_START.md              # 快速开始
└── README.md                   # 本文件
```

---

## 🛠️ 技术栈

### 核心框架
- **PySide6** - Qt6 Python绑定，用于GUI开发
- **PyQtGraph** - 实时数据可视化
- **OpenCV** - 图像处理

### 数据处理
- **NumPy** - 数值计算
- **SciPy** - 科学计算（信号处理）
- **Matplotlib** - 数据绘图

### 硬件通信
- **PySerial** - 串口通信
- **PyModbus** - Modbus协议

### 文档生成
- **python-docx** - Word文档生成
- **ReportLab** - PDF生成

### 打包工具
- **PyInstaller** - 应用打包

---

## 🔧 开发

### 代码风格
项目遵循 PEP 8 编码规范

### 目录说明
- `src/controllers/` - MVC架构中的控制器层，处理业务逻辑
- `src/models/` - 数据模型和数据库操作
- `src/views/` - 界面层，与用户交互
- `src/services/` - 独立的业务服务模块
- `src/utils/` - 通用工具函数

### 本地包
项目包含两个自研本地包：
1. **flamekit** - 火焰分析工具包，封装迈德威视工业相机操作
2. **modbus_multi_device** - Modbus多设备通信包

安装方式：
```bash
pip install -e flame_package
pip install -e modbus_multi_device_package
```

---

## 🧪 测试

运行测试：
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_ignition_experiment_logic.py
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证

---

## 👥 作者

**Shi Jinpeng / Kevin**
- 单位: 北京科技大学 (USTB)
- Email: shijinpeng06@126.com
- GitHub: [@kevinalliswell](https://github.com/kevinalliswell)

---

## 🙏 致谢

- 北京科技大学 - 项目支持
- Qt/PySide6 社区
- 所有贡献者和测试人员

---

## 📞 技术支持

如遇到问题或需要帮助：
1. 查阅项目文档（`docs/` 目录）
2. 查看 [Issues](https://github.com/kevinalliswell/CPIE2/issues)
3. 联系作者：shijinpeng06@126.com

---

## 📈 更新日志

### v1.1.0
- 基于 `dev` 分支稳定化改进合并到正式发布线
- 修复启动、资源路径、构建脚本与版本说明不一致问题
- 降低硬件 SDK 导入副作用，支持无相机环境下的 smoke check 与关键测试
- 整理关键 pytest 用例并补充 Windows release 自动化流程

### v1.0.0
- 🎉 首次发布
- ✨ 完整的着火点和爆炸性实验功能
- 📊 数据管理和报告生成
- 🎥 火焰图像分析

---

## ⭐ Star History

如果这个项目对你有帮助，请给它一个 Star ⭐️

---

<div align="center">

**使用愉快！有问题欢迎反馈 😊**

[⬆ 回到顶部](#cpie-20---煤粉着火点及爆炸性检测系统)

</div>

