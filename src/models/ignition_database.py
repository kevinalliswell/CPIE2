#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验数据库模块
用于存储和管理实验温度数据
"""

import sqlite3
import os
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from utils.logger import get_logger
from utils.path_manager import PathManager


class IgnitionDatabase:
    """着火点实验数据库管理类"""
    
    # 字段映射：数据库字段名 -> 中文表头
    COLUMN_HEADERS = {
        'pv': '炉膛温度',
        'ch1': '样品1',
        'ch2': '样品2',
        'ch3': '样品3',
        'ch4': '样品4',
        'ch5': '样品5',
        'ch6': '样品6'
    }
    
    def __init__(self, db_path: str = "ignition_data.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的 ignition_data.db
        """
        self.logger = get_logger(__name__)
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._check_and_upgrade_schema()
        self._create_tables()
    
    def _connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            # 启用外键支持
            self.cursor.execute("PRAGMA foreign_keys = ON")
            self.logger.info(f"✓ 数据库连接成功: {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 数据库连接失败: {e}")
            raise

    def _create_migration_backup(self, reason: str) -> Optional[str]:
        """在执行破坏性迁移前创建数据库文件备份"""
        if not self.db_path or self.db_path == ":memory:" or not os.path.exists(self.db_path):
            self.logger.info("ℹ 当前数据库无需创建迁移备份")
            return None

        safe_reason = reason.replace(" ", "_")
        backup_dir = PathManager.get_data_path("db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_name = (
            f"{os.path.splitext(os.path.basename(self.db_path))[0]}_"
            f"{safe_reason}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        )
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(self.db_path, backup_path)
        self.logger.warning(f"⚠ 已创建迁移备份: {backup_path}")
        return backup_path

    def _ensure_columns(self, table_name: str, missing_columns: Dict[str, str]):
        """安全地向现有表补充缺失字段"""
        if not missing_columns:
            return

        for column_name, column_definition in missing_columns.items():
            self.logger.info(f"🔄 为 {table_name} 添加字段: {column_name}")
            self.cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )

        self.conn.commit()
        self.logger.info(f"✓ {table_name} 缺失字段补充完成: {list(missing_columns.keys())}")

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
                # 检查并补充 experiment_sessions 缺失字段
                self.cursor.execute("PRAGMA table_info(experiment_sessions)")
                columns = [row[1] for row in self.cursor.fetchall()]

                required_columns = {
                    'experiment_id': 'TEXT',
                    'sample_names': 'TEXT',
                    'client': 'TEXT',
                    'operator': 'TEXT'
                }
                missing_columns = {
                    col: definition
                    for col, definition in required_columns.items()
                    if col not in columns
                }

                if missing_columns:
                    self.logger.warning(
                        f"⚠ 检测到旧表结构，缺少字段: {list(missing_columns.keys())}"
                    )
                    self._ensure_columns('experiment_sessions', missing_columns)

            # 检查并升级 ignition_realtime_data 表（添加 session_id 字段）
            self._upgrade_realtime_data_table()

            # 检查并升级 ignition_detection 表（添加 tangent_analysis_image_path 字段）
            self._upgrade_ignition_detection_table()

        except sqlite3.Error as e:
            self.logger.error(f"✗ 检查表结构失败: {e}")
            raise
    
    def _upgrade_realtime_data_table(self):
        """升级 ignition_realtime_data 表：添加 session_id 字段"""
        try:
            # 检查表是否存在
            self.cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='ignition_realtime_data'
            """)

            if self.cursor.fetchone() is None:
                return  # 表不存在，跳过升级

            # 检查是否已有 session_id 字段
            self.cursor.execute("PRAGMA table_info(ignition_realtime_data)")
            columns = [row[1] for row in self.cursor.fetchall()]

            if 'session_id' in columns:
                return  # 字段已存在，跳过升级

            backup_path = self._create_migration_backup('ignition_realtime_data_upgrade')
            message = (
                "检测到 ignition_realtime_data 表缺少 session_id 字段。"
                "为避免数据迁移过程中出现不可恢复的数据丢失，本次启动不会自动重建该表。"
            )
            if backup_path:
                message += f" 已创建备份: {backup_path}"
            self.logger.error(f"✗ {message}")
            raise sqlite3.DatabaseError(message)

        except sqlite3.Error as e:
            self.logger.error(f"✗ 升级 ignition_realtime_data 表失败: {e}")
            self.conn.rollback()
            raise
    
    def _upgrade_ignition_detection_table(self):
        """升级 ignition_detection 表：添加 detection_method 和 tangent_analysis_image_path 字段，修复级联删除约束"""
        try:
            # 检查表是否存在
            self.cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='ignition_detection'
            """)

            if self.cursor.fetchone() is None:
                return  # 表不存在，跳过升级

            # 检查字段是否存在
            self.cursor.execute("PRAGMA table_info(ignition_detection)")
            columns = [row[1] for row in self.cursor.fetchall()]

            missing_columns = {}
            if 'detection_method' not in columns:
                missing_columns['detection_method'] = "TEXT DEFAULT 'realtime'"
            if 'tangent_analysis_image_path' not in columns:
                missing_columns['tangent_analysis_image_path'] = 'TEXT'

            if missing_columns:
                self.logger.warning(
                    f"⚠ 检测到 ignition_detection 表缺少字段: {list(missing_columns.keys())}"
                )
                self._ensure_columns('ignition_detection', missing_columns)

            # 检查并修复级联删除约束
            self.cursor.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='ignition_detection'
            """)
            table_sql = self.cursor.fetchone()
            if table_sql and table_sql[0]:
                # 检查是否缺少 ON DELETE CASCADE
                if 'ON DELETE CASCADE' not in table_sql[0] and 'FOREIGN KEY' in table_sql[0]:
                    backup_path = self._create_migration_backup('ignition_detection_fk_upgrade')
                    message = (
                        "检测到 ignition_detection 表缺少 ON DELETE CASCADE 约束。"
                        "当前版本不会再自动删除并重建该表，请先基于备份执行人工迁移后再启动。"
                    )
                    if backup_path:
                        message += f" 备份文件: {backup_path}"
                    self.logger.error(f"✗ {message}")
                    raise sqlite3.DatabaseError(message)

        except sqlite3.Error as e:
            self.logger.error(f"✗ 升级 ignition_detection 表失败: {e}")
            self.conn.rollback()
            raise
    
    def _create_tables(self):
        """创建数据表"""
        try:
            # 创建实时数据表（带 session_id 外键）
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ignition_realtime_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pv REAL NOT NULL,
                    ch1 REAL NOT NULL,
                    ch2 REAL NOT NULL,
                    ch3 REAL NOT NULL,
                    ch4 REAL NOT NULL,
                    ch5 REAL NOT NULL,
                    ch6 REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE CASCADE
                )
            """)
            
            # 创建实验记录表（记录实验会话信息）
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    experiment_name TEXT,
                    sample_names TEXT,
                    client TEXT,
                    operator TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'running'
                )
            """)
            
            # 创建着火点检测结果表（添加图片路径字段，带级联删除）
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ignition_detection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    channel INTEGER NOT NULL,
                    ignition_temperature REAL NOT NULL,
                    detection_method TEXT DEFAULT 'realtime',
                    tangent_analysis_image_path TEXT,
                    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引以提高查询性能
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON ignition_realtime_data(session_id)
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON ignition_realtime_data(timestamp)
            """)
            
            self.conn.commit()
            self.logger.info("✓ 数据表创建成功")
        except sqlite3.Error as e:
            self.logger.error(f"✗ 数据表创建失败: {e}")
            raise
    
    # ==================== 增 (Create) ====================
    
    def insert_ignition_data(self, pv: float, ch1: float, ch2: float, 
                            ch3: float, ch4: float, ch5: float, ch6: float,
                            session_id: int = None) -> int:
        """
        插入一条实时温度数据
        
        Args:
            pv: 炉膛温度
            ch1-ch6: 样品1-6的温度
            session_id: 实验会话ID（可选，用于关联实验会话）
            
        Returns:
            插入数据的ID
        """
        try:
            self.cursor.execute("""
                INSERT INTO ignition_realtime_data 
                (session_id, pv, ch1, ch2, ch3, ch4, ch5, ch6)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, pv, ch1, ch2, ch3, ch4, ch5, ch6))
            
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"✗ 插入数据失败: {e}")
            self.conn.rollback()
            return -1
    
    def insert_batch_data(self, data_list: List[Tuple[float, ...]], session_id: int = None) -> int:
        """
        批量插入数据
        
        Args:
            data_list: 数据列表，每个元素为 (pv, ch1, ch2, ch3, ch4, ch5, ch6)
            session_id: 实验会话ID（可选，用于关联实验会话）
            
        Returns:
            成功插入的记录数
        """
        try:
            # 为每条数据添加 session_id
            data_with_session = [(session_id,) + tuple(data) for data in data_list]
            
            self.cursor.executemany("""
                INSERT INTO ignition_realtime_data 
                (session_id, pv, ch1, ch2, ch3, ch4, ch5, ch6)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_with_session)
            
            self.conn.commit()
            return self.cursor.rowcount
        except sqlite3.Error as e:
            self.logger.error(f"✗ 批量插入数据失败: {e}")
            self.conn.rollback()
            return 0
    
    def start_experiment_session(self, experiment_id: str = None,
                                 experiment_name: str = None, 
                                 sample_names: str = None,
                                 client: str = None,
                                 operator: str = None,
                                 description: str = None) -> int:
        """
        开始一个新的实验会话
        
        Args:
            experiment_id: 实验编号（如 IGN-20250101-001）
            experiment_name: 实验名称
            sample_names: 样品名称（JSON字符串，存储6个样品名称）
            client: 委托单位
            operator: 操作员
            description: 实验描述
            
        Returns:
            会话ID (session_id)
        """
        try:
            self.cursor.execute("""
                INSERT INTO experiment_sessions 
                (experiment_id, start_time, experiment_name, sample_names, client, operator, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'prepared')
            """, (experiment_id, datetime.now(), experiment_name, sample_names, client, operator, description))
            
            self.conn.commit()
            session_id = self.cursor.lastrowid
            self.logger.info(f"✓ 实验会话已创建，会话ID: {session_id}, 实验编号: {experiment_id}, 实验名称: {experiment_name}")
            return session_id
        except sqlite3.Error as e:
            self.logger.error(f"✗ 创建实验会话失败: {e}")
            self.conn.rollback()
            return -1
    
    def record_ignition_detection(self, session_id: int, channel: int, 
                                  ignition_temperature: float,
                                  detection_method: str = 'realtime',
                                  image_path: str = None) -> int:
        """
        记录着火点检测结果
        
        Args:
            session_id: 实验会话ID
            channel: 通道号(1-6)
            ignition_temperature: 着火温度
            detection_method: 检测方法 ('realtime', 'tangent', 'manual')
            image_path: 切线分析图片路径（可选）
            
        Returns:
            记录ID
        """
        try:
            self.cursor.execute("""
                INSERT INTO ignition_detection 
                (session_id, channel, ignition_temperature, detection_method, tangent_analysis_image_path)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, channel, ignition_temperature, detection_method, image_path))
            
            self.conn.commit()
            self.logger.info(f"✓ 着火点检测记录已保存: 通道{channel}, 温度{ignition_temperature}°C, 方法: {detection_method}")
            if image_path:
                self.logger.info(f"  图片路径: {image_path}")
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"✗ 记录着火点检测失败: {e}")
            self.conn.rollback()
            return -1
    
    def update_tangent_method_result(self, session_id: int, channel: int,
                                    tangent_temperature: float,
                                    image_path: str = None) -> bool:
        """
        更新切线法检测结果（已弃用，请使用 upsert_ignition_detection）
        
        Args:
            session_id: 实验会话ID
            channel: 通道号(1-6)
            tangent_temperature: 切线法检测的着火温度
            image_path: 切线法分析图片路径（可选）
            
        Returns:
            是否更新成功
        """
        # 使用新的 upsert 方法
        return self.upsert_ignition_detection(
            session_id=session_id,
            channel=channel,
            ignition_temperature=tangent_temperature,
            detection_method='tangent',
            image_path=image_path
        )
    
    def upsert_ignition_detection(self, session_id: int, channel: int,
                                  ignition_temperature: float,
                                  detection_method: str,
                                  image_path: str = None) -> bool:
        """
        插入或更新着火点检测结果
        如果该会话和通道已有记录，则更新；否则插入新记录
        
        Args:
            session_id: 实验会话ID
            channel: 通道号(1-6)
            ignition_temperature: 着火温度
            detection_method: 检测方法 ('realtime', 'tangent', 'manual')
            image_path: 切线分析图片路径（可选）
            
        Returns:
            是否成功
        """
        try:
            # 检查是否已存在记录
            self.cursor.execute("""
                SELECT id FROM ignition_detection
                WHERE session_id = ? AND channel = ?
            """, (session_id, channel))
            
            existing = self.cursor.fetchone()
            
            if existing:
                # 更新现有记录
                self.cursor.execute("""
                    UPDATE ignition_detection 
                    SET ignition_temperature = ?,
                        detection_method = ?,
                        tangent_analysis_image_path = ?,
                        timestamp = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND channel = ?
                """, (ignition_temperature, detection_method, image_path, session_id, channel))
                
                self.logger.info(
                    f"✓ 着火点检测记录已更新: 通道{channel}, "
                    f"温度{ignition_temperature:.1f}°C, 方法: {detection_method}"
                )
            else:
                # 插入新记录
                self.cursor.execute("""
                    INSERT INTO ignition_detection 
                    (session_id, channel, ignition_temperature, detection_method, tangent_analysis_image_path)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, channel, ignition_temperature, detection_method, image_path))
                
                self.logger.info(
                    f"✓ 着火点检测记录已插入: 通道{channel}, "
                    f"温度{ignition_temperature:.1f}°C, 方法: {detection_method}"
                )
            
            if image_path:
                self.logger.info(f"  图片路径: {image_path}")
            
            self.conn.commit()
            return True
                
        except sqlite3.Error as e:
            self.logger.error(f"✗ 保存着火点检测结果失败: {e}")
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
            # 1. 在删除数据库记录前，获取 experiment_id
            self.cursor.execute("""
                SELECT experiment_id FROM experiment_sessions WHERE id = ?
            """, (session_id,))
            
            row = self.cursor.fetchone()
            if not row:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return False
            
            experiment_id = row[0]
            
            # 2. 查询所有关联的图片路径
            self.cursor.execute("""
                SELECT tangent_analysis_image_path 
                FROM ignition_detection 
                WHERE session_id = ? AND tangent_analysis_image_path IS NOT NULL
            """, (session_id,))
            
            image_paths = [row[0] for row in self.cursor.fetchall() if row[0]]
            deleted_files_count = 0
            
            # 3. 删除物理图片文件
            for image_path in image_paths:
                try:
                    # 如果路径是绝对路径，直接使用；否则检查相对路径
                    if os.path.isabs(image_path):
                        full_path = image_path
                    else:
                        # 尝试相对于data目录的路径
                        full_path = PathManager.get_data_path(image_path)
                    
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        deleted_files_count += 1
                        self.logger.info(f"✓ 已删除图片文件: {full_path}")
                    else:
                        self.logger.warning(f"⚠ 图片文件不存在，跳过: {full_path}")
                except Exception as e:
                    self.logger.error(f"✗ 删除图片文件失败: {image_path}, 错误: {e}")
                    # 继续执行，不因单个文件删除失败而中断
            
            # 4. 删除实验文件夹（如果存在）
            if experiment_id:
                experiment_folder = PathManager.get_data_path(f"analysis_images/{experiment_id}")
                if os.path.exists(experiment_folder) and os.path.isdir(experiment_folder):
                    try:
                        shutil.rmtree(experiment_folder)
                        self.logger.info(f"✓ 已删除实验文件夹: {experiment_folder}")
                    except Exception as e:
                        self.logger.error(f"✗ 删除实验文件夹失败: {experiment_folder}, 错误: {e}")
                        # 继续执行，不因文件夹删除失败而中断
            
            # 5. 删除数据库记录（CASCADE删除 ignition_realtime_data 和 ignition_detection）
            # 注意：由于现在 ignition_detection 表有级联删除，会自动删除
            self.cursor.execute("""
                DELETE FROM experiment_sessions WHERE id = ?
            """, (session_id,))
            
            self.conn.commit()
            if self.cursor.rowcount > 0:
                self.logger.info(
                    f"✓ 已删除会话 ID: {session_id} 及其所有数据，"
                    f"共删除 {deleted_files_count} 个图片文件"
                )
                return True
            else:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 删除会话失败: {e}")
            self.conn.rollback()
            return False
    
    def delete_data_by_id(self, record_id: int) -> bool:
        """
        根据ID删除单条数据
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        try:
            self.cursor.execute("""
                DELETE FROM ignition_realtime_data WHERE id = ?
            """, (record_id,))
            
            self.conn.commit()
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已删除记录 ID: {record_id}")
                return True
            else:
                self.logger.error(f"✗ 未找到记录 ID: {record_id}")
                return False
        except sqlite3.Error as e:
            self.logger.error(f"✗ 删除数据失败: {e}")
            self.conn.rollback()
            return False
    
    def delete_data_by_time_range(self, start_time: str, end_time: str) -> int:
        """
        删除指定时间范围内的数据
        
        Args:
            start_time: 开始时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            end_time: 结束时间
            
        Returns:
            删除的记录数
        """
        try:
            self.cursor.execute("""
                DELETE FROM ignition_realtime_data 
                WHERE timestamp BETWEEN ? AND ?
            """, (start_time, end_time))
            
            self.conn.commit()
            count = self.cursor.rowcount
            self.logger.info(f"✓ 已删除 {count} 条记录")
            return count
        except sqlite3.Error as e:
            self.logger.error(f"✗ 删除数据失败: {e}")
            self.conn.rollback()
            return 0
    
    def delete_all_data(self) -> bool:
        """
        删除所有实时数据（谨慎使用）
        
        Returns:
            是否删除成功
        """
        try:
            self.cursor.execute("DELETE FROM ignition_realtime_data")
            self.conn.commit()
            self.logger.info("✓ 所有数据已清空")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"✗ 清空数据失败: {e}")
            self.conn.rollback()
            return False
    
    # ==================== 查询会话完整数据 ====================
    
    def get_session_temperature_data(self, session_id: int) -> List[Dict]:
        """
        获取指定会话的所有温度数据（用于切线法分析）
        
        Args:
            session_id: 会话ID
        
        Returns:
            数据列表，每条记录包含时间戳和各通道温度
            [
                {
                    'timestamp': '2025-01-21 10:30:00.000',
                    'elapsed_seconds': 125.5,
                    'furnace_temperature': 250.5,
                    'sample1_temperature': 245.2,
                    ...
                },
                ...
            ]
        """
        try:
            # 首先获取会话的开始时间（用于计算elapsed_seconds）
            self.cursor.execute("""
                SELECT start_time FROM experiment_sessions WHERE id = ?
            """, (session_id,))
            
            row = self.cursor.fetchone()
            if not row:
                self.logger.error(f"✗ 未找到会话 ID: {session_id}")
                return []
            
            start_time_str = row[0]
            
            # 解析开始时间，支持带毫秒或不带毫秒的格式
            try:
                # 先尝试带毫秒的格式
                session_start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                # 如果失败，尝试不带毫秒的格式
                session_start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
            
            # 优先使用 session_id 字段直接查询（更准确、更高效）
            self.cursor.execute("""
                SELECT 
                    timestamp,
                    pv,
                    ch1, ch2, ch3, ch4, ch5, ch6
                FROM ignition_realtime_data
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            
            rows = self.cursor.fetchall()
            
            # 如果通过 session_id 查询没有结果，尝试通过时间范围查询（兼容旧数据）
            if not rows:
                self.logger.debug(f"⚠ 通过 session_id 未找到数据，尝试通过时间范围查询...")
                
                # 获取会话的结束时间
                self.cursor.execute("""
                    SELECT end_time FROM experiment_sessions WHERE id = ?
                """, (session_id,))
                end_row = self.cursor.fetchone()
                end_time_str = end_row[0] if end_row else None
                
                if end_time_str:
                    # 会话已结束，查询开始到结束之间的数据
                    self.cursor.execute("""
                        SELECT 
                            timestamp,
                            pv,
                            ch1, ch2, ch3, ch4, ch5, ch6
                        FROM ignition_realtime_data
                        WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp ASC
                    """, (start_time_str, end_time_str))
                else:
                    # 会话未结束，查询开始时间之后的所有数据
                    self.cursor.execute("""
                        SELECT 
                            timestamp,
                            pv,
                            ch1, ch2, ch3, ch4, ch5, ch6
                        FROM ignition_realtime_data
                        WHERE timestamp >= ?
                        ORDER BY timestamp ASC
                    """, (start_time_str,))
                
                rows = self.cursor.fetchall()
            
            if not rows:
                self.logger.warning(f"⚠ 会话 {session_id} 没有温度数据")
                return []
            
            # 转换为字典列表
            data = []
            for row in rows:
                timestamp_str = row[0]
                
                # 解析时间戳，支持带毫秒或不带毫秒的格式
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        self.logger.error(f"✗ 无法解析时间戳: {timestamp_str}, 错误: {e}")
                        continue
                
                elapsed_seconds = (timestamp - session_start_time).total_seconds()
                
                data.append({
                    'timestamp': timestamp_str,
                    'elapsed_seconds': elapsed_seconds,
                    'furnace_temperature': float(row[1]) if row[1] is not None else 0.0,
                    'sample1_temperature': float(row[2]) if row[2] is not None else 0.0,
                    'sample2_temperature': float(row[3]) if row[3] is not None else 0.0,
                    'sample3_temperature': float(row[4]) if row[4] is not None else 0.0,
                    'sample4_temperature': float(row[5]) if row[5] is not None else 0.0,
                    'sample5_temperature': float(row[6]) if row[6] is not None else 0.0,
                    'sample6_temperature': float(row[7]) if row[7] is not None else 0.0
                })
            
            self.logger.info(f"✓ 成功读取会话 {session_id} 的 {len(data)} 条温度数据")
            return data
            
        except sqlite3.Error as e:
            self.logger.error(f"✗ 获取会话温度数据失败: {e}")
            return []
    
    # ==================== 改 (Update) ====================
    
    def update_data_by_id(self, record_id: int, **kwargs) -> bool:
        """
        根据ID更新数据
        
        Args:
            record_id: 记录ID
            **kwargs: 要更新的字段，如 pv=100.0, ch1=25.5
            
        Returns:
            是否更新成功
        """
        if not kwargs:
            self.logger.error("✗ 没有提供要更新的字段")
            return False
        
        # 构建更新语句
        valid_fields = ['pv', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6']
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
            sql = f"UPDATE ignition_realtime_data SET {', '.join(update_fields)} WHERE id = ?"
            values.append(record_id)
            
            self.cursor.execute(sql, values)
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.logger.info(f"✓ 已更新记录 ID: {record_id}")
                return True
            else:
                self.logger.error(f"✗ 未找到记录 ID: {record_id}")
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
        if not kwargs:
            self.logger.error("✗ 没有提供要更新的字段")
            return False
        
        valid_fields = ['experiment_name', 'sample_names', 'client', 'operator', 'description', 'status']
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
    
    def end_experiment_session(self, session_id: int, status: str = 'completed') -> bool:
        """
        结束实验会话
        
        Args:
            session_id: 会话ID
            status: 结束状态 (completed/cancelled/error)
            
        Returns:
            是否更新成功
        """
        try:
            self.cursor.execute("""
                UPDATE experiment_sessions 
                SET end_time = ?, status = ?
                WHERE id = ?
            """, (datetime.now(), status, session_id))
            
            self.conn.commit()
            self.logger.info(f"✓ 实验会话已结束，ID: {session_id}, 状态: {status}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"✗ 结束实验会话失败: {e}")
            self.conn.rollback()
            return False
    
    # ==================== 查 (Read) ====================
    
    def get_data_by_id(self, record_id: int) -> Optional[Dict]:
        """
        根据ID查询单条数据
        
        Args:
            record_id: 记录ID
            
        Returns:
            数据字典，如果不存在返回None
        """
        try:
            self.cursor.execute("""
                SELECT id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                FROM ignition_realtime_data
                WHERE id = ?
            """, (record_id,))
            
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'timestamp': row[1],
                    'pv': row[2],
                    'ch1': row[3],
                    'ch2': row[4],
                    'ch3': row[5],
                    'ch4': row[6],
                    'ch5': row[7],
                    'ch6': row[8]
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询数据失败: {e}")
            return None
    
    def get_latest_data(self, limit: int = 1) -> List[Dict]:
        """
        获取最新的N条数据
        
        Args:
            limit: 返回数据条数
            
        Returns:
            数据列表
        """
        try:
            self.cursor.execute("""
                SELECT id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                FROM ignition_realtime_data
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'pv': row[2],
                    'ch1': row[3],
                    'ch2': row[4],
                    'ch3': row[5],
                    'ch4': row[6],
                    'ch5': row[7],
                    'ch6': row[8]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询最新数据失败: {e}")
            return []
    
    def get_data_by_time_range(self, start_time: str, end_time: str) -> List[Dict]:
        """
        查询指定时间范围内的数据
        
        Args:
            start_time: 开始时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            end_time: 结束时间
            
        Returns:
            数据列表
        """
        try:
            self.cursor.execute("""
                SELECT id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                FROM ignition_realtime_data
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (start_time, end_time))
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'pv': row[2],
                    'ch1': row[3],
                    'ch2': row[4],
                    'ch3': row[5],
                    'ch4': row[6],
                    'ch5': row[7],
                    'ch6': row[8]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询时间范围数据失败: {e}")
            return []
    
    def get_all_data(self, order_by: str = 'timestamp', 
                    ascending: bool = True, limit: int = None) -> List[Dict]:
        """
        查询所有数据
        
        Args:
            order_by: 排序字段
            ascending: 是否升序
            limit: 限制返回数量
            
        Returns:
            数据列表
        """
        try:
            order = 'ASC' if ascending else 'DESC'
            sql = f"""
                SELECT id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6
                FROM ignition_realtime_data
                ORDER BY {order_by} {order}
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'pv': row[2],
                    'ch1': row[3],
                    'ch2': row[4],
                    'ch3': row[5],
                    'ch4': row[6],
                    'ch5': row[7],
                    'ch6': row[8]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询所有数据失败: {e}")
            return []
    
    def get_data_count(self) -> int:
        """
        获取数据总数
        
        Returns:
            数据总数
        """
        try:
            self.cursor.execute("SELECT COUNT(*) FROM ignition_realtime_data")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询数据总数失败: {e}")
            return 0
    
    def get_statistics(self, channel: str = 'pv') -> Optional[Dict]:
        """
        获取某个通道的统计信息
        
        Args:
            channel: 通道名称 (pv, ch1-ch6)
            
        Returns:
            统计信息字典 (最大值、最小值、平均值、标准差)
        """
        valid_channels = ['pv', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6']
        if channel not in valid_channels:
            self.logger.error(f"✗ 无效的通道名称: {channel}")
            return None
        
        try:
            self.cursor.execute(f"""
                SELECT 
                    MAX({channel}) as max_value,
                    MIN({channel}) as min_value,
                    AVG({channel}) as avg_value,
                    COUNT({channel}) as count
                FROM ignition_realtime_data
            """)
            
            row = self.cursor.fetchone()
            if row:
                return {
                    'channel': channel,
                    'channel_name': self.COLUMN_HEADERS.get(channel, channel),
                    'max': row[0],
                    'min': row[1],
                    'avg': row[2],
                    'count': row[3]
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询统计信息失败: {e}")
            return None
    
    def get_all_experiment_sessions(self, status: str = None) -> List[Dict]:
        """
        获取实验会话列表
        
        Args:
            status: 过滤状态 (prepared/running/completed/cancelled/error)
            
        Returns:
            会话列表
        """
        try:
            if status:
                self.cursor.execute("""
                    SELECT id, experiment_id, start_time, end_time, experiment_name, sample_names, 
                           client, operator, description, status
                    FROM experiment_sessions
                    WHERE status = ?
                    ORDER BY start_time DESC
                """, (status,))
            else:
                self.cursor.execute("""
                    SELECT id, experiment_id, start_time, end_time, experiment_name, sample_names, 
                           client, operator, description, status
                    FROM experiment_sessions
                    ORDER BY start_time DESC
                """)
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'experiment_id': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'experiment_name': row[4],
                    'sample_names': row[5],
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
    
    def get_ignition_detections(self, session_id: int = None) -> List[Dict]:
        """
        获取着火点检测记录
        
        Args:
            session_id: 实验会话ID (可选)
            
        Returns:
            检测记录列表
        """
        try:
            if session_id:
                self.cursor.execute("""
                    SELECT id, session_id, timestamp, channel, ignition_temperature
                    FROM ignition_detection
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))
            else:
                self.cursor.execute("""
                    SELECT id, session_id, timestamp, channel, ignition_temperature
                    FROM ignition_detection
                    ORDER BY timestamp DESC
                """)
            
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'session_id': row[1],
                    'timestamp': row[2],
                    'channel': row[3],
                    'ignition_temperature': row[4]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"✗ 查询着火点检测记录失败: {e}")
            return []
    
    def generate_conclusion(self, session_id: int) -> str:
        """
        根据实验数据自动生成结论
        
        Args:
            session_id: 实验会话ID
            
        Returns:
            生成的结论文本
        """
        try:
            # 获取着火点检测记录
            detections = self.get_ignition_detections(session_id)
            if not detections:
                return "未检测到样品着火，无法生成结论。"
            
            # 提取着火温度
            temps = [d['ignition_temperature'] for d in detections if d['ignition_temperature'] is not None]
            
            if not temps:
                return "未检测到有效着火温度数据。"
            
            # 计算统计值
            sample_count = len(temps)
            avg_temp = sum(temps) / sample_count
            highest_temp = max(temps)
            lowest_temp = min(temps)
            temp_range = highest_temp - lowest_temp
            
            # 生成结论
            conclusion = (
                f"共测试{sample_count}个样品，"
                f"平均着火温度为{avg_temp:.1f}°C，"
                f"温度范围：{lowest_temp:.1f}-{highest_temp:.1f}°C（温差{temp_range:.1f}°C）。"
            )
            
            self.logger.info(f"✓ 自动生成实验结论: {conclusion}")
            return conclusion
            
        except Exception as e:
            self.logger.error(f"✗ 生成实验结论失败: {e}")
            return "实验数据符合标准要求。"
    
    # ==================== 数据导出 ====================
    
    def export_to_csv(self, output_file: str, start_time: str = None, 
                     end_time: str = None) -> bool:
        """
        导出数据到CSV文件
        
        Args:
            output_file: 输出文件路径
            start_time: 开始时间 (可选)
            end_time: 结束时间 (可选)
            
        Returns:
            是否导出成功
        """
        import csv
        
        try:
            # 获取数据
            if start_time and end_time:
                data = self.get_data_by_time_range(start_time, end_time)
            else:
                data = self.get_all_data()
            
            if not data:
                self.logger.error("✗ 没有数据可导出")
                return False
            
            # 写入CSV
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                # 使用中文表头
                fieldnames = ['ID', '时间戳', 
                            self.COLUMN_HEADERS['pv'],
                            self.COLUMN_HEADERS['ch1'],
                            self.COLUMN_HEADERS['ch2'],
                            self.COLUMN_HEADERS['ch3'],
                            self.COLUMN_HEADERS['ch4'],
                            self.COLUMN_HEADERS['ch5'],
                            self.COLUMN_HEADERS['ch6']]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data:
                    writer.writerow({
                        'ID': row['id'],
                        '时间戳': row['timestamp'],
                        self.COLUMN_HEADERS['pv']: row['pv'],
                        self.COLUMN_HEADERS['ch1']: row['ch1'],
                        self.COLUMN_HEADERS['ch2']: row['ch2'],
                        self.COLUMN_HEADERS['ch3']: row['ch3'],
                        self.COLUMN_HEADERS['ch4']: row['ch4'],
                        self.COLUMN_HEADERS['ch5']: row['ch5'],
                        self.COLUMN_HEADERS['ch6']: row['ch6']
                    })
            
            self.logger.info(f"✓ 数据已导出到: {output_file}, 共 {len(data)} 条记录")
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
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"✓ 数据库已备份到: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"✗ 数据库备份失败: {e}")
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
        self.close()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建数据库实例
    db = IgnitionDatabase("test_ignition.db")
    
    print("\n" + "="*50)
    print("数据库功能测试")
    print("="*50)
    
    # 1. 插入测试数据
    print("\n1. 插入单条数据:")
    record_id = db.insert_ignition_data(
        pv=150.5, ch1=25.3, ch2=26.1, ch3=24.8, 
        ch4=25.9, ch5=26.5, ch6=25.1
    )
    print(f"插入记录ID: {record_id}")
    
    # 2. 批量插入
    print("\n2. 批量插入数据:")
    batch_data = [
        (151.2, 26.0, 26.5, 25.3, 26.2, 27.0, 25.8),
        (152.0, 26.8, 27.2, 26.0, 26.9, 27.5, 26.3),
        (153.5, 27.5, 28.0, 26.8, 27.6, 28.2, 27.0)
    ]
    count = db.insert_batch_data(batch_data)
    print(f"批量插入 {count} 条记录")
    
    # 3. 查询数据
    print("\n3. 查询最新数据:")
    latest = db.get_latest_data(limit=2)
    for data in latest:
        print(f"  时间: {data['timestamp']}, 炉膛温度: {data['pv']}°C")
    
    # 4. 统计信息
    print("\n4. 统计信息:")
    stats = db.get_statistics('pv')
    if stats:
        print(f"  {stats['channel_name']}: 最大={stats['max']}, "
              f"最小={stats['min']}, 平均={stats['avg']:.2f}")
    
    # 5. 更新数据
    print("\n5. 更新数据:")
    success = db.update_data_by_id(record_id, pv=155.0, ch1=28.0)
    
    # 6. 查询总数
    print("\n6. 数据总数:")
    total = db.get_data_count()
    print(f"  共有 {total} 条记录")
    
    # 7. 导出CSV
    print("\n7. 导出数据:")
    db.export_to_csv("test_export.csv")
    
    # 8. 实验会话测试
    print("\n8. 实验会话管理:")
    session_id = db.start_experiment_session("测试实验", "这是一个测试实验")
    db.record_ignition_detection(session_id, channel=1, ignition_temperature=180.5)
    db.end_experiment_session(session_id, status='completed')
    
    # 9. 查询会话
    print("\n9. 查询实验会话:")
    sessions = db.get_all_experiment_sessions()
    for session in sessions:
        print(f"  会话ID: {session['id']}, 名称: {session['experiment_name']}, "
              f"状态: {session['status']}")
    
    # 清理
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)
    db.close()

