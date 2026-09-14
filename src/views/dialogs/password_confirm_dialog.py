"""
密码确认对话框
用于删除操作前的密码验证
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, 
    QLineEdit, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from utils.password_manager import PasswordManager


class PasswordConfirmDialog(QDialog):
    """密码确认对话框（口令由 PasswordManager 管理，可通过 Ctrl+Alt+P 修改）"""

    def __init__(self, parent=None, password_manager: PasswordManager = None):
        super().__init__(parent)
        self.password_manager = password_manager or PasswordManager()
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("密码确认")
        self.setModal(True)
        self.setFixedSize(400, 250)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 提示信息
        info_label = QLabel("此操作需要密码确认")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(info_label)
        
        # 密码输入
        password_layout = QVBoxLayout()
        password_layout.setSpacing(8)
        password_label = QLabel("请输入密码")
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
        layout.addLayout(password_layout)
        
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
        
        # 确认按钮
        self.confirm_button = QPushButton("确认")
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
        
        # 设置焦点到密码输入框
        self.password_input.setFocus()
    
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
        password = self.password_input.text()
        
        # 验证输入
        if not password:
            self.show_error("请输入密码")
            return
        
        # 验证密码
        if self.password_manager.verify_password(password):
            self.hide_error()
            self.accept()
        else:
            self.show_error("密码错误，请重新输入")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def show_error(self, message: str):
        """显示错误信息"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)
    
    def hide_error(self):
        """隐藏错误信息"""
        self.error_label.setVisible(False)


if __name__ == "__main__":
    """测试密码确认对话框"""
    import sys
    from PySide6.QtWidgets import QApplication, QMessageBox
    
    app = QApplication(sys.argv)
    
    dialog = PasswordConfirmDialog()
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        QMessageBox.information(None, "成功", "密码验证成功！")
    else:
        QMessageBox.information(None, "取消", "操作已取消")
    
    sys.exit(0)

