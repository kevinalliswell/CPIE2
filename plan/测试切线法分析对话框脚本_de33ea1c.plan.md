---
name: 测试切线法分析对话框脚本
overview: 创建一个测试脚本，用于测试 tangent_analysis_dialog.py 对话框。脚本将接受可选的会话ID参数（默认15），从数据库查询温度数据，并显示对话框进行着火温度分析。
todos: []
---

# 测试切线法分析对话框脚本

## 目标

创建一个独立的测试脚本，用于测试 `TangentAnalysisDialog` 对话框功能。

## 实现方案

### 1. 脚本位置

- 文件路径: `tests/test_tangent_analysis_dialog.py`
- 参考现有的 `test_tangent_analysis_from_db.py` 的结构

### 2. 脚本功能

- 接受命令行参数 `--session` (可选，默认15)
- 初始化数据库连接 (`IgnitionDatabase`)
- 加载配置文件 (`experiment_config.yaml`)
- 创建并显示 `TangentAnalysisDialog` 对话框
- 支持GUI模式运行（使用 PySide6.QApplication）

### 3. 关键实现点

#### 3.1 数据库初始化

```python
from utils.path_manager import PathManager
from models.ignition_database import IgnitionDatabase

db_path = PathManager.get_data_path("ignition_experiment.db")
db = IgnitionDatabase(db_path)
```

#### 3.2 配置加载

```python
import yaml

with open('configs/experiment_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
# 提取着火点实验配置
ignition_config = config.get('ignition_experiment', {})
```

#### 3.3 对话框创建和显示

```python
from PySide6.QtWidgets import QApplication
from views.dialogs.tangent_analysis_dialog import TangentAnalysisDialog

app = QApplication(sys.argv)
dialog = TangentAnalysisDialog(
    session_id=session_id,
    db=db,
    config=ignition_config,
    parent=None
)
dialog.exec()
```

### 4. 脚本结构

- 导入必要的模块
- 命令行参数解析（argparse）
- 数据库连接和验证
- 配置加载
- 创建Qt应用和对话框
- 错误处理和日志输出

### 5. 验证会话数据

在显示对话框前，先验证会话ID是否存在数据：

- 调用 `db.get_session_temperature_data(session_id)` 检查数据
- 如果没有数据，输出错误信息并退出

### 6. 文件依赖

- `src/models/ignition_database.py` - 数据库操作
- `src/views/dialogs/tangent_analysis_dialog.py` - 对话框类
- `src/utils/path_manager.py` - 路径管理
- `configs/experiment_config.yaml` - 配置文件
- `data/ignition_experiment.db` - 数据库文件

## 注意事项

- 需要确保Qt应用在脚本中正确初始化
- 脚本应该能够独立运行，不依赖主应用程序
- 添加适当的错误处理和用户友好的提示信息
- 支持命令行参数以便灵活测试不同的会话ID