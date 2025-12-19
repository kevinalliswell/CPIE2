# src/app.py

import sys
import os

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow
# from views.dialogs.login_dialog import LoginDialog  # 已禁用登录功能
from utils.tools import Tools
from utils.single_instance import SingleInstance

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 单实例检测
    single_instance = SingleInstance("CPIE")
    
    if not single_instance.try_lock():
        # 应用程序已经在运行
        SingleInstance.show_already_running_message()
        sys.exit(0)
    
    try:
        # 应用暗色主题
        Tools.apply_stylesheet("dark")
        
        # 已禁用登录功能，直接显示主窗口
        # # 显示登录对话框
        # login_dialog = LoginDialog()
        # if login_dialog.exec() != QDialog.DialogCode.Accepted:
        #     sys.exit(0)  # 用户取消登录，退出应用
        
        # 显示主窗口
        window = MainWindow()
        window.show()
        exit_code = app.exec()
    
    finally:
        # 确保释放锁
        single_instance.unlock()
    
    sys.exit(exit_code)






