"""
修改密码对话框
用于在登录界面修改用户密码
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from models.user_manager import UserManager


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""
    
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.user_manager = UserManager()
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("修改密码")
        self.setModal(True)
        self.setFixedSize(450, 350)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # # 标题
        # title_label = QLabel("修改密码")
        # title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # title_label.setStyleSheet("""
        #     QLabel {
        #         font-size: 24px;
        #         font-weight: bold;
        #         color: #00d9ff;
        #         margin-bottom: 10px;
        #     }
        # """)
        # layout.addWidget(title_label)
        
        # 用户名显示
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
        
        username_display = QLineEdit(self.username)
        username_display.setReadOnly(True)
        username_display.setFixedHeight(48)
        username_display.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 0px 16px;
                color: rgba(255, 255, 255, 0.6);
                font-size: 15px;
            }
        """)
        username_layout.addWidget(username_display)
        layout.addLayout(username_layout)
        
        # 旧密码输入
        old_password_layout = QVBoxLayout()
        old_password_layout.setSpacing(8)
        old_password_label = QLabel("当前密码")
        old_password_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                padding-left: 2px;
            }
        """)
        old_password_layout.addWidget(old_password_label)
        
        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("请输入当前密码")
        self.old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_password_input.setFixedHeight(48)
        self.old_password_input.setStyleSheet("""
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
        old_password_layout.addWidget(self.old_password_input)
        layout.addLayout(old_password_layout)
        
        # 新密码输入
        new_password_layout = QVBoxLayout()
        new_password_layout.setSpacing(8)
        new_password_label = QLabel("新密码")
        new_password_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                padding-left: 2px;
            }
        """)
        new_password_layout.addWidget(new_password_label)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setFixedHeight(48)
        self.new_password_input.setStyleSheet("""
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
        new_password_layout.addWidget(self.new_password_input)
        layout.addLayout(new_password_layout)
        
        # 确认新密码输入
        confirm_password_layout = QVBoxLayout()
        confirm_password_layout.setSpacing(8)
        confirm_password_label = QLabel("确认新密码")
        confirm_password_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                padding-left: 2px;
            }
        """)
        confirm_password_layout.addWidget(confirm_password_label)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请再次输入新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setFixedHeight(48)
        self.confirm_password_input.setStyleSheet("""
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
        confirm_password_layout.addWidget(self.confirm_password_input)
        layout.addLayout(confirm_password_layout)
        
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
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 确定按钮
        self.confirm_button = QPushButton("确定")
        self.confirm_button.setFixedHeight(45)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #ffffff;
                border-radius: 8px;
                font-size: 15px;
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
        self.confirm_button.clicked.connect(self.on_confirm_clicked)
        button_layout.addWidget(self.confirm_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedHeight(45)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: #ffffff;
                border-radius: 8px;
                font-size: 15px;
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
        
        layout.addLayout(button_layout)
        
        # 对话框样式
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(26, 35, 50, 0.95),
                    stop: 1 rgba(15, 20, 25, 0.95)
                );
            }
        """)
        
        # 设置焦点到旧密码输入框
        self.old_password_input.setFocus()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Enter 键确认
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self.on_confirm_clicked)
        
        # Escape 键取消
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.reject)
    
    def on_confirm_clicked(self):
        """处理确认按钮点击"""
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # 验证输入
        if not old_password:
            self.show_error("请输入当前密码")
            self.old_password_input.setFocus()
            return
        
        if not new_password:
            self.show_error("请输入新密码")
            self.new_password_input.setFocus()
            return
        
        if len(new_password) < 3:
            self.show_error("新密码长度至少为3个字符")
            self.new_password_input.setFocus()
            return
        
        if new_password != confirm_password:
            self.show_error("两次输入的新密码不一致")
            self.confirm_password_input.setFocus()
            return
        
        if old_password == new_password:
            self.show_error("新密码不能与当前密码相同")
            self.new_password_input.setFocus()
            return
        
        # 尝试修改密码
        success = self.user_manager.change_password(
            self.username, 
            old_password, 
            new_password
        )
        
        if success:
            QMessageBox.information(
                self, 
                "修改成功", 
                "密码修改成功！\n请使用新密码登录。"
            )
            self.accept()
        else:
            self.show_error("当前密码错误，请重新输入")
            self.old_password_input.clear()
            self.old_password_input.setFocus()
    
    def show_error(self, message: str):
        """显示错误信息"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)
    
    def hide_error(self):
        """隐藏错误信息"""
        self.error_label.setVisible(False)
