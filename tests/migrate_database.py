#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
根据更新后的数据库字段，对原始数据库进行迁移重建
"""

import os
import sys
import sqlite3
import shutil
import re
from datetime import datetime
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.explosion_database import ExplosionDatabase
from models.ignition_database import IgnitionDatabase


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, data_dir="data"):
        """
        初始化迁移器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件路径
        self.explosion_db_path = self.data_dir / "explosion_experiment.db"
        self.ignition_db_path = self.data_dir / "ignition_experiment.db"
        
        print(f"数据目录: {self.data_dir}")
        print(f"备份目录: {self.backup_dir}")
    
    def backup_database(self, db_path: Path) -> Path:
        """
        备份数据库文件
        
        Args:
            db_path: 数据库文件路径
            
        Returns:
            备份文件路径
        """
        if not db_path.exists():
            print(f"⚠ 数据库文件不存在: {db_path}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✓ 已备份数据库: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"✗ 备份数据库失败: {e}")
            return None
    
    def get_table_columns(self, cursor, table_name):
        """获取表的列信息"""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        return {col[1]: i for i, col in enumerate(columns_info)}
    
    def extract_experiment_id(self, experiment_name):
        """
        从 experiment_name 中提取实验编号
        
        Args:
            experiment_name: 实验名称字符串，可能格式：
                - "实验编号：EXP-20251205-094357 | 委托单位：..."
                - "IGN-20241201-001" (直接就是实验编号)
                - "EXP-20251205-094357" (直接就是实验编号)
            
        Returns:
            提取的实验编号，如 "EXP-20251205-094357" 或 "IGN-20241201-001"，如果提取失败返回 None
        """
        if not experiment_name:
            return None
        
        # 首先检查是否整个字符串就是实验编号格式（EXP- 或 IGN- 开头）
        direct_pattern = r'^([A-Z]{2,4}-\d{8}-\d{3,6})$'
        direct_match = re.match(direct_pattern, experiment_name.strip())
        if direct_match:
            return direct_match.group(1)
        
        # 尝试匹配实验编号格式：实验编号：EXP-YYYYMMDD-HHMMSS 或 实验编号：IGN-YYYYMMDD-NNN
        pattern1 = r'实验编号[：:]\s*([A-Z]{2,4}-\d{8}-\d{3,6})'
        match1 = re.search(pattern1, experiment_name)
        if match1:
            return match1.group(1)
        
        # 如果没有匹配到，尝试直接匹配 EXP- 或 IGN- 开头的格式
        pattern2 = r'([A-Z]{2,4}-\d{8}-\d{3,6})'
        match2 = re.search(pattern2, experiment_name)
        if match2:
            return match2.group(1)
        
        # 如果都没有匹配到，返回 None
        return None
    
    def migrate_explosion_database(self):
        """迁移爆炸性实验数据库"""
        print("\n" + "="*60)
        print("开始迁移爆炸性实验数据库")
        print("="*60)
        
        if not self.explosion_db_path.exists():
            print(f"⚠ 数据库文件不存在: {self.explosion_db_path}")
            return False
        
        # 备份数据库
        backup_path = self.backup_database(self.explosion_db_path)
        if not backup_path:
            print("✗ 备份失败，取消迁移")
            return False
        
        try:
            # 连接旧数据库
            old_conn = sqlite3.connect(self.explosion_db_path)
            old_cursor = old_conn.cursor()
            
            # 获取表结构
            sessions_cols = self.get_table_columns(old_cursor, "experiment_sessions")
            rounds_cols = self.get_table_columns(old_cursor, "test_rounds")
            results_cols = self.get_table_columns(old_cursor, "experiment_results")
            
            print(f"\n旧表结构:")
            print(f"  experiment_sessions: {list(sessions_cols.keys())}")
            print(f"  test_rounds: {list(rounds_cols.keys())}")
            print(f"  experiment_results: {list(results_cols.keys())}")
            
            # 读取所有数据 - 使用 SELECT * 确保获取所有字段
            old_cursor.execute("SELECT * FROM experiment_sessions ORDER BY id")
            sessions_data = old_cursor.fetchall()
            print(f"\n✓ 读取到 {len(sessions_data)} 条会话记录")
            
            old_cursor.execute("SELECT * FROM test_rounds ORDER BY session_id, round_number")
            rounds_data = old_cursor.fetchall()
            print(f"✓ 读取到 {len(rounds_data)} 条测试轮次记录")
            
            old_cursor.execute("SELECT * FROM experiment_results ORDER BY session_id")
            results_data = old_cursor.fetchall()
            print(f"✓ 读取到 {len(results_data)} 条实验结果记录")
            
            old_conn.close()
            
            # 创建新数据库
            temp_db_path = self.data_dir / "explosion_experiment_new.db"
            if temp_db_path.exists():
                temp_db_path.unlink()
            
            new_db = ExplosionDatabase(str(temp_db_path))
            
            # 迁移数据
            session_id_mapping = {}  # 旧ID -> 新ID映射
            
            # 迁移会话数据
            print("\n迁移会话数据...")
            for old_row in sessions_data:
                # 构建字段字典
                session_dict = {}
                for col_name, col_idx in sessions_cols.items():
                    if col_idx < len(old_row):
                        session_dict[col_name] = old_row[col_idx]
                
                old_id = session_dict.get('id')
                
                # 处理 experiment_id：优先使用旧表的 experiment_id，如果没有则从 experiment_name 中提取
                experiment_id = session_dict.get('experiment_id')
                experiment_name = session_dict.get('experiment_name', '')
                
                if not experiment_id and experiment_name:
                    experiment_id = self.extract_experiment_id(experiment_name)
                    if experiment_id:
                        print(f"  从 experiment_name 提取实验编号: {experiment_id} (原始值: {experiment_name[:50]}...)")
                    else:
                        print(f"  ⚠ 无法从 experiment_name 提取实验编号: {experiment_name[:50]}...")
                
                # 插入新数据库
                new_db.cursor.execute("""
                    INSERT INTO experiment_sessions 
                    (experiment_id, start_time, end_time, experiment_name, 
                     sample_name, client, operator, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    experiment_id,
                    session_dict.get('start_time'),
                    session_dict.get('end_time'),
                    session_dict.get('experiment_name'),
                    session_dict.get('sample_name'),
                    session_dict.get('client'),
                    session_dict.get('operator'),
                    session_dict.get('description'),
                    session_dict.get('status', 'running')
                ))
                new_db.conn.commit()
                
                new_id = new_db.cursor.lastrowid
                session_id_mapping[old_id] = new_id
                
                if len(session_id_mapping) % 10 == 0:
                    print(f"  已迁移 {len(session_id_mapping)} 条会话...")
            
            print(f"✓ 已迁移 {len(session_id_mapping)} 条会话记录")
            
            # 迁移测试轮次数据
            print("\n迁移测试轮次数据...")
            migrated_rounds = 0
            for old_row in rounds_data:
                # 构建字段字典
                round_dict = {}
                for col_name, col_idx in rounds_cols.items():
                    if col_idx < len(old_row):
                        round_dict[col_name] = old_row[col_idx]
                
                old_session_id = round_dict.get('session_id')
                new_session_id = session_id_mapping.get(old_session_id)
                
                if not new_session_id:
                    print(f"⚠ 警告: 会话ID {old_session_id} 不存在映射，跳过轮次 ID {round_dict.get('id')}")
                    continue
                
                new_db.cursor.execute("""
                    INSERT INTO test_rounds 
                    (session_id, round_number, flame_length, max_flame_image_path, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_session_id,
                    round_dict.get('round_number'),
                    round_dict.get('flame_length'),
                    round_dict.get('max_flame_image_path'),
                    round_dict.get('timestamp')
                ))
                migrated_rounds += 1
                
                if migrated_rounds % 50 == 0:
                    print(f"  已迁移 {migrated_rounds} 条轮次...")
            
            new_db.conn.commit()
            print(f"✓ 已迁移 {migrated_rounds} 条测试轮次记录")
            
            # 迁移实验结果数据
            print("\n迁移实验结果数据...")
            migrated_results = 0
            for old_row in results_data:
                # 构建字段字典
                result_dict = {}
                for col_name, col_idx in results_cols.items():
                    if col_idx < len(old_row):
                        result_dict[col_name] = old_row[col_idx]
                
                old_session_id = result_dict.get('session_id')
                new_session_id = session_id_mapping.get(old_session_id)
                
                if not new_session_id:
                    print(f"⚠ 警告: 会话ID {old_session_id} 不存在映射，跳过结果 ID {result_dict.get('id')}")
                    continue
                
                new_db.cursor.execute("""
                    INSERT INTO experiment_results 
                    (session_id, total_rounds, avg_flame_length, explosion_level, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_session_id,
                    result_dict.get('total_rounds'),
                    result_dict.get('avg_flame_length'),
                    result_dict.get('explosion_level'),
                    result_dict.get('timestamp')
                ))
                migrated_results += 1
            
            new_db.conn.commit()
            print(f"✓ 已迁移 {migrated_results} 条实验结果记录")
            
            new_db.close()
            
            # 替换旧数据库
            old_backup = self.data_dir / "explosion_experiment_old.db"
            if old_backup.exists():
                old_backup.unlink()
            
            self.explosion_db_path.rename(old_backup)
            temp_db_path.rename(self.explosion_db_path)
            
            print(f"\n✓ 爆炸性实验数据库迁移完成")
            print(f"  旧数据库备份: {old_backup}")
            print(f"  新数据库: {self.explosion_db_path}")
            print(f"  迁移统计: 会话={len(session_id_mapping)}, 轮次={migrated_rounds}, 结果={migrated_results}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def migrate_ignition_database(self):
        """迁移着火点实验数据库"""
        print("\n" + "="*60)
        print("开始迁移着火点实验数据库")
        print("="*60)
        
        if not self.ignition_db_path.exists():
            print(f"⚠ 数据库文件不存在: {self.ignition_db_path}")
            return False
        
        # 备份数据库
        backup_path = self.backup_database(self.ignition_db_path)
        if not backup_path:
            print("✗ 备份失败，取消迁移")
            return False
        
        try:
            # 连接旧数据库
            old_conn = sqlite3.connect(self.ignition_db_path)
            old_cursor = old_conn.cursor()
            
            # 检查表是否存在
            old_cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='experiment_sessions'
            """)
            if not old_cursor.fetchone():
                print("⚠ 表 experiment_sessions 不存在，跳过迁移")
                old_conn.close()
                return False
            
            # 获取表结构
            sessions_cols = self.get_table_columns(old_cursor, "experiment_sessions")
            realtime_cols = self.get_table_columns(old_cursor, "ignition_realtime_data")
            
            # 检查 ignition_detection 表是否存在
            old_cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='ignition_detection'
            """)
            detection_exists = old_cursor.fetchone() is not None
            detection_cols = {}
            if detection_exists:
                detection_cols = self.get_table_columns(old_cursor, "ignition_detection")
            
            print(f"\n旧表结构:")
            print(f"  experiment_sessions: {list(sessions_cols.keys())}")
            print(f"  ignition_realtime_data: {list(realtime_cols.keys())}")
            if detection_exists:
                print(f"  ignition_detection: {list(detection_cols.keys())}")
            
            # 读取所有数据 - 使用 SELECT * 确保获取所有字段
            old_cursor.execute("SELECT * FROM experiment_sessions ORDER BY id")
            sessions_data = old_cursor.fetchall()
            print(f"\n✓ 读取到 {len(sessions_data)} 条会话记录")
            
            old_cursor.execute("SELECT * FROM ignition_realtime_data ORDER BY timestamp")
            realtime_data = old_cursor.fetchall()
            print(f"✓ 读取到 {len(realtime_data)} 条实时数据记录")
            
            detection_data = []
            if detection_exists:
                old_cursor.execute("SELECT * FROM ignition_detection ORDER BY id")
                detection_data = old_cursor.fetchall()
                print(f"✓ 读取到 {len(detection_data)} 条着火点检测记录")
            
            old_conn.close()
            
            # 创建新数据库
            temp_db_path = self.data_dir / "ignition_experiment_new.db"
            if temp_db_path.exists():
                temp_db_path.unlink()
            
            new_db = IgnitionDatabase(str(temp_db_path))
            
            # 迁移数据
            session_id_mapping = {}  # 旧ID -> 新ID映射
            
            # 迁移会话数据
            print("\n迁移会话数据...")
            for old_row in sessions_data:
                # 构建字段字典
                session_dict = {}
                for col_name, col_idx in sessions_cols.items():
                    if col_idx < len(old_row):
                        session_dict[col_name] = old_row[col_idx]
                
                old_id = session_dict.get('id')
                
                # 处理 experiment_id：优先使用旧表的 experiment_id，如果没有则从 experiment_name 中提取
                experiment_id = session_dict.get('experiment_id')
                experiment_name = session_dict.get('experiment_name', '')
                
                if not experiment_id and experiment_name:
                    experiment_id = self.extract_experiment_id(experiment_name)
                    if experiment_id:
                        print(f"  从 experiment_name 提取实验编号: {experiment_id} (原始值: {experiment_name[:50]}...)")
                    else:
                        print(f"  ⚠ 无法从 experiment_name 提取实验编号: {experiment_name[:50]}...")
                
                # 处理 sample_name -> sample_names (兼容旧数据)
                sample_names = session_dict.get('sample_names')
                if not sample_names and 'sample_name' in session_dict:
                    sample_names = session_dict.get('sample_name')
                
                # 插入新数据库
                new_db.cursor.execute("""
                    INSERT INTO experiment_sessions 
                    (experiment_id, start_time, end_time, experiment_name, 
                     sample_names, client, operator, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    experiment_id,
                    session_dict.get('start_time'),
                    session_dict.get('end_time'),
                    session_dict.get('experiment_name'),
                    sample_names,
                    session_dict.get('client'),
                    session_dict.get('operator'),
                    session_dict.get('description'),
                    session_dict.get('status', 'running')
                ))
                new_db.conn.commit()
                
                new_id = new_db.cursor.lastrowid
                session_id_mapping[old_id] = new_id
                
                if len(session_id_mapping) % 10 == 0:
                    print(f"  已迁移 {len(session_id_mapping)} 条会话...")
            
            print(f"✓ 已迁移 {len(session_id_mapping)} 条会话记录")
            
            # 迁移实时数据
            print("\n迁移实时数据...")
            migrated_realtime = 0
            
            for old_row in realtime_data:
                # 构建字段字典
                data_dict = {}
                for col_name, col_idx in realtime_cols.items():
                    if col_idx < len(old_row):
                        data_dict[col_name] = old_row[col_idx]
                
                old_session_id = data_dict.get('session_id')
                new_session_id = session_id_mapping.get(old_session_id) if old_session_id else None
                
                # 如果没有session_id，尝试通过时间范围匹配
                if not new_session_id:
                    timestamp = data_dict.get('timestamp')
                    if timestamp:
                        # 查找时间匹配的会话
                        old_conn_temp = sqlite3.connect(self.ignition_db_path)
                        old_cursor_temp = old_conn_temp.cursor()
                        for old_sess_id, new_sess_id in session_id_mapping.items():
                            old_cursor_temp.execute("""
                                SELECT start_time, end_time 
                                FROM experiment_sessions 
                                WHERE id = ?
                            """, (old_sess_id,))
                            sess_time = old_cursor_temp.fetchone()
                            if sess_time:
                                start_time = sess_time[0]
                                end_time = sess_time[1] or timestamp
                                if start_time <= timestamp <= end_time:
                                    new_session_id = new_sess_id
                                    break
                        old_conn_temp.close()
                
                new_db.cursor.execute("""
                    INSERT INTO ignition_realtime_data 
                    (session_id, timestamp, pv, ch1, ch2, ch3, ch4, ch5, ch6)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_session_id,
                    data_dict.get('timestamp'),
                    data_dict.get('pv'),
                    data_dict.get('ch1'),
                    data_dict.get('ch2'),
                    data_dict.get('ch3'),
                    data_dict.get('ch4'),
                    data_dict.get('ch5'),
                    data_dict.get('ch6')
                ))
                migrated_realtime += 1
                
                if migrated_realtime % 1000 == 0:
                    print(f"  已迁移 {migrated_realtime} 条实时数据...")
            
            new_db.conn.commit()
            print(f"✓ 已迁移 {migrated_realtime} 条实时数据记录")
            
            # 迁移着火点检测数据
            if detection_data:
                print("\n迁移着火点检测数据...")
                migrated_detection = 0
                
                for old_row in detection_data:
                    # 构建字段字典
                    detection_dict = {}
                    for col_name, col_idx in detection_cols.items():
                        if col_idx < len(old_row):
                            detection_dict[col_name] = old_row[col_idx]
                    
                    old_session_id = detection_dict.get('session_id')
                    new_session_id = session_id_mapping.get(old_session_id)
                    
                    if not new_session_id:
                        print(f"⚠ 警告: 会话ID {old_session_id} 不存在映射，跳过检测记录 ID {detection_dict.get('id')}")
                        continue
                    
                    # 处理字段映射
                    detection_method = detection_dict.get('detection_method', 'realtime')
                    image_path = detection_dict.get('tangent_analysis_image_path') or detection_dict.get('image_path')
                    
                    new_db.cursor.execute("""
                        INSERT INTO ignition_detection 
                        (session_id, timestamp, channel, ignition_temperature, 
                         detection_method, tangent_analysis_image_path)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        new_session_id,
                        detection_dict.get('timestamp'),
                        detection_dict.get('channel'),
                        detection_dict.get('ignition_temperature'),
                        detection_method,
                        image_path
                    ))
                    migrated_detection += 1
                
                new_db.conn.commit()
                print(f"✓ 已迁移 {migrated_detection} 条着火点检测记录")
            
            new_db.close()
            
            # 替换旧数据库
            old_backup = self.data_dir / "ignition_experiment_old.db"
            if old_backup.exists():
                old_backup.unlink()
            
            self.ignition_db_path.rename(old_backup)
            temp_db_path.rename(self.ignition_db_path)
            
            print(f"\n✓ 着火点实验数据库迁移完成")
            print(f"  旧数据库备份: {old_backup}")
            print(f"  新数据库: {self.ignition_db_path}")
            print(f"  迁移统计: 会话={len(session_id_mapping)}, 实时数据={migrated_realtime}, 检测记录={len(detection_data) if detection_data else 0}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_migration(self):
        """验证迁移结果"""
        print("\n" + "="*60)
        print("验证迁移结果")
        print("="*60)
        
        # 验证爆炸性数据库
        if self.explosion_db_path.exists():
            try:
                db = ExplosionDatabase(str(self.explosion_db_path))
                stats = db.get_statistics()
                if stats:
                    print(f"\n爆炸性数据库统计:")
                    print(f"  总会话数: {stats.get('total_sessions', 0)}")
                    print(f"  各状态会话: {stats.get('sessions_by_status', {})}")
                    print(f"  各爆炸性等级: {stats.get('results_by_level', {})}")
                
                # 验证数据完整性
                sessions = db.get_all_experiment_sessions()
                print(f"  会话记录数: {len(sessions)}")
                
                if sessions:
                    sample_session = sessions[0]
                    rounds = db.get_session_test_rounds(sample_session['id'])
                    print(f"  示例会话 {sample_session['id']} 的轮次数: {len(rounds)}")
                
                db.close()
            except Exception as e:
                print(f"✗ 验证爆炸性数据库失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 验证着火点数据库
        if self.ignition_db_path.exists():
            try:
                db = IgnitionDatabase(str(self.ignition_db_path))
                sessions = db.get_all_experiment_sessions()
                data_count = db.get_data_count()
                print(f"\n着火点数据库统计:")
                print(f"  总会话数: {len(sessions)}")
                print(f"  实时数据记录数: {data_count}")
                
                if sessions:
                    sample_session = sessions[0]
                    detections = db.get_ignition_detections(sample_session['id'])
                    print(f"  示例会话 {sample_session['id']} 的检测记录数: {len(detections)}")
                
                db.close()
            except Exception as e:
                print(f"✗ 验证着火点数据库失败: {e}")
                import traceback
                traceback.print_exc()
    
    def migrate_all(self):
        """迁移所有数据库"""
        print("\n" + "="*80)
        print("数据库迁移工具")
        print("="*80)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        success_count = 0
        
        # 迁移爆炸性数据库
        if self.explosion_db_path.exists():
            if self.migrate_explosion_database():
                success_count += 1
        else:
            print(f"\n⚠ 爆炸性数据库文件不存在: {self.explosion_db_path}")
        
        # 迁移着火点数据库
        if self.ignition_db_path.exists():
            if self.migrate_ignition_database():
                success_count += 1
        else:
            print(f"\n⚠ 着火点数据库文件不存在: {self.ignition_db_path}")
        
        # 验证迁移结果
        if success_count > 0:
            self.verify_migration()
        
        print("\n" + "="*80)
        print(f"迁移完成！成功迁移 {success_count} 个数据库")
        print("="*80)
        print("\n注意: 旧数据库已备份到 data/backups/ 目录")
        print("      旧数据库文件已重命名为 *_old.db")


if __name__ == "__main__":
    migrator = DatabaseMigrator()
    migrator.migrate_all()
