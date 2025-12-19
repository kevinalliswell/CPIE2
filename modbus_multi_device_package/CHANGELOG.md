# 更新日志

本文档记录了所有重要的项目变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2024-11-26

### 新增
- 初始版本发布
- 支持4种常用Modbus设备类型：
  - 智能数显压力表 (PressureSensorDevice)
  - DAM-3944A 继电器模块 (RelayControllerDevice)
  - DAM-3138 温度采集模块 (TemperatureSensorDevice)
  - 宇电AI系列温控仪表 (YudianControllerDevice)
- 多设备统一管理器 (ModbusDeviceManager)
- 独立线程数据轮询机制 (DataPoller)
- 优先级控制命令执行器 (ControlExecutor)
- YAML配置文件支持 (ConfigLoader)
- 完整的回调机制（数据回调、控制回调、错误回调）
- 历史数据自动保存和查询
- 完善的日志系统
- 配置验证功能
- 详细的API文档
- 使用示例和测试用例

### 功能特性
- ✅ 多设备并发管理
- ✅ 自动轮询数据采集
- ✅ 控制命令优先级队列
- ✅ 灵活的配置系统
- ✅ 易于扩展的设备架构
- ✅ 线程安全操作
- ✅ 完整的错误处理

### 文档
- README.md - 项目说明和快速开始指南
- api_doc.md - 完整的API参考文档
- LICENSE - MIT许可证
- examples/example_usage.py - 完整的使用示例
- examples/example_config.yaml - 配置文件示例

### 测试
- tests/test_config.py - 配置加载器单元测试

---

## [未来计划]

### 待添加功能
- [ ] 更多设备类型支持
- [ ] Web界面监控
- [ ] 数据库存储支持
- [ ] MQTT/HTTP API接口
- [ ] 设备自动发现
- [ ] 更多的单元测试覆盖
- [ ] 性能优化和基准测试
- [ ] 国际化支持

### 改进计划
- [ ] 增强错误处理和恢复机制
- [ ] 添加设备状态监控
- [ ] 支持异步操作
- [ ] 优化内存使用
- [ ] 改进日志系统

---

## 版本说明

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的API变更
- **次版本号**：向后兼容的功能新增
- **修订号**：向后兼容的问题修正

