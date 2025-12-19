---
name: 用户登录和权限管理
overview: 实现系统登录界面和用户权限管理功能，包括在 models 模块中创建用户管理模块，创建登录对话框，并在历史查询页面中根据权限控制删除操作。
todos:
  - id: create_user_manager
    content: 创建 src/models/user_manager.py 模块，实现用户数据库管理、认证和权限检查功能
    status: pending
  - id: create_login_dialog
    content: 创建 src/views/dialogs/login_dialog.py 登录对话框，包含用户名密码输入和认证逻辑
    status: pending
  - id: modify_app_entry
    content: 修改 src/app.py，在显示 MainWindow 之前先显示登录对话框
    status: pending
  - id: modify_main_window
    content: 修改 src/views/main_window.py，保存当前登录用户信息
    status: pending
  - id: add_permission_check
    content: 修改 src/views/pages/history_query_page.py 的 delete_experiment 方法，添加权限检查
    status: pending
  - id: update_exports
    content: 更新 src/models/__init__.py 和 src/views/dialogs/__init__.py，添加新模块的导出
    status: pending
---

# 用户登录和权限管理实现计划

## 一、用户管理模块 (`src/models/user_manager.py`)

创建独立的用户管理模块，负责用户认证和权限管理。

### 1.1 数据库设计

- 创建 SQLite 数据库 `users.db` 存储用户信息
- 用户表结构：
  - `id`: 主键
  - `username`: 用户名（唯一）
  - `password`: 密码（简单存储，不加密）
  - `role`: 角色（'admin' 或 'experimenter'）
  - `created_at`: 创建时间

### 1.2 核心功能

- `__init__()`: 初始化数据库连接，创建表结构
- `initialize_default_users()`: 初始化默认账号
  - 管理员：username='admin', password='admin123', role='admin'
  - 实验员：username='experimenter', password='exp123', role='experimenter'
- `authenticate(username, password) -> User | None`: 用户认证，返回用户对象或 None
- `get_current_user() -> User | None`: 获取当前登录用户
- `set_current_user(user)`: 设置当前登录用户
- `has_permission(permission) -> bool`: 检查当前用户是否有指定权限
- `is_admin() -> bool`: 检查当前用户是否为管理员
- `is_experimenter() -> bool`: 检查当前用户是否为实验员

### 1.3 用户数据类

创建简单的 `User` 数据类（使用 dataclass 或 NamedTuple）：

- `username`: 用户名
- `role`: 角色
- `permissions`: 权限列表

## 二、登录对话框 (`src/views/dialogs/login_dialog.py`)

创建模态登录对话框，在 MainWindow 之前显示。

### 2.1 UI 设计

- 用户名输入框（QLineEdit）
- 密码输入框（QLineEdit，Password 模式）
- 登录按钮（QPushButton）
- 错误提示标签（QLabel，初始隐藏）
- 使用暗色主题样式，与应用整体风格一致

### 2.2 功能实现

- `__init__()`: 初始化 UI，设置窗口属性（模态、无边框或标准对话框）
- `authenticate()`: 调用 UserManager 进行认证
- `accept()`: 登录成功后关闭对话框
- `reject()`: 登录失败或取消时关闭对话框
- 支持 Enter 键快速登录

### 2.3 信号

- `login_successful(user)`: 登录成功信号，传递用户对象

## 三、修改应用入口 (`src/app.py`)

在显示 MainWindow 之前先显示登录对话框。

### 3.1 修改逻辑

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 显示登录对话框
    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)  # 用户取消登录，退出应用
    
    # 登录成功，显示主窗口
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

## 四、修改主窗口 (`src/views/main_window.py`)

保存当前登录用户信息，供其他页面使用。

### 4.1 添加属性

- `self.current_user`: 存储当前登录用户对象
- 在 `__init__()` 中从 UserManager 获取当前用户

### 4.2 可选：添加用户信息显示

- 在 TitleBar 或 StatusBar 中显示当前登录用户名和角色

## 五、修改历史查询页面 (`src/views/pages/history_query_page.py`)

在删除操作时检查用户权限。

### 5.1 修改 `delete_experiment()` 方法

- 在删除操作开始前检查当前用户权限
- 如果当前用户是实验员，显示提示并禁止删除
- 如果当前用户是管理员，执行原有删除逻辑

### 5.2 实现方式

```python
def delete_experiment(self):
    from src.models.user_manager import UserManager
    user_manager = UserManager()
    
    if not user_manager.is_admin():
        QMessageBox.warning(self, "权限不足", "实验员无权删除实验记录！")
        return
    
    # 原有的删除逻辑...
```

## 六、更新模块导出 (`src/models/__init__.py`)

添加 UserManager 到模块导出列表。

### 6.1 添加导入和导出

```python
from .user_manager import UserManager, User

__all__ = [
    # ... 现有导出
    'UserManager',
    'User'
]
```

## 七、更新对话框模块导出 (`src/views/dialogs/__init__.py`)

添加 LoginDialog 到导出列表。

## 八、其他需要权限控制的地方

根据需求，可能还需要在以下位置添加权限检查：

- 数据库初始化操作
- 配置修改操作
- 其他敏感操作

## 实现细节

### 密码存储

- 使用简单存储方式（不加密），符合"不要太复杂"的要求
- 密码以明文存储在数据库中

### 权限定义

- `admin`: 管理员，可以执行所有操作（初始化、删除、修改）
- `experimenter`: 实验员，只能查看数据，不能删除和修改

### 数据库位置

- 用户数据库文件：`data/users.db`（使用 PathManager 管理路径）

### 默认账号

- 管理员：用户名 `admin`，密码 `admin123`
- 实验员：用户名 `experimenter`，密码 `exp123`