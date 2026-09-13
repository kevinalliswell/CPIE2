# CPIE 2.0 构建快速开始

## 🚀 三步完成构建

### 第一步: 安装依赖
```bash
# 激活虚拟环境（Python 3.10+，推荐 3.11）
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# 安装标准依赖
pip install -r requirements.txt

# 安装本地包
pip install -e flame_package
pip install -e modbus_multi_device_package
```

### 第二步: 验证环境
```bash
# 验证本地包可以导入
python -c "import flamekit; print('flamekit OK')"
python -c "import modbus_multi_device; print('modbus_multi_device OK')"

# 查看已安装的包
pip list | grep -E "(flamekit|modbus)"
```

### 第三步: 执行构建
```bash
python build_release.py
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

### 清理重新构建
```bash
# 清理构建文件
rm -rf build/ dist/ *.spec

# 重新构建
python build_release.py
```

---

## ⚠️ 常见错误速查

| 错误 | 解决方案 |
|------|---------|
| `ModuleNotFoundError: flamekit` | 运行 `pip install -e flame_package` |
| `ModuleNotFoundError: modbus_multi_device` | 运行 `pip install -e modbus_multi_device_package` |
| `unexpected keyword argument 'device_id'` | pymodbus 版本过低，需要 `pip install "pymodbus>=3.10,<4"`（Python 3.10+） |
| `构建验证失败` | 检查 `resources/` 和 `configs/` 目录 |
| `样式文件未加载` | 确认 `resources/styles/*.qss` 存在 |
| `图标不存在` | 确认 `resources/icons/cpie_logo_icon.ico` 存在 |

---

## 📋 构建前检查清单

- [ ] Python 3.10+ ✓
- [ ] 虚拟环境激活 ✓
- [ ] pip 已升级 ✓
- [ ] requirements.txt 安装完成 ✓
- [ ] 本地包安装完成 ✓
- [ ] configs/software.info 存在 ✓
- [ ] resources/ 目录完整 ✓

---

## 🎯 文件清单

1. **build_release.py** - 构建脚本（唯一维护的构建入口）
2. **requirements.txt** - 依赖清单
3. **BUILD_GUIDE.md** - 详细构建指南
4. **QUICK_START.md** - 本文件

---

## 💡 使用技巧

### 开发模式安装
```bash
# 推荐! 修改源码后无需重装
pip install -e ./flame_package
pip install -e ./modbus_multi_device_package
```

### 运行测试
```bash
pytest tests/
```

---

## 📞 需要帮助?

1. 查看 **BUILD_GUIDE.md** 获取详细说明
2. 检查构建日志中的错误信息

---

**祝构建成功! 🎉**
