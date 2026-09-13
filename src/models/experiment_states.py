#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验状态枚举模块
定义爆炸性和着火点实验的状态枚举，统一管理实验状态流转
"""

from enum import Enum
from typing import Optional, Set


class ExplosionExperimentState(Enum):
    """爆炸性实验状态枚举"""
    
    # 初始状态
    IDLE = "idle"  # 未连接设备
    
    # 设备连接状态
    CONNECTED = "connected"  # 设备已连接
    
    # 实验会话状态
    SESSION_CREATED = "session_created"  # 实验会话已创建
    SEQUENCE_RUNNING = "sequence_running"  # 时序控制运行中
    WAITING_ANALYSIS = "waiting_analysis"  # 等待火焰分析
    COMPLETED = "completed"  # 实验完成
    CANCELLED = "cancelled"  # 实验取消
    ERROR = "error"  # 实验错误
    
    def description(self) -> str:
        """获取状态描述"""
        descriptions = {
            self.IDLE: "未连接设备",
            self.CONNECTED: "设备已连接",
            self.SESSION_CREATED: "实验会话已创建",
            self.SEQUENCE_RUNNING: "时序控制运行中",
            self.WAITING_ANALYSIS: "等待火焰分析",
            self.COMPLETED: "实验完成",
            self.CANCELLED: "实验取消",
            self.ERROR: "实验错误"
        }
        return descriptions.get(self, "未知状态")
    
    def display_text(self) -> str:
        """获取UI显示文本"""
        display_texts = {
            self.IDLE: "状态: 未连接",
            self.CONNECTED: "状态: 已连接",
            self.SESSION_CREATED: "状态: 实验已创建",
            self.SEQUENCE_RUNNING: "状态: 实验中",
            self.WAITING_ANALYSIS: "状态: 等待分析",
            self.COMPLETED: "状态: 实验完成",
            self.CANCELLED: "状态: 已取消",
            self.ERROR: "状态: 错误"
        }
        return display_texts.get(self, "状态: 未知")
    
    def color(self) -> str:
        """获取UI显示颜色"""
        colors = {
            self.IDLE: "#999999",
            self.CONNECTED: "#4caf50",
            self.SESSION_CREATED: "#2196F3",
            self.SEQUENCE_RUNNING: "#ff9800",
            self.WAITING_ANALYSIS: "#ff9800",
            self.COMPLETED: "#4caf50",
            self.CANCELLED: "#999999",
            self.ERROR: "#f44336"
        }
        return colors.get(self, "#999999")
    
    def to_db_status(self) -> str:
        """转换为数据库状态字符串"""
        # 映射到数据库中的status字段值
        db_status_map = {
            self.IDLE: None,  # 未连接时没有数据库记录
            self.CONNECTED: None,  # 连接状态不存储在数据库
            self.SESSION_CREATED: "running",  # 创建会话时默认状态为running
            self.SEQUENCE_RUNNING: "running",
            self.WAITING_ANALYSIS: "running",  # 等待分析时仍为running
            self.COMPLETED: "completed",
            self.CANCELLED: "cancelled",
            self.ERROR: "error"
        }
        return db_status_map.get(self)
    
    @classmethod
    def from_db_status(cls, db_status: Optional[str]) -> 'ExplosionExperimentState':
        """从数据库状态字符串创建枚举"""
        if db_status is None:
            return cls.IDLE
        
        status_map = {
            "running": cls.SESSION_CREATED,  # 默认映射到SESSION_CREATED
            "completed": cls.COMPLETED,
            "cancelled": cls.CANCELLED,
            "error": cls.ERROR
        }
        return status_map.get(db_status, cls.IDLE)
    
    def can_transition_to(self, new_state: 'ExplosionExperimentState') -> bool:
        """检查是否可以转换到新状态"""
        # 定义合法的状态转换规则
        valid_transitions: dict[ExplosionExperimentState, Set[ExplosionExperimentState]] = {
            self.IDLE: {self.CONNECTED},
            self.CONNECTED: {self.IDLE, self.SESSION_CREATED},
            # SESSION_CREATED 允许直接完成实验（can_finalize 包含该状态，且轮次结束后页面会回到该状态）
            self.SESSION_CREATED: {self.SEQUENCE_RUNNING, self.COMPLETED, self.CANCELLED, self.ERROR},
            # 用户在时序运行中主动停止时回到 SESSION_CREATED，以便重试本轮或完成实验
            self.SEQUENCE_RUNNING: {self.WAITING_ANALYSIS, self.SESSION_CREATED, self.CANCELLED, self.ERROR},
            self.WAITING_ANALYSIS: {self.SEQUENCE_RUNNING, self.SESSION_CREATED, self.COMPLETED, self.CANCELLED, self.ERROR},
            self.COMPLETED: {self.CONNECTED, self.SESSION_CREATED},  # 完成状态可以直接创建新实验，或回到连接状态
            self.CANCELLED: set(),  # 取消状态是终态
            self.ERROR: {self.SESSION_CREATED, self.CANCELLED}  # 错误后可以重试或取消
        }
        
        allowed_states = valid_transitions.get(self, set())
        return new_state in allowed_states
    
    def is_running(self) -> bool:
        """检查是否处于运行状态"""
        return self in {self.SEQUENCE_RUNNING, self.WAITING_ANALYSIS}
    
    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self in {self.COMPLETED, self.CANCELLED}
    
    def can_start(self) -> bool:
        """检查是否可以启动实验"""
        return self == self.SESSION_CREATED
    
    def can_stop(self) -> bool:
        """检查是否可以停止实验"""
        return self in {self.SEQUENCE_RUNNING, self.WAITING_ANALYSIS}
    
    def can_create_experiment(self) -> bool:
        """检查是否可以创建实验"""
        return self in {self.CONNECTED, self.COMPLETED}  # 连接状态或完成状态都可以创建新实验
    
    def can_finalize(self) -> bool:
        """检查是否可以完成实验"""
        return self in {self.SESSION_CREATED, self.WAITING_ANALYSIS}


class IgnitionExperimentState(Enum):
    """着火点实验状态枚举"""
    
    # 初始状态
    IDLE = "idle"  # 未连接设备
    
    # 设备连接状态
    CONNECTED = "connected"  # 设备已连接
    
    # 实验会话状态
    PREPARED = "prepared"  # 实验已准备
    RUNNING = "running"  # 实验运行中
    STOPPED = "stopped"  # 实验已停止
    COMPLETED = "completed"  # 实验完成
    CANCELLED = "cancelled"  # 实验取消
    ERROR = "error"  # 实验错误
    
    def description(self) -> str:
        """获取状态描述"""
        descriptions = {
            self.IDLE: "未连接设备",
            self.CONNECTED: "设备已连接",
            self.PREPARED: "实验已准备",
            self.RUNNING: "实验运行中",
            self.STOPPED: "实验已停止",
            self.COMPLETED: "实验完成",
            self.CANCELLED: "实验取消",
            self.ERROR: "实验错误"
        }
        return descriptions.get(self, "未知状态")
    
    def display_text(self) -> str:
        """获取UI显示文本"""
        display_texts = {
            self.IDLE: "状态: 未连接",
            self.CONNECTED: "状态: 已连接",
            self.PREPARED: "状态: 实验已准备",
            self.RUNNING: "状态: 实验中",
            self.STOPPED: "状态: 已停止",
            self.COMPLETED: "状态: 实验完成",
            self.CANCELLED: "状态: 已取消",
            self.ERROR: "状态: 错误"
        }
        return display_texts.get(self, "状态: 未知")
    
    def color(self) -> str:
        """获取UI显示颜色"""
        colors = {
            self.IDLE: "#999999",
            self.CONNECTED: "#4caf50",
            self.PREPARED: "#2196F3",
            self.RUNNING: "#ff9800",
            self.STOPPED: "#999999",
            self.COMPLETED: "#4caf50",
            self.CANCELLED: "#999999",
            self.ERROR: "#f44336"
        }
        return colors.get(self, "#999999")
    
    def to_db_status(self) -> str:
        """转换为数据库状态字符串"""
        # 映射到数据库中的status字段值
        db_status_map = {
            self.IDLE: None,
            self.CONNECTED: None,
            self.PREPARED: "prepared",
            self.RUNNING: "running",
            self.STOPPED: "completed",  # 停止时数据库状态为completed
            self.COMPLETED: "completed",
            self.CANCELLED: "cancelled",
            self.ERROR: "error"
        }
        return db_status_map.get(self)
    
    @classmethod
    def from_db_status(cls, db_status: Optional[str]) -> 'IgnitionExperimentState':
        """从数据库状态字符串创建枚举"""
        if db_status is None:
            return cls.IDLE
        
        status_map = {
            "prepared": cls.PREPARED,
            "running": cls.RUNNING,
            "completed": cls.STOPPED,  # 数据库的completed对应STOPPED状态
            "cancelled": cls.CANCELLED,
            "error": cls.ERROR
        }
        return status_map.get(db_status, cls.IDLE)
    
    def can_transition_to(self, new_state: 'IgnitionExperimentState') -> bool:
        """检查是否可以转换到新状态"""
        # 定义合法的状态转换规则
        valid_transitions: dict[IgnitionExperimentState, Set[IgnitionExperimentState]] = {
            self.IDLE: {self.CONNECTED},
            self.CONNECTED: {self.IDLE, self.PREPARED},
            self.PREPARED: {self.RUNNING, self.CANCELLED, self.ERROR},
            self.RUNNING: {self.STOPPED, self.CANCELLED, self.ERROR},
            self.STOPPED: {self.COMPLETED, self.CANCELLED, self.CONNECTED},  # 停止后只能完成或重置，不能继续运行
            self.COMPLETED: {self.CONNECTED},  # 完成状态可以重置为连接状态，以便创建新实验
            self.CANCELLED: set(),  # 取消状态是终态
            self.ERROR: {self.PREPARED, self.CANCELLED}  # 错误后可以重试或取消
        }
        
        allowed_states = valid_transitions.get(self, set())
        return new_state in allowed_states
    
    def is_running(self) -> bool:
        """检查是否处于运行状态"""
        return self == self.RUNNING
    
    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self in {self.COMPLETED, self.CANCELLED}
    
    def can_start(self) -> bool:
        """检查是否可以启动实验"""
        return self == self.PREPARED  # 只有准备状态可以启动，停止后不能继续运行
    
    def can_stop(self) -> bool:
        """检查是否可以停止实验"""
        return self == self.RUNNING
    
    def can_create_experiment(self) -> bool:
        """检查是否可以创建实验"""
        return self in {self.CONNECTED, self.COMPLETED}  # 只有连接状态或完成状态可以创建新实验，停止状态必须先完成实验
    
    def can_finalize(self) -> bool:
        """检查是否可以完成实验"""
        return self in {self.STOPPED, self.RUNNING}  # 停止状态或运行状态都可以完成实验
