# src/utils/single_instance.py
"""
单实例应用管理器
防止应用程序被重复启动
"""

import os
from PySide6.QtCore import QLockFile, QDir
from PySide6.QtWidgets import QMessageBox


class SingleInstance:
    """单实例管理器"""
    
    def __init__(self, app_name: str = "CPIE"):
        """
        初始化单实例管理器
        
        Args:
            app_name: 应用程序名称，用于生成唯一的锁文件名
        """
        self.app_name = app_name
        
        # 在临时目录创建锁文件
        temp_dir = QDir.tempPath()
        lock_file_path = os.path.join(temp_dir, f"{app_name}.lock")
        
        self.lock_file = QLockFile(lock_file_path)
        # 锁文件过期时间（毫秒），用于在程序异常崩溃后回收残留的锁文件。
        # 注意：QLockFile 不会周期性刷新锁文件的时间戳，过期时间是一个“绝对上限”，
        # 而非心跳间隔。它本身已能通过记录的 PID 自动识别并清理“持有进程已退出”的锁，
        # 因此这里设置一个较大的值（8 小时），避免长时间运行的实验过程中
        # 锁被误判为过期，从而允许第二个实例启动并同时写入同一数据库。
        self.lock_file.setStaleLockTime(8 * 60 * 60 * 1000)
        
        self._is_locked = False
    
    def try_lock(self) -> bool:
        """
        尝试获取锁
        
        Returns:
            bool: 成功获取锁返回True，否则返回False
        """
        if self._is_locked:
            return True
        
        # 尝试锁定（超时时间：100毫秒）
        self._is_locked = self.lock_file.tryLock(100)
        return self._is_locked
    
    def unlock(self):
        """释放锁"""
        if self._is_locked:
            self.lock_file.unlock()
            self._is_locked = False
    
    def is_locked(self) -> bool:
        """检查是否已锁定"""
        return self._is_locked
    
    def get_lock_file_path(self) -> str:
        """获取锁文件路径"""
        return self.lock_file.fileName()
    
    @staticmethod
    def show_already_running_message():
        """显示应用程序已运行的提示消息"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("提示")
        msg_box.setText("系统已经在运行中，请勿重复启动！")
        # msg_box.setInformativeText(
        #     "应用程序只允许运行一个实例。\n\n"
        #     "如果您看不到已运行的窗口，请检查任务栏或系统托盘。"
        # )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def __del__(self):
        """析构函数，确保释放锁"""
        self.unlock()

