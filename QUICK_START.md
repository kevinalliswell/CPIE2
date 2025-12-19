# CPIE 2.0 构建快速开始

## 🚀 三步完成构建

### 第一步: 安装依赖
```bash
# 激活虚拟环境
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# 安装标准依赖
pip install -r requirements.txt

# 安装本地包
python install_local_packages.py
```

### 第二步: 验证环境
```bash
# 验证所有包
python install_local_packages.py --verify

# 查看已安装的包
pip list | grep -E "(flamekit|modbus)"
```

### 第三步: 执行构建
```bash
# 正常构建
python build_release_optimized.py

# 或调试模式
python build_release_optimized.py --debug
```

---

## 📦 输出位置

构建完成后,文件位置:
- **应用程序**: `dist/CPIE/`
- **发布包**: `release/CPIE_*.zip`
- **日志**: 控制台输出

---

## 🔍 快速诊断

### 检查本地包
```bash
python -c "import flamekit; print('OK')"
python -c "import modbus_multi_device; print('OK')"
```

### 检查依赖完整性
```bash
python build_release_optimized.py --debug 2>&1 | grep "✗"
```

### 清理重新构建
```bash
# 清理构建文件
rm -rf build/ dist/ *.spec

# 重新构建
python build_release_optimized.py
```

---

## ⚠️ 常见错误速查

| 错误 | 解决方案 |
|------|---------|
| `ModuleNotFoundError: flamekit` | 运行 `python install_local_packages.py` |
| `构建验证失败` | 检查 `resources/` 和 `configs/` 目录 |
| `样式文件未加载` | 确认 `resources/styles/*.qss` 存在 |
| `图标不存在` | 确认 `resources/icons/cpie_logo_icon.ico` 存在 |

---

## 📋 构建前检查清单

- [ ] Python 3.10+ ✓
- [ ] 虚拟环境激活 ✓
- [ ] pip 已升级 ✓
- [ ] requirements_full.txt 安装完成 ✓
- [ ] 本地包安装完成 ✓
- [ ] configs/software.info 存在 ✓
- [ ] resources/ 目录完整 ✓

---

## 🎯 文件清单

优化后提供的文件:

1. **build_release_optimized.py** - 优化的构建脚本
2. **requirements_full.txt** - 完整依赖清单
3. **install_local_packages.py** - 本地包安装工具
4. **BUILD_GUIDE.md** - 详细构建指南
5. **QUICK_START.md** - 本文件

---

## 💡 使用技巧

### 开发模式安装
```bash
# 推荐! 修改源码后无需重装
pip install -e ./flame_package
pip install -e ./modbus_multi_device_package
```

### 增量构建
```bash
# 不清理缓存,构建更快
python build_release_optimized.py --no-clean
```

### 查看详细日志
```bash
python build_release_optimized.py --debug 2>&1 | tee build.log
```

---

## 📞 需要帮助?

1. 查看 **BUILD_GUIDE.md** 获取详细说明
2. 检查构建日志中的错误信息
3. 运行 `install_local_packages.py --verify` 验证环境

---

**祝构建成功! 🎉**
