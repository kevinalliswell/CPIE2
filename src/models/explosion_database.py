#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆炸性实验数据库模块
用于存储和管理实验火焰长度、分析结果数据路径等
"""

import sqlite3
import os
import yaml
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from utils.logger import get_logger
from utils.path_manager import PathManager


class ExplosionDatabase:
    """爆炸性实验数据库管理类"""
    
    # 字段映射：数据库字段名 -> 中文表头
    COLUMN_HEADERS = {
        'round_number': '轮次',
        'flame_length': '火焰长度(mm)',
        'max_flame_image_path': '最大火焰图片路径',
        'avg_flame_length': '平均火焰长度(mm)',
        'explosion_level': '爆炸性等级'
    }
    
    # 爆炸性等级分类标准（将从配置文件动态加载）
    # EXPLOSION_LEVELS 现在是实例变量，在 __init__ 中通过 _load_explosion_thresholds 加载
    
    # SQL注入防护：order_by字段白名单
    VALID_ORDER_BY_FIELDS = {
        'get_all_experiment_sessions': ['id', 'start_time', 'end_time', 'experiment_name', 'status', 'experiment_id'],
        'get_all_results': ['id', 'timestamp', 'avg_flame_length', 'explosion_level', 'total_rounds']
    }
    
    def _load_explosion_thresholds(self, config_path: str = None):
        """
        从配置文件加载爆炸性阈值
        
        Args:
            config_path: 配置文件路径
        """
        # 默认配置文件路径
        if config_path is None:
            config_path = os.path.join("configs", "experiment_config.yaml")
        
        try:
            # 读取配置文件
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                # 提取爆炸性阈值
                thresholds = config.get('explosion_experiment', {}).get('explosion-thresholds', {})
                
                no_explosion = thresholds.get('no-explosion', 25.0)
                weak_explosion = thresholds.get('weak-explosion', 400.0)
                strong_explosion = thresholds.get('strong-explosion', 800.0)
                
                # 动态生成爆炸性等级配置
                self.EXPLOSION_LEVELS = {
                    'none': {'name': '无爆炸性', 'min': 0, 'max': no_explosion},
                    'weak': {'name': '弱爆炸性', 'min': no_explosion, 'max': weak_explosion},
                    'strong': {'name': '强爆炸性', 'min': weak_explosion, 'max': strong_explosion},
                    'super': {'name': '超强爆炸性', 'min': strong_explosion, 'max': float('inf')}
                }
                
                if hasattr(self, 'logger'):
                    self.logger.info(f"✓ 已从配置文件加载爆炸性阈值: 无爆炸<{no_explosion}, 弱爆炸<{weak_explosion}, 强爆炸<{strong_explosion}")
            else:
                # 使用默认值（向后兼容）
                self.EXPLOSION_LEVELS = {
                    'none': {'name': '无爆炸性', 'min': 0, 'max': 25.0},
                    'weak': {'name': '弱爆炸性', 'min': 25.0, 'max': 400.0},
                    'strong': {'name': '强爆炸性', 'min': 400.0, 'max': 800.0},
                    'super': {'name': '超强爆炸性', 'min': 800.0, 'max': float('inf')}
                }
                if hasattr(self, 'logger'):
                    self.logger.warning(f"⚠ 配置文件不存在: {config_path}，使用默认阈值")
                    
        except Exception as e:
            # 出错时使用默认值
            self.EXPLOSION_LEVELS = {
                'none': {'name': '无爆炸性', 'min': 0, 'max': 25.0},
                'weak': {'name': '弱爆炸性', 'min': 25.0, 'max': 400.0},
                'strong': {'name': '强爆炸性', 'min': 400.0, 'max': 800.0},
                'super': {'name': '超强爆炸性', 'min': 800.0, 'max': float('inf')}
            }
            if hasattr(self, 'logger'):
                self.logger.error(f"✗ 加载配置文件失败: {e}，使用默认阈值")
    
    def __init__(self, db_path: str = "explosion_data.db", config_path: str = None):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的 explosion_data.db
            config_path: 配置文件路径，默认为 configs/experiment_config.yaml
        """
        self.logger = get_logger(__name__)
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # 加载爆炸性阈值配置
        self._load_explosion_thresholds(config_path)
        
        self._connect()
        self._check_and_upgrade_schema()
        self._create_tables()
    
    def _connect(self):
        """连接数据库"""
        try:
            # 设置超时时间，避免长时间锁定
            self.conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=10.0  # 10秒超时
            )
            self.cursor = self.conn.cursor()
            # 启用WAL模式，提高并发性能
            self.cursor.execute("PRAGMA journal_mode=WAL")
            # 启用外键支持
            self.cursor.execute("PRAGMA foreign_keys = ON")
            self.logger.info(f"✓ 数据库连接成功: {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 数据库连接失败: {e}")
            raise
    
    def _check_and_upgrade_schema(self):
        """检查并升级数据库表结构"""
        try:
            # 检查 experiment_sessions 表是否存在
            self.cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='experiment_sessions'
            """)
            
            table_exists = self.cursor.fetchone() is not None
            
            if table_exists:
                # 检查是否有必要的字段
                self.cursor.execute("PRAGMA table_info(experiment_sessions)")
                columns = [row[1] for row in self.cursor.fetchall()]
                
                required_columns = ['experiment_id', 'operator', 'client']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    self.logger.warning(f"⚠ 检测到旧表结构，缺少字段: {missing_columns}")
                    self.logger.info("🔄 升级数据库表结构...")
                    
                    # 添加缺失的列
                    for col in missing_columns:
                        try:
                            self.cursor.execute(f"""
                                ALTER TABLE experiment_sessions 
                                ADD COLUMN {col} TEXT
                            """)
                            self.logger.info(f"✓ 已添加字段: {col}")
                        except sqlite3.Error as e:
                            self.logger.error(f"✗ 添加字段 {col} 失败: {e}")
                    
                    self.conn.commit()
                    self.logger.info("✓ 数据库表结构升级完成")
                    
        except sqlite3.Error as e:
            self.logger.error(f"✗ 检查表结构失败: {e}")
    
    def _create_tables(self):
        """创建数据表"""
        try:
            # 创建实验会话表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    experiment_name TEXT,
                    sample_name TEXT,
                    client TEXT,
                    operator TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'running'
                )
            """)
            
            # 创建测试轮次表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    flame_length REAL NOT NULL,
                    max_flame_image_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE CASCADE
                )
            """)
            
            # 创建实验结果表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    total_rounds INTEGER NOT NULL,
                    avg_flame_length REAL NOT NULL,
                    explosion_level TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引以提高查询性能
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON test_rounds(session_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_result_session_id 
                ON experiment_results(session_id)
            """)
            
            # 新增：为常用查询字段添加索引
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status 
                ON experiment_sessions(status)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time 
                ON experiment_sessions(start_time)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rounds_round_number 
                ON test_rounds(session_id, round_number)
            """)
            
            self.conn.commit()
            self.logger.info("✓ 数据表创建成功")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 数据表创建失败: {e}")
            raise
    
    # ==================== 增 (Create) ====================
    
    def start_experiment_session(self, experiment_id: str = None,
                                 experiment_name: str = None, 
                                 sample_name: str = None,
                                 client: str = None,
                                 operator: str = None,
                                 description: str = None) -> int:
        """
        开始一个新的实验会话
        
        Args:
            experiment_id: 实验编号（如 EXP-20250101-001）
            experiment_name: 实验名称
            sample_name: 样品名称
            client: 委托单位
            operator: 操作员
            description: 实验描述
            
        Returns:
            会话ID (session_id)，失败返回-1
        """
        try:
            # 输入验证：至少需要实验名称或实验编号
            if not experiment_name and not experiment_id:
                self.logger.error("✗ 实验名称或实验编号至少需要一个")
                return -1
            
            self.cursor.execute("""
                INSERT INTO experiment_sessions 
                (experiment_id, start_time, experiment_name, sample_name, client, operator, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'running')
            """, (experiment_id, datetime.now(), experiment_name, sample_name, client, operator, description))
            
            self.conn.commit()
            session_id = self.cursor.lastrowid
            self.logger.info(f"✓ 实验会话已启动，会话ID: {session_id}, 实验编号: {experiment_id}, 实验名称: {experiment_name}")
            return session_id
        except sqlite3.Error as e:
            self.logger.error(f"✗ 启动实验会话失败: {e}")
            self.conn.rollback()
            return -1
    
    def add_test_round(self, session_id: int, round_number: int, 
                      flame_length: float, max_flame_image_path: str = None) -> int:
        """
        添加一轮测试数据
        
        Args:
            session_id: 实验会话ID
            round_number: 轮次编号 (1-10)
            flame_length: 火焰长度(mm)
            max_flame_image_path: 最大火焰图片路径
            
        Returns:
            记录ID
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return -1
            
            if not (1 <= round_number <= 10):
                self.logger.error(f"✗ 无效的轮次编号: {round_number}，应在1-10之间")
                return -1
            
            if flame_length < 0:
                self.logger.error(f"✗ 无效的火焰长度: {flame_length}")
                return -1
            
            # 检查是否已存在该轮次
            self.cursor.execute("""
                SELECT id FROM test_rounds 
                WHERE session_id = ? AND round_number = ?
            """, (session_id, round_number))
            
            existing = self.cursor.fetchone()
            if existing:
                self.logger.warning(f"⚠ 会话 {session_id} 第 {round_number} 轮已存在，将更新")
                # 更新现有记录
                self.cursor.execute("""
                    UPDATE test_rounds 
                    SET flame_length = ?, max_flame_image_path = ?, timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (flame_length, max_flame_image_path, existing[0]))
                self.conn.commit()
                self.logger.info(f"✓ 第{round_number}轮测试数据已更新: 火焰长度={flame_length}mm")
                return existing[0]
            
            # 插入新记录
            self.cursor.execute("""
                INSERT INTO test_rounds 
                (session_id, round_number, flame_length, max_flame_image_path)
                VALUES (?, ?, ?, ?)
            """, (session_id, round_number, flame_length, max_flame_image_path))
            
            self.conn.commit()
            self.logger.info(f"✓ 第{round_number}轮测试数据已记录: 火焰长度={flame_length}mm")
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"✗ 添加测试轮次失败: {e}")
            self.conn.rollback()
            return -1
    
    def add_batch_test_rounds(self, session_id: int, 
                             rounds_data: List[Tuple[int, float, str]]) -> int:
        """
        批量添加测试轮次数据
        
        Args:
            session_id: 实验会话ID
            rounds_data: 轮次数据列表 [(round_number, flame_length, image_path), ...]
            
        Returns:
            成功插入的记录数，失败返回0
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return 0
            
            if not rounds_data:
                self.logger.error("✗ 没有提供轮次数据")
                return 0
            
            # 验证每个轮次数据
            for r in rounds_data:
                if len(r) < 2:
                    self.logger.error("✗ 轮次数据格式错误")
                    return 0
                round_number, flame_length = r[0], r[1]
                if not (1 <= round_number <= 10):
                    self.logger.error(f"✗ 无效的轮次编号: {round_number}")
                    return 0
                if flame_length < 0:
                    self.logger.error(f"✗ 无效的火焰长度: {flame_length}")
                    return 0
            
            data_with_session = [(session_id, r[0], r[1], r[2]) for r in rounds_data]
            self.cursor.executemany("""
                INSERT INTO test_rounds 
                (session_id, round_number, flame_length, max_flame_image_path)
                VALUES (?, ?, ?, ?)
            """, data_with_session)
            
            self.conn.commit()
            count = self.cursor.rowcount
            self.logger.info(f"✓ 批量添加 {count} 轮测试数据")
            return count
        except sqlite3.Error as e:
            self.logger.error(f"✗ 批量添加测试轮次失败: {e}")
            self.conn.rollback()
            return 0
    
    # ==================== 业务逻辑方法 ====================
    
    def classify_explosion_strength(self, avg_flame_length: float) -> str:
        """
        根据平均火焰长度分类爆炸性强弱（从配置文件读取阈值）
        
        Args:
            avg_flame_length: 平均火焰长度(mm)
            
        Returns:
            爆炸性等级 (无爆炸性/弱爆炸性/强爆炸性/超强爆炸性)
        """
        # 使用动态加载的阈值
        if avg_flame_length < self.EXPLOSION_LEVELS['none']['max']:
            return self.EXPLOSION_LEVELS['none']['name']
        elif avg_flame_length < self.EXPLOSION_LEVELS['weak']['max']:
            return self.EXPLOSION_LEVELS['weak']['name']
        elif avg_flame_length < self.EXPLOSION_LEVELS['strong']['max']:
            return self.EXPLOSION_LEVELS['strong']['name']
        else:
            return self.EXPLOSION_LEVELS['super']['name']
    
    def generate_conclusion(self, session_id: int) -> str:
        """
        根据实验数据自动生成结论
        
        Args:
            session_id: 实验会话ID
            
        Returns:
            生成的结论文本
        """
        try:
            # 获取测试轮次和平均火焰长度
            result = self.get_session_result(session_id)
            if not result:
                return "实验数据不完整，无法生成结论。"
            
            total_rounds = result['total_rounds']
            avg_flame_length = result['avg_flame_length']
            explosion_level = result['explosion_level']
            
            # 生成结论
            conclusion = (
                f"经过{total_rounds}次重复测试，"
                f"平均火焰长度为{avg_flame_length:.1f}mm，"
                f"属于{explosion_level}。"
            )
            
            self.logger.info(f"✓ 自动生成实验结论: {conclusion}")
            return conclusion
            
        except Exception as e:
            self.logger.error(f"✗ 生成实验结论失败: {e}")
            return "实验数据符合标准要求。"
    
    def calculate_session_average(self, session_id: int) -> Optional[float]:
        """
        计算某个会话的平均火焰长度
        
        Args:
            session_id: 实验会话ID
            
        Returns:
            平均火焰长度，如果没有数据返回None
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return None
            
            self.cursor.execute("""
                SELECT AVG(flame_length) 
                FROM test_rounds 
                WHERE session_id = ?
            """, (session_id,))
            
            result = self.cursor.fetchone()
            if result and result[0] is not None:
                return round(result[0], 2)
            return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 计算平均值失败: {e}")
            return None
    
    def finalize_experiment(self, session_id: int, status: str = 'completed') -> bool:
        """
        完成实验，计算平均值并保存结果
        
        Args:
            session_id: 实验会话ID
            status: 结束状态 (completed/cancelled/error)
            
        Returns:
            是否成功
        """
        try:
            # 检查会话状态，避免重复完成
            session = self.get_session_by_id(session_id)
            if not session:
                self.logger.error(f"✗ 会话 {session_id} 不存在")
                return False
            
            if session.get('status') in ['completed', 'cancelled']:
                self.logger.warning(f"⚠ 会话 {session_id} 已经完成，状态: {session.get('status')}")
                return False
            
            # 获取测试轮次数
            self.cursor.execute("""
                SELECT COUNT(*), AVG(flame_length)
                FROM test_rounds 
                WHERE session_id = ?
            """, (session_id,))
            
            result = self.cursor.fetchone()
            if not result or result[0] == 0:
                self.logger.error(f"✗ 会话 {session_id} 没有测试数据")
                self.conn.rollback()  # 显式回滚
                return False
            
            total_rounds = result[0]
            avg_flame_length = round(result[1], 2)
            
            # 分类爆炸性强弱
            explosion_level = self.classify_explosion_strength(avg_flame_length)
            
            # 保存结果
            self.cursor.execute("""
                INSERT INTO experiment_results 
                (session_id, total_rounds, avg_flame_length, explosion_level)
                VALUES (?, ?, ?, ?)
            """, (session_id, total_rounds, avg_flame_length, explosion_level))
            
            # 更新会话状态
            self.cursor.execute("""
                UPDATE experiment_sessions 
                SET end_time = ?, status = ?
                WHERE id = ?
            """, (datetime.now(), status, session_id))
            
            self.conn.commit()
            self.logger.info(f"✓ 实验已完成 - 平均火焰长度: {avg_flame_length}mm, 爆炸性: {explosion_level}")
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"✗ 完成实验失败: {e}")
            self.conn.rollback()  # 确保回滚
            return False
        except Exception as e:
            self.logger.error(f"✗ 完成实验异常: {e}")
            self.conn.rollback()  # 确保回滚
            return False
    
    def end_experiment_session(self, session_id: int, status: str = 'completed') -> bool:
        """
        结束实验会话（不保存结果，仅更新状态）
        
        Args:
            session_id: 会话ID
            status: 结束状态 (completed/stopped/cancelled)
        
        Returns:
            是否成功
        """
        try:
            self.cursor.execute("""
                UPDATE experiment_sessions 
                SET end_time = ?, status = ?
                WHERE id = ?
            """, (datetime.now(), status, session_id))
            
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 实验会话已结束 ID: {session_id}, 状态: {status}")
                return True
            else:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 结束会话失败: {e}")
            self.conn.rollback()
            return False
    
    # ==================== 删 (Delete) ====================
    
    def delete_session(self, session_id: int) -> bool:
        """
        删除实验会话及其所有关联数据和文件
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否删除成功
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return False
            
            # 1. 在删除数据库记录前，查询所有关联的图片路径
            self.cursor.execute("""
                SELECT max_flame_image_path 
                FROM test_rounds 
                WHERE session_id = ? AND max_flame_image_path IS NOT NULL
            """, (session_id,))
            
            image_paths = [row[0] for row in self.cursor.fetchall() if row[0]]
            deleted_files_count = 0
            
            # 2. 删除物理图片文件
            max_flame_images_dir = PathManager.get_max_flame_images_path()
            for image_path in image_paths:
                try:
                    # 如果路径是绝对路径，直接使用；否则相对于max_flame_images目录
                    if os.path.isabs(image_path):
                        full_path = image_path
                    else:
                        # 提取文件名
                        filename = os.path.basename(image_path)
                        full_path = os.path.join(max_flame_images_dir, filename)
                    
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        deleted_files_count += 1
                        self.logger.info(f"✓ 已删除图片文件: {full_path}")
                    else:
                        self.logger.warning(f"⚠ 图片文件不存在，跳过: {full_path}")
                except Exception as e:
                    self.logger.error(f"✗ 删除图片文件失败: {image_path}, 错误: {e}")
                    # 继续执行，不因单个文件删除失败而中断
            
            # 3. 删除数据库记录（利用CASCADE自动删除关联表）
            self.cursor.execute("""
                DELETE FROM experiment_sessions WHERE id = ?
            """, (session_id,))
            
            self.conn.commit()
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已删除会话 ID: {session_id} 及其所有数据，共删除 {deleted_files_count} 个图片文件")
                return True
            else:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 删除会话失败: {e}")
            self.conn.rollback()
            return False
    
    def delete_test_round(self, round_id: int) -> bool:
        """
        删除单个测试轮次
        
        Args:
            round_id: 轮次记录ID
            
        Returns:
            是否删除成功
        """
        try:
            # 输入验证
            if round_id <= 0:
                self.logger.error("✗ 无效的轮次ID")
                return False
            
            self.cursor.execute("""
                DELETE FROM test_rounds WHERE id = ?
            """, (round_id,))
            
            self.conn.commit()
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已删除测试轮次 ID: {round_id}")
                return True
            else:
                self.logger.error(f"✗ 未找到测试轮次 ID: {round_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 删除测试轮次失败: {e}")
            self.conn.rollback()
            return False
    
    def delete_all_data(self) -> bool:
        """
        删除所有数据（谨慎使用）
        
        Returns:
            是否删除成功
        """
        try:
            self.cursor.execute("DELETE FROM experiment_results")
            self.cursor.execute("DELETE FROM test_rounds")
            self.cursor.execute("DELETE FROM experiment_sessions")
            self.conn.commit()
            self.logger.info("✓ 所有数据已清空")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"✗ 清空数据失败: {e}")
            self.conn.rollback()
            return False
    
    # ==================== 改 (Update) ====================
    
    def update_test_round(self, round_id: int, **kwargs) -> bool:
        """
        更新测试轮次数据
        
        Args:
            round_id: 轮次记录ID
            **kwargs: 要更新的字段，如 flame_length=100.0, max_flame_image_path="path/to/image.jpg"
            
        Returns:
            是否更新成功
        """
        # 输入验证
        if round_id <= 0:
            self.logger.error("✗ 无效的轮次ID")
            return False
        
        if not kwargs:
            self.logger.error("✗ 没有提供要更新的字段")
            return False
        
        # 构建更新语句
        valid_fields = ['round_number', 'flame_length', 'max_flame_image_path']
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            self.logger.error("✗ 没有有效的更新字段")
            return False
        
        try:
            sql = f"UPDATE test_rounds SET {', '.join(update_fields)} WHERE id = ?"
            values.append(round_id)
            
            self.cursor.execute(sql, values)
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已更新测试轮次 ID: {round_id}")
                return True
            else:
                self.logger.error(f"✗ 未找到测试轮次 ID: {round_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 更新数据失败: {e}")
            self.conn.rollback()
            return False
    
    def update_session(self, session_id: int, **kwargs) -> bool:
        """
        更新实验会话信息
        
        Args:
            session_id: 会话ID
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        # 输入验证
        if session_id <= 0:
            self.logger.error("✗ 无效的会话ID")
            return False
        
        if not kwargs:
            self.logger.error("✗ 没有提供要更新的字段")
            return False
        
        valid_fields = ['experiment_name', 'sample_name', 'client', 'operator', 'description', 'status']
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            self.logger.error("✗ 没有有效的更新字段")
            return False
        
        try:
            sql = f"UPDATE experiment_sessions SET {', '.join(update_fields)} WHERE id = ?"
            values.append(session_id)
            
            self.cursor.execute(sql, values)
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已更新会话 ID: {session_id}")
                return True
            else:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 更新会话失败: {e}")
            self.conn.rollback()
            return False
    
    # ==================== 查 (Read) ====================
    
    def get_session_by_id(self, session_id: int) -> Optional[Dict]:
        """
        根据ID查询实验会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息字典，不存在返回None
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return None
            
            self.cursor.execute("""
                SELECT id, start_time, end_time, experiment_name, 
                       sample_name, client, operator, description, status
                FROM experiment_sessions
                WHERE id = ?
            """, (session_id,))
            
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'start_time': row[1],
                    'end_time': row[2],
                    'experiment_name': row[3],
                    'sample_name': row[4],
                    'client': row[5],
                    'operator': row[6],
                    'description': row[7],
                    'status': row[8]
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询会话失败: {e}")
            return None
    
    def get_session_test_rounds(self, session_id: int) -> List[Dict]:
        """
        获取某个会话的所有测试轮次
        
        Args:
            session_id: 实验会话ID
            
        Returns:
            测试轮次列表，不存在返回空列表
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return []
            
            self.cursor.execute("""
                SELECT id, session_id, round_number, flame_length, 
                       max_flame_image_path, timestamp
                FROM test_rounds
                WHERE session_id = ?
                ORDER BY round_number ASC
            """, (session_id,))
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'session_id': row[1],
                    'round_number': row[2],
                    'flame_length': row[3],
                    'max_flame_image_path': row[4],
                    'timestamp': row[5]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询测试轮次失败: {e}")
            return []
    
    def get_session_result(self, session_id: int) -> Optional[Dict]:
        """
        获取实验会话的结果
        
        Args:
            session_id: 实验会话ID
            
        Returns:
            结果字典，不存在返回None
        """
        try:
            # 输入验证
            if session_id <= 0:
                self.logger.error("✗ 无效的会话ID")
                return None
            
            self.cursor.execute("""
                SELECT id, session_id, total_rounds, avg_flame_length, 
                       explosion_level, timestamp
                FROM experiment_results
                WHERE session_id = ?
            """, (session_id,))
            
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'session_id': row[1],
                    'total_rounds': row[2],
                    'avg_flame_length': row[3],
                    'explosion_level': row[4],
                    'timestamp': row[5]
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询实验结果失败: {e}")
            return None
    
    def get_all_experiment_sessions(self, status: str = None, order_by: str = 'start_time',
                        ascending: bool = False) -> List[Dict]:
        """
        查询所有实验会话
        
        Args:
            status: 过滤状态 (running/completed/cancelled/error)
            order_by: 排序字段
            ascending: 是否升序
            
        Returns:
            会话列表
        """
        try:
            # SQL注入防护：验证order_by字段
            if order_by not in self.VALID_ORDER_BY_FIELDS['get_all_experiment_sessions']:
                self.logger.warning(f"⚠ 无效的排序字段: {order_by}，使用默认值: start_time")
                order_by = 'start_time'
            
            order = 'ASC' if ascending else 'DESC'
            
            if status:
                self.cursor.execute(f"""
                    SELECT id, experiment_id, start_time, end_time, experiment_name, 
                           sample_name, client, operator, description, status
                    FROM experiment_sessions
                    WHERE status = ?
                    ORDER BY {order_by} {order}
                """, (status,))
            else:
                self.cursor.execute(f"""
                    SELECT id, experiment_id, start_time, end_time, experiment_name, 
                           sample_name, client, operator, description, status
                    FROM experiment_sessions
                    ORDER BY {order_by} {order}
                """)
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'experiment_id': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'experiment_name': row[4],
                    'sample_name': row[5],
                    'client': row[6],
                    'operator': row[7],
                    'description': row[8],
                    'status': row[9]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询实验会话失败: {e}")
            return []
    
    def get_results_by_explosion_level(self, explosion_level: str) -> List[Dict]:
        """
        根据爆炸性等级查询结果
        
        Args:
            explosion_level: 爆炸性等级 (无爆炸性/弱爆炸性/强爆炸性/超强爆炸性)
            
        Returns:
            结果列表
        """
        try:
            self.cursor.execute("""
                SELECT r.id, r.session_id, r.total_rounds, r.avg_flame_length, 
                       r.explosion_level, r.timestamp, s.sample_name, s.experiment_name
                FROM experiment_results r
                JOIN experiment_sessions s ON r.session_id = s.id
                WHERE r.explosion_level = ?
                ORDER BY r.timestamp DESC
            """, (explosion_level,))
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'session_id': row[1],
                    'total_rounds': row[2],
                    'avg_flame_length': row[3],
                    'explosion_level': row[4],
                    'timestamp': row[5],
                    'sample_name': row[6],
                    'experiment_name': row[7]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询爆炸性等级结果失败: {e}")
            return []
    
    def get_all_results(self, order_by: str = 'timestamp', 
                       ascending: bool = False) -> List[Dict]:
        """
        查询所有实验结果
        
        Args:
            order_by: 排序字段
            ascending: 是否升序
            
        Returns:
            结果列表
        """
        try:
            # SQL注入防护：验证order_by字段
            if order_by not in self.VALID_ORDER_BY_FIELDS['get_all_results']:
                self.logger.warning(f"⚠ 无效的排序字段: {order_by}，使用默认值: timestamp")
                order_by = 'timestamp'
            
            order = 'ASC' if ascending else 'DESC'
            self.cursor.execute(f"""
                SELECT r.id, r.session_id, r.total_rounds, r.avg_flame_length, 
                       r.explosion_level, r.timestamp, s.sample_name, s.experiment_name
                FROM experiment_results r
                JOIN experiment_sessions s ON r.session_id = s.id
                ORDER BY r.{order_by} {order}
            """)
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'session_id': row[1],
                    'total_rounds': row[2],
                    'avg_flame_length': row[3],
                    'explosion_level': row[4],
                    'timestamp': row[5],
                    'sample_name': row[6],
                    'experiment_name': row[7]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询所有结果失败: {e}")
            return []
    
    def get_statistics(self) -> Optional[Dict]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            stats = {}
            
            # 会话总数
            self.cursor.execute("SELECT COUNT(*) FROM experiment_sessions")
            stats['total_sessions'] = self.cursor.fetchone()[0]
            
            # 各状态会话数
            self.cursor.execute("""
                SELECT status, COUNT(*) 
                FROM experiment_sessions 
                GROUP BY status
            """)
            stats['sessions_by_status'] = dict(self.cursor.fetchall())
            
            # 各爆炸性等级数量
            self.cursor.execute("""
                SELECT explosion_level, COUNT(*) 
                FROM experiment_results 
                GROUP BY explosion_level
            """)
            stats['results_by_level'] = dict(self.cursor.fetchall())
            
            # 平均火焰长度统计
            self.cursor.execute("""
                SELECT AVG(avg_flame_length), MIN(avg_flame_length), MAX(avg_flame_length)
                FROM experiment_results
            """)
            row = self.cursor.fetchone()
            if row[0] is not None:
                stats['flame_length_stats'] = {
                    'avg': round(row[0], 2),
                    'min': row[1],
                    'max': row[2]
                }
            
            return stats
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询统计信息失败: {e}")
            return None
    
    # ==================== 数据导出 ====================
    
    def export_to_csv(self, output_file: str, session_id: int = None) -> bool:
        """
        导出数据到CSV文件
        
        Args:
            output_file: 输出文件路径
            session_id: 会话ID (可选，不指定则导出所有结果)
            
        Returns:
            是否导出成功
        """
        import csv
        
        try:
            if session_id:
                # 导出特定会话的测试轮次
                rounds = self.get_session_test_rounds(session_id)
                if not rounds:
                    self.logger.error(f"✗ 会话 {session_id} 没有测试数据")
                    return False
                
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['轮次', '火焰长度(mm)', '最大火焰图片路径', '时间戳']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for row in rounds:
                        writer.writerow({
                            '轮次': row['round_number'],
                            '火焰长度(mm)': row['flame_length'],
                            '最大火焰图片路径': row['max_flame_image_path'] or '',
                            '时间戳': row['timestamp']
                        })
                
                self.logger.info(f"✓ 会话 {session_id} 数据已导出到: {output_file}, 共 {len(rounds)} 轮")
            else:
                # 导出所有实验结果
                results = self.get_all_results()
                if not results:
                    self.logger.error("✗ 没有结果数据可导出")
                    return False
                
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['会话ID', '实验名称', '样品名称', '测试轮次', 
                                '平均火焰长度(mm)', '爆炸性等级', '时间戳']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for row in results:
                        writer.writerow({
                            '会话ID': row['session_id'],
                            '实验名称': row['experiment_name'] or '',
                            '样品名称': row['sample_name'] or '',
                            '测试轮次': row['total_rounds'],
                            '平均火焰长度(mm)': row['avg_flame_length'],
                            '爆炸性等级': row['explosion_level'],
                            '时间戳': row['timestamp']
                        })
                
                self.logger.info(f"✓ 数据已导出到: {output_file}, 共 {len(results)} 条记录")
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 导出数据失败: {e}")
            return False
    
    # ==================== 数据库管理 ====================
    
    def vacuum(self):
        """压缩数据库，回收空间"""
        try:
            self.cursor.execute("VACUUM")
            self.logger.info("✓ 数据库已优化")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 数据库优化失败: {e}")
    
    def backup(self, backup_path: str) -> bool:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否备份成功
        """
        try:
            import shutil
            import os
            
            # 确保备份目录存在
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
                self.logger.info(f"✓ 已创建备份目录: {backup_dir}")
            
            # 先提交所有未提交的事务，确保数据已写入
            if self.conn:
                self.conn.commit()
            
            # 复制文件
            shutil.copy2(self.db_path, backup_path)
            
            # 验证备份文件是否存在且大小合理
            if os.path.exists(backup_path):
                original_size = os.path.getsize(self.db_path)
                backup_size = os.path.getsize(backup_path)
                if backup_size > 0 and abs(original_size - backup_size) < 1024:  # 允许1KB差异
                    self.logger.info(f"✓ 数据库已备份到: {backup_path} (大小: {backup_size} 字节)")
                    return True
                else:
                    self.logger.error(f"✗ 备份文件大小异常: 原始={original_size}, 备份={backup_size}")
                    return False
            else:
                self.logger.error("✗ 备份文件不存在")
                return False
        except Exception as e:
            self.logger.error(f"✗ 数据库备份失败: {e}")
            import traceback
            self.logger.error(f"✗ 错误详情: {traceback.format_exc()}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("✓ 数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def __del__(self):
        """析构函数"""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass  # 忽略析构时的错误


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建数据库实例
    db = ExplosionDatabase("test_explosion.db")
    
    print("\n" + "="*60)
    print("爆炸性实验数据库功能测试")
    print("="*60)
    
    # 1. 开始实验会话
    print("\n1. 开始实验会话:")
    session_id = db.start_experiment_session(
        experiment_name="煤粉爆炸性测试",
        sample_name="煤样A",
        description="测试煤样A的爆炸性特征"
    )
    print(f"会话ID: {session_id}")
    
    # 2. 模拟5轮测试
    print("\n2. 添加测试数据 (前5轮):")
    test_data_round1 = [
        (1, 15.5, "images/test1_round1.jpg"),
        (2, 18.2, "images/test1_round2.jpg"),
        (3, 16.8, "images/test1_round3.jpg"),
        (4, 17.5, "images/test1_round4.jpg"),
        (5, 19.0, "images/test1_round5.jpg"),
    ]
    
    for round_num, flame_len, img_path in test_data_round1:
        db.add_test_round(session_id, round_num, flame_len, img_path)
    
    # 3. 计算平均值
    print("\n3. 计算前5轮平均火焰长度:")
    avg_length = db.calculate_session_average(session_id)
    print(f"平均火焰长度: {avg_length}mm")
    
    # 模拟：如果平均值低于20，继续5轮测试
    if avg_length < 20:
        print("\n4. 火焰长度低于20mm，继续后5轮测试:")
        test_data_round2 = [
            (6, 22.5, "images/test1_round6.jpg"),
            (7, 25.0, "images/test1_round7.jpg"),
            (8, 23.8, "images/test1_round8.jpg"),
            (9, 24.2, "images/test1_round9.jpg"),
            (10, 26.5, "images/test1_round10.jpg"),
        ]
        
        for round_num, flame_len, img_path in test_data_round2:
            db.add_test_round(session_id, round_num, flame_len, img_path)
        
        # 重新计算平均值
        avg_length = db.calculate_session_average(session_id)
        print(f"10轮平均火焰长度: {avg_length}mm")
    
    # 5. 完成实验
    print("\n5. 完成实验并保存结果:")
    db.finalize_experiment(session_id)
    
    # 6. 查询测试轮次
    print("\n6. 查询所有测试轮次:")
    rounds = db.get_session_test_rounds(session_id)
    print(f"共进行了 {len(rounds)} 轮测试")
    for r in rounds[:3]:  # 只显示前3轮
        print(f"  第{r['round_number']}轮: {r['flame_length']}mm")
    
    # 7. 查询实验结果
    print("\n7. 查询实验结果:")
    result = db.get_session_result(session_id)
    if result:
        print(f"  测试轮次: {result['total_rounds']}")
        print(f"  平均火焰长度: {result['avg_flame_length']}mm")
        print(f"  爆炸性等级: {result['explosion_level']}")
    
    # 8. 创建另一个测试（强爆炸性）
    print("\n8. 创建第二个实验 (强爆炸性):")
    session_id2 = db.start_experiment_session(
        experiment_name="煤粉爆炸性测试",
        sample_name="煤样B",
        description="测试煤样B的爆炸性特征"
    )
    
    # 添加5轮高火焰长度数据
    strong_explosion_data = [
        (1, 520.5, "images/test2_round1.jpg"),
        (2, 580.2, "images/test2_round2.jpg"),
        (3, 550.8, "images/test2_round3.jpg"),
        (4, 600.5, "images/test2_round4.jpg"),
        (5, 590.0, "images/test2_round5.jpg"),
    ]
    
    db.add_batch_test_rounds(session_id2, strong_explosion_data)
    db.finalize_experiment(session_id2)
    
    result2 = db.get_session_result(session_id2)
    if result2:
        print(f"  样品B - 爆炸性等级: {result2['explosion_level']}")
    
    # 9. 统计信息
    print("\n9. 数据库统计:")
    stats = db.get_statistics()
    if stats:
        print(f"  总会话数: {stats['total_sessions']}")
        print(f"  各状态会话: {stats.get('sessions_by_status', {})}")
        print(f"  各爆炸性等级: {stats.get('results_by_level', {})}")
        if 'flame_length_stats' in stats:
            print(f"  火焰长度统计: 平均={stats['flame_length_stats']['avg']}mm, "
                  f"最小={stats['flame_length_stats']['min']}mm, "
                  f"最大={stats['flame_length_stats']['max']}mm")
    
    # 10. 导出数据
    print("\n10. 导出数据:")
    db.export_to_csv("test_explosion_results.csv")
    db.export_to_csv("test_session1_rounds.csv", session_id=session_id)
    
    # 11. 查询特定爆炸性等级
    print("\n11. 查询弱爆炸性样品:")
    weak_results = db.get_results_by_explosion_level("弱爆炸性")
    for r in weak_results:
        print(f"  样品: {r['sample_name']}, 平均火焰长度: {r['avg_flame_length']}mm")
    
    # 清理
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    db.close()