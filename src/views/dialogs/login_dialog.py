"""
登录对话框
用于用户登录认证
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox, QComboBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QPainter, QBrush, QFont
from models.user_manager import UserManager, User
from utils.path_manager import PathManager
from .change_password_dialog import ChangePasswordDialog


class BackgroundWidget(QWidget):
    """背景图片Widget"""
    
    def __init__(self, image_path=None, parent=None):
        super().__init__(parent)
        self.background_pixmap = None
        if image_path and os.path.exists(image_path):
            self.background_pixmap = QPixmap(image_path)
    
    def paintEvent(self, event):
        """绘制背景图片"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        if self.background_pixmap and not self.background_pixmap.isNull():
            # 计算缩放后的图片尺寸，保持宽高比并填充整个区域
            pixmap_scaled = self.background_pixmap.scaled(
                self.width(),
                self.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 居中绘制
            x = (self.width() - pixmap_scaled.width()) // 2
            y = (self.height() - pixmap_scaled.height()) // 2
            painter.drawPixmap(x, y, pixmap_scaled)
        
        # 添加半透明遮罩层，使图片更柔和，文字更清晰
        painter.setOpacity(0.4)
        painter.fillRect(self.rect(), QBrush(Qt.GlobalColor.black))


class LoginDialog(QDialog):
    """登录对话框"""
    
    # 登录成功信号
    login_successful = Signal(User)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.user_manager = UserManager()
        self.current_user = None
        
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("系统登录")
        self.setModal(True)
        self.setFixedSize(800, 600)
        
        # 主布局 - 使用水平布局，左侧背景，右侧登录表单
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧背景区域 - 使用自定义背景widget
        bg_image_path = PathManager.get_resources_path("images/ustb.png")
        left_widget = BackgroundWidget(bg_image_path)
        left_widget.setObjectName("backgroundWidget")
        
        # 右侧登录表单区域
        form_widget = QWidget()
        form_widget.setObjectName("formWidget")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(25)
        form_layout.setContentsMargins(60, 80, 60, 80)
        
        # 标题区域
        title_container = QVBoxLayout()
        title_label = QLabel("CPIE 系统登录")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
                letter-spacing: 2px;
            }
        """)
        title_container.addWidget(title_label)
        
        subtitle_label = QLabel("欢迎使用实验管理系统")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                margin-top: 5px;
            }
        """)
        title_container.addWidget(subtitle_label)
        form_layout.addLayout(title_container)
        
        form_layout.addStretch()
        
        # 用户名选择
        username_layout = QVBoxLayout()
        username_layout.setSpacing(8)
        username_label = QLabel("用户名")
        username_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                padding-left: 2px;
            }
        """)
        username_layout.addWidget(username_label)
        
        self.username_input = QComboBox()
        self.username_input.addItem("管理员", "admin")
        self.username_input.addItem("实验员", "experimenter")
        self.username_input.setCurrentIndex(0)  # 默认选中管理员
        self.username_input.setFixedHeight(48)
        self.username_input.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 0px 16px;
                color: #ffffff;
                font-size: 15px;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(0, 217, 255, 0.6);
            }
            QComboBox:focus {
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid #00d9ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid rgba(255, 255, 255, 0.8);
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: rgba(42, 42, 62, 0.95);
                border: 2px solid rgba(0, 217, 255, 0.5);
                border-radius: 8px;
                selection-background-color: rgba(0, 217, 255, 0.3);
                selection-color: #00d9ff;
                color: #fff;
                padding: 4px;
            }
        """)
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)
        
        # 密码输入
        password_layout = QVBoxLayout()
        password_layout.setSpacing(8)
        password_label = QLabel("密码")
        password_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                padding-left: 2px;
            }
        """)
        password_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(48)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 0px 16px;
                color: #ffffff;
                font-size: 15px;
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid #00d9ff;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        password_layout.addWidget(self.password_input)
        form_layout.addLayout(password_layout)
        
        # 错误提示标签
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 13px;
                min-height: 20px;
                padding: 4px;
                background: rgba(255, 107, 107, 0.1);
                border-radius: 4px;
            }
        """)
        self.error_label.setVisible(False)
        form_layout.addWidget(self.error_label)
        
        # 修改密码链接
        change_password_layout = QHBoxLayout()
        change_password_layout.setContentsMargins(0, 0, 0, 0)
        change_password_link = QLabel('<a href="#" style="color: rgba(0, 217, 255, 0.8); text-decoration: none; font-size: 13px;">修改密码</a>')
        change_password_link.setAlignment(Qt.AlignmentFlag.AlignRight)
        change_password_link.setOpenExternalLinks(False)
        change_password_link.linkActivated.connect(self.on_change_password_clicked)
        change_password_link.setStyleSheet("""
            QLabel {
                background: transparent;
            }
            QLabel:hover {
                background: transparent;
            }
        """)
        change_password_layout.addWidget(change_password_link)
        form_layout.addLayout(change_password_layout)
        
        form_layout.addStretch()
        
        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.setFixedHeight(50)
        self.login_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #ffffff;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00e8ff,
                    stop: 1 #00a8d0
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #0096b8,
                    stop: 1 #007a96
                );
            }
        """)
        self.login_button.clicked.connect(self.on_login_clicked)
        button_layout.addWidget(self.login_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedHeight(50)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: #ffffff;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.05);
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        form_layout.addLayout(button_layout)
        
        # 添加左右两个区域到主布局
        main_layout.addWidget(left_widget, 1)  # 左侧背景占1份
        main_layout.addWidget(form_widget, 1)   # 右侧表单占1份
        
        # 对话框样式
        self.setStyleSheet("""
            QDialog {
                background: #0f1419;
            }
            QWidget#backgroundWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1a2332,
                    stop: 1 #0f1419
                );
            }
            QWidget#formWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(26, 35, 50, 0.95),
                    stop: 1 rgba(15, 20, 25, 0.95)
                );
                border-left: 1px solid rgba(0, 217, 255, 0.2);
            }
        """)
        
        # 设置焦点到密码输入框
        self.password_input.setFocus()
    
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Enter 键登录
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self.on_login_clicked)
        
        # Escape 键取消
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.reject)
    
    def on_login_clicked(self):
        """处理登录按钮点击"""
        # 从 QComboBox 获取选中的用户名
        username = self.username_input.currentData()
        if not username:
            username = self.username_input.currentText().split('(')[-1].split(')')[0].strip()
        password = self.password_input.text()
        
        # 验证输入
        if not username:
            self.show_error("请选择用户名")
            return
        
        if not password:
            self.show_error("请输入密码")
            return
        
        # 尝试认证
        user = self.user_manager.authenticate(username, password)
        
        if user:
            # 登录成功
            self.current_user = user
            self.user_manager.set_current_user(user)
            self.hide_error()
            self.accept()
            self.login_successful.emit(user)
        else:
            # 登录失败
            self.show_error("用户名或密码错误")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def show_error(self, message: str):
        """显示错误信息"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)
    
    def hide_error(self):
        """隐藏错误信息"""
        self.error_label.setVisible(False)
    
    def get_user(self) -> User:
        """获取登录的用户"""
        return self.current_user
    
    def on_change_password_clicked(self):
        """处理修改密码链接点击"""
        # 获取当前选中的用户名
        username = self.username_input.currentData()
        if not username:
            username = self.username_input.currentText()
        
        # 显示修改密码对话框
        change_password_dialog = ChangePasswordDialog(username, self)
        change_password_dialog.exec()


if __name__ == "__main__":
    """测试登录对话框"""
    import sys
    from PySide6.QtWidgets import QApplication
    from utils.tools import Tools
    
    app = QApplication(sys.argv)
    Tools.apply_stylesheet("dark")
    
    dialog = LoginDialog()
    
    def on_login_success(user):
        print(f"登录成功: {user.username} ({user.role})")
        QMessageBox.information(dialog, "登录成功", 
                              f"欢迎，{user.username}！\n角色: {user.role}")
    
    dialog.login_successful.connect(on_login_success)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("对话框已接受")
    else:
        print("对话框已取消")
    
    sys.exit(0)
