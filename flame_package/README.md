# FlameKit 🔥

[![Release](https://img.shields.io/github/v/release/kevinalliswell/flame-package)](https://github.com/kevinalliswell/flame-package/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

**FlameKit** 是一个基于迈德威视（MindVision）工业相机的火焰长度检测与图像分析工具包。它为燃烧实验研究提供了高速采集、实时分析、标定管理和结果回放的完整解决方案。

---

## ✨ 主要功能

- 🚀 **高速采集**：支持 30-300+ FPS 的图像采集（取决于相机型号及分辨率）。
- 🧠 **火焰分析**：内置火焰分割算法，自动测量火焰长度、宽度和面积。
- 📏 **标定管理**：支持像素到毫米的物理标定，并根据分辨率自动管理标定参数。
- ⚡ **内存缓冲**：针对高速采集进行了深度优化，采用内存缓冲机制，确保在高帧率下不会丢帧。
- 🔄 **慢动作回放**：支持采集后的图像序列按指定速率慢动作回放。
- 🛠️ **简洁 API**：极简的 API 设计，只需几行代码即可完成完整的实验流程。

---

## 📦 安装

### 1. 安装相机 SDK
在使用本工具包之前，请确保已安装 **迈德威视 (MindVision) 驱动及 SDK**。
- **Windows**: 从 [迈德威视官网](http://www.mindvision.com.cn/) 下载并安装 MVSDK。
- **Linux**: 安装 `libMVSDK.so` 到系统库路径。

### 2. 安装 Python 包
```bash
git clone https://github.com/kevinalliswell/flame-package.git
cd flame-package
pip install -r requirements.txt
pip install -e .
```

---

## 🚀 快速开始

以下是一个最简单的火焰分析工作流：

```python
from flamekit import FlameKit

# 1. 初始化
kit = FlameKit()

try:
    if kit.initialize():
        # 2. 预览相机 (3秒)
        kit.preview(seconds=3.0)
        
        # 3. 高速采集 1 秒
        print("开始采集...")
        images, count = kit.capture_one_second()
        print(f"采集完成，共 {count} 帧")
        
        # 4. 火焰长度分析
        result, max_image_path = kit.analyze()
        print(f"最大火焰长度: {result['max_length_mm']:.2f} mm")
        
        # 5. 播放分析结果
        kit.play_analyzed(speed=0.5)
        
        # 6. 保存最大火焰图
        kit.save_max_result()
finally:
    # 7. 释放资源
    kit.release()
```

---

## 📖 文档导航

- [安装指南](文档/INSTALL.md) - 详细的 SDK 配置步骤。
- [使用手册](文档/简明使用手册.md) - 核心功能使用方法。
- [API 参考](文档/USAGE.md) - 详细的类与方法说明。
- [示例代码](examples/) - 包含标定、参数调节等多个示例程序。

---

## 📂 目录结构

```text
flame-package/
├── flamekit/              # 核心包内容
│   ├── analyzer.py       # 图像分析算法
│   ├── camera.py         # 相机驱动封装 (支持内存缓冲)
│   ├── core.py           # 顶层 API (FlameKit 类)
│   └── mvsdk.py          # 迈德威视 SDK Python 绑定
├── examples/              # 示例程序
├── 文档/                  # 详细 Markdown 文档
├── CHANGELOG.md           # 更新日志
└── requirements.txt       # 依赖列表
```

---

## 📄 许可证

本项目基于 **MIT License**。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献与支持

作者: **Kevin @ USTB**
如有任何疑问、建议或 Bug 反馈，请提交 [Issue](https://github.com/kevinalliswell/flame-package/issues)。
