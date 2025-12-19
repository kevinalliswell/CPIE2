---
name: 图片另存为功能
overview: 为图片查看对话框添加另存为功能，默认保存到桌面，文件名包含实验编号、样品名称、测试序号和火焰长度信息
todos:
  - id: update-dialog-interface
    content: 修改 ImageViewerDialog 接口，添加 experiment_id 和 sample_name 可选参数
    status: completed
  - id: add-save-button
    content: 在按钮区域添加另存为按钮（在关闭按钮左侧）
    status: completed
    dependencies:
      - update-dialog-interface
  - id: implement-save-function
    content: 实现 save_image_as 方法，包含文件对话框、默认路径和文件名生成逻辑
    status: completed
    dependencies:
      - add-save-button
  - id: update-caller
    content: 更新 explosion_detail_card.py 中的调用代码，传入实验编号和样品名称
    status: completed
    dependencies:
      - implement-save-function
---

# 图片另存为功能实现计划

## 实现步骤

### 1. 修改 ImageViewerDialog 接口

- 在 `__init__` 方法中添加可选参数 `experiment_id` 和 `sample_name`
- 将这些参数存储为实例变量，用于生成默认文件名

### 2. 添加"另存为"按钮

在 [`src/views/dialogs/image_viewer_dialog.py`](src/views/dialogs/image_viewer_dialog.py) 的 `create_button_section` 方法中：

- 在"关闭"按钮左侧添加"另存为"按钮
- 设置与"关闭"按钮相同的样式风格
- 连接到新的 `save_image_as` 方法

### 3. 实现图片另存为功能

创建 `save_image_as` 方法：

- 使用 `QFileDialog.getSaveFileName` 弹出保存对话框
- 使用 `QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)` 获取桌面路径
- 生成默认文件名格式：`{实验编号}_{样品名称}_test_{测试序号}_flame_{火焰长度}mm.jpg`
- 示例：`EXP-20241201-001_粉尘样品A_test_1_flame_285.5mm.jpg`
- 使用 `shutil.copy` 复制原始图片到目标位置
- 添加错误处理和成功提示

### 4. 更新调用处

修改 [`src/views/ui_components/explosion_detail_card.py`](src/views/ui_components/explosion_detail_card.py) 的 `show_flame_image` 方法：

- 从 `self.experiment_data` 中获取实验编号和样品名称
- 传递给 ImageViewerDialog 构造函数

## 技术要点

- 导入必要的模块：`QFileDialog`, `QStandardPaths`, `shutil`, `QMessageBox`
- 文件名中的特殊字符处理（如果实验编号或样品名称包含非法字符）
- 保留原始图片格式（从 `image_path` 提取扩展名）
- 用户取消保存操作的处理