#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理模块
用于用户认证和权限管理
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from utils.logger import get_logger
from utils.path_manager import PathManager


@dataclass
class User:
    """用户数据类"""
    username: str
    role: str  # 'admin' 或 'experimenter'
    
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.role == 'admin'
    
    def is_experimenter(self) -> bool:
        """检查是否为实验员"""
        return self.role == 'experimenter'


class UserManager:
    """用户管理类，负责用户认证和权限管理"""
    
    # 单例模式：当前登录用户
    _current_user: Optional[User] = None
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化用户管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        self.logger = get_logger(__name__)
        
        if db_path is None:
            db_path = PathManager.get_data_path('users.db')
        
        # 确保目录存在
        PathManager.ensure_file_directory_exists(db_path)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
        self._initialize_default_users()
    
    def _connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            # 启用外键支持
            self.cursor.execute("PRAGMA foreign_keys = ON")
            self.logger.info(f"✓ 用户数据库连接成功: {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 用户数据库连接失败: {e}")
            raise
    
    def _create_tables(self):
        """创建用户表"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'experimenter')),
                    created_at TEXT NOT NULL
                )
            """)
            self.conn.commit()
            self.logger.info("✓ 用户表创建成功")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 创建用户表失败: {e}")
            raise
    
    def _initialize_default_users(self):
        """初始化默认用户账号"""
        try:
            # 检查是否已有用户
            self.cursor.execute("SELECT COUNT(*) FROM users")
            count = self.cursor.fetchone()[0]
            
            if count == 0:
                # 创建默认管理员账号
                admin_created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.cursor.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (?, ?, ?, ?)
                """, ('admin', 'admin123', 'admin', admin_created_at))
                
                # 创建默认实验员账号
                exp_created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.cursor.execute("""
                    INSERT INTO users (username, password, role, created_at)
                    VALUES (?, ?, ?, ?)
                """, ('experimenter', 'exp123', 'experimenter', exp_created_at))
                
                self.conn.commit()
                self.logger.info("✓ 默认用户账号初始化成功")
                self.logger.info("  - 管理员: admin / admin123")
                self.logger.info("  - 实验员: experimenter / exp123")
            else:
                self.logger.debug("用户表已存在数据，跳过默认用户初始化")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 初始化默认用户失败: {e}")
            self.conn.rollback()
            raise
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            如果认证成功返回User对象，否则返回None
        """
        try:
            self.cursor.execute("""
                SELECT username, role FROM users
                WHERE username = ? AND password = ?
            """, (username, password))
            
            result = self.cursor.fetchone()
            
            if result:
                user = User(username=result[0], role=result[1])
                self.logger.info(f"✓ 用户认证成功: {username} ({result[1]})")
                return user
            else:
                self.logger.warning(f"✗ 用户认证失败: {username}")
                return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 用户认证出错: {e}")
            return None
    
    def get_current_user(self) -> Optional[User]:
        """
        获取当前登录用户
        
        Returns:
            当前登录的User对象，如果未登录则返回None
        """
        return UserManager._current_user
    
    def set_current_user(self, user: Optional[User]):
        """
        设置当前登录用户
        
        Args:
            user: User对象，如果为None则清除当前用户
        """
        UserManager._current_user = user
        if user:
            self.logger.info(f"✓ 设置当前用户: {user.username} ({user.role})")
        else:
            self.logger.info("✓ 清除当前用户")
    
    def has_permission(self, permission: str) -> bool:
        """
        检查当前用户是否有指定权限
        
        Args:
            permission: 权限名称（如 'delete', 'modify', 'init'）
            
        Returns:
            如果有权限返回True，否则返回False
        """
        user = self.get_current_user()
        if not user:
            return False
        
        # 管理员拥有所有权限
        if user.is_admin():
            return True
        
        # 实验员只有查看权限
        if user.is_experimenter():
            return False
        
        return False
    
    def is_admin(self) -> bool:
        """
        检查当前用户是否为管理员
        
        Returns:
            如果是管理员返回True，否则返回False
        """
        user = self.get_current_user()
        return user is not None and user.is_admin()
    
    def is_experimenter(self) -> bool:
        """
        检查当前用户是否为实验员
        
        Returns:
            如果是实验员返回True，否则返回False
        """
        user = self.get_current_user()
        return user is not None and user.is_experimenter()
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        修改用户密码
        
        Args:
            username: 用户名
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            如果修改成功返回True，否则返回False
        """
        try:
            # 先验证旧密码
            self.cursor.execute("""
                SELECT id FROM users
                WHERE username = ? AND password = ?
            """, (username, old_password))
            
            result = self.cursor.fetchone()
            
            if not result:
                self.logger.warning(f"✗ 修改密码失败: 旧密码不正确 ({username})")
                return False
            
            # 更新密码
            self.cursor.execute("""
                UPDATE users
                SET password = ?
                WHERE username = ? AND password = ?
            """, (new_password, username, old_password))
            
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 密码修改成功: {username}")
                return True
            else:
                self.logger.warning(f"✗ 密码修改失败: 未找到匹配的用户 ({username})")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 修改密码出错: {e}")
            self.conn.rollback()
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("✓ 用户数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    """测试用户管理模块"""
    # 测试用户管理器
    user_manager = UserManager()
    
    # 测试认证
    print("\n=== 测试用户认证 ===")
    admin_user = user_manager.authenticate('admin', 'admin123')
    print(f"管理员认证: {admin_user}")
    
    exp_user = user_manager.authenticate('experimenter', 'exp123')
    print(f"实验员认证: {exp_user}")
    
    wrong_user = user_manager.authenticate('admin', 'wrong_password')
    print(f"错误密码认证: {wrong_user}")
    
    # 测试权限
    print("\n=== 测试权限检查 ===")
    user_manager.set_current_user(admin_user)
    print(f"当前用户是管理员: {user_manager.is_admin()}")
    print(f"当前用户有删除权限: {user_manager.has_permission('delete')}")
    
    user_manager.set_current_user(exp_user)
    print(f"当前用户是实验员: {user_manager.is_experimenter()}")
    print(f"当前用户有删除权限: {user_manager.has_permission('delete')}")
    
    user_manager.close()
    print("\n测试完成")
