"""
着火点实验详情卡片组件
显示着火点实验的完整信息，包括基本信息、样品详情、测试结果等
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Signal

# 导入基类
from src.views.ui_components.base_detail_card import BaseDetailCard


class IgnitionDetailCard(BaseDetailCard):
    """
    着火点实验详情卡片
    专门用于显示着火点实验的详细信息
    """
    
    # 新增信号
    tangent_analysis_requested = Signal()  # 请求切线法分析
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 存储实验ID，用于切线法分析
        self.current_experiment_id = None
    
    def create_button_area(self) -> QWidget:
        """创建底部按钮区域（重写以添加切线法分析按钮）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border-top: 1px solid rgba(0, 217, 255, 0.2);
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        layout.addStretch()
        
        # 切线法分析按钮
        self.tangent_btn = QPushButton("🔬 切线法分析复核着火点")
        self.tangent_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #9c27b0,
                    stop: 1 #673ab7
                );
                border: none;
                color: #fff;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ab47bc,
                    stop: 1 #7e57c2
                );
            }
        """)
        self.tangent_btn.clicked.connect(self.tangent_analysis_requested.emit)
        layout.addWidget(self.tangent_btn)
        
        # 生成报告按钮
        self.report_btn = QPushButton("📄 生成报告")
        self.report_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #000;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00e8ff,
                    stop: 1 #00a8d0
                );
            }
        """)
        self.report_btn.clicked.connect(self.generate_report_requested.emit)
        layout.addWidget(self.report_btn)
        
        layout.addStretch()
        
        return widget
    
    def load_experiment_detail(self, exp_id: int, exp_data: Dict, ignition_db=None):
        """
        加载着火点实验详情
        Args:
            exp_id: 实验ID
            exp_data: 实验数据字典
            ignition_db: 着火点实验数据库实例
        """
        self.experiment_data = exp_data
        self.current_experiment_id = exp_id  # 保存实验ID，用于切线法分析
        
        # 清空现有内容
        self.clear_content()
        
        # 如果没有结论，自动生成
        if not exp_data.get('conclusion') and ignition_db:
            try:
                exp_data['conclusion'] = ignition_db.generate_conclusion(exp_id)
            except Exception:
                pass  # 生成失败时使用默认值或不显示
        
        # 显示着火点实验详情
        self.show_ignition_detail(exp_data)
        
        # 显示按钮区域
        self.button_widget.setVisible(True)
    
    # ==================== 着火点实验详情 ====================
    
    def show_ignition_detail(self, data: Dict):
        """显示着火点实验详情"""
        # 标题区域
        title_section = self.create_title_section(
            data.get('experiment_code', 'N/A'),
            "🔥 着火点检测实验"
        )
        self.content_layout.addWidget(title_section)
        
        # 基本信息
        samples = data.get('samples', [])
        valid_samples = [s for s in samples if s.get('name')]
        
        basic_info = self.create_info_section(
            "📋 基本信息",
            [
                ("检测人员", data.get('inspector', 'N/A'), "#00d9ff"),
                ("委托单位", data.get('client_organization', 'N/A'), "#aaa"),
                ("样品数量", f"{len(valid_samples)} 个", "#aaa"),
            ]
        )
        self.content_layout.addWidget(basic_info)
        
        # 统计结果
        avg_temp = data.get('avg_ignition_temperature')
        highest_temp = data.get('highest_ignition_temp')
        lowest_temp = data.get('lowest_ignition_temp')
        
        stats_items = []
        if avg_temp is not None:
            stats_items.append(("平均着火温度", f"{avg_temp:.1f} °C", "#00ff00"))
        if highest_temp is not None:
            stats_items.append(("最高温度", f"{highest_temp:.1f} °C", "#ff5555"))
        if lowest_temp is not None:
            stats_items.append(("最低温度", f"{lowest_temp:.1f} °C", "#5555ff"))
        
        if stats_items:
            # 计算温差
            if highest_temp and lowest_temp:
                temp_range = highest_temp - lowest_temp
                stats_items.append(("温度范围", f"{temp_range:.1f} °C", "#ff9800"))
            
            stats_info = self.create_info_section("📊 统计结果", stats_items)
            self.content_layout.addWidget(stats_info)
        
        # 样品详情（增强版）
        if samples and 'sample_data' in data:
            samples_section = self.create_ignition_samples_section(
                samples, 
                data.get('sample_data', [])
            )
            self.content_layout.addWidget(samples_section)
        elif samples:
            # 如果没有sample_data，使用简化版
            samples_section = self.create_samples_section(samples)
            self.content_layout.addWidget(samples_section)
        
        # 时间信息
        time_items = []
        if data.get('start_time'):
            time_str = data['start_time'][:19] if len(data['start_time']) > 19 else data['start_time']
            time_items.append(("开始时间", time_str, "#aaa"))
        if data.get('end_time'):
            time_str = data['end_time'][:19] if len(data['end_time']) > 19 else data['end_time']
            time_items.append(("结束时间", time_str, "#aaa"))
        
        if time_items:
            time_info = self.create_info_section("⏰ 时间记录", time_items)
            self.content_layout.addWidget(time_info)
        
        # 实验结论
        if data.get('conclusion'):
            conclusion_section = self.create_description_section(
                "实验结论",
                data.get('conclusion')
            )
            self.content_layout.addWidget(conclusion_section)
        
        # 备注
        if data.get('notes'):
            note_section = self.create_note_section(data.get('notes'))
            self.content_layout.addWidget(note_section)
        
        self.content_layout.addStretch()
    
    def create_samples_section(self, samples: list) -> QWidget:
        """创建样品详情区域（紧凑2列布局）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("🧪 样品详情")
        title_label.setStyleSheet("color: #00d9ff; font-size: 11px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: rgba(255, 255, 255, 0.1); max-height: 1px;")
        main_layout.addWidget(separator)
        
        # 样品网格布局（2列）
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        
        row, col = 0, 0
        for sample in samples[:6]:  # 最多显示6个样品
            sample_item = self.create_sample_item(sample)
            grid_layout.addWidget(sample_item, row, col)
            col += 1
            if col >= 2:  # 2列布局
                col = 0
                row += 1
        
        main_layout.addLayout(grid_layout)
        
        return widget
    
    def create_sample_item(self, sample: Dict) -> QWidget:
        """创建单个样品项（紧凑版）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 3px;
                padding: 4px 6px;
            }
            QWidget:hover {
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 样品名称
        name = sample.get('name', f"样品#{sample.get('position', '?')}")
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #fff; font-size: 10px;")
        name_label.setFixedWidth(55)
        layout.addWidget(name_label)
        
        # 着火温度
        temp = sample.get('temperature')
        if temp is not None:
            temp_label = QLabel(f"{temp:.0f}°C")
            temp_label.setStyleSheet("color: #00ff00; font-size: 10px;")
        else:
            temp_label = QLabel("未着火")
            temp_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(temp_label)
        
        layout.addStretch()
        
        return widget
    
    def create_ignition_samples_section(self, samples: list, sample_data: list) -> QWidget:
        """创建着火点实验增强样品区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("🧪 样品详情")
        title_label.setStyleSheet("color: #00d9ff; font-size: 11px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: rgba(255, 255, 255, 0.1); max-height: 1px;")
        main_layout.addWidget(separator)
        
        # 合并样品基本信息和测试数据
        for i, sample in enumerate(samples[:6], 1):
            # 查找对应的测试数据
            test_data = next((s for s in sample_data if s['sample_position'] == i), None)
            
            sample_widget = self.create_ignition_sample_item(i, sample, test_data)
            main_layout.addWidget(sample_widget)
        
        return widget
    
    def create_ignition_sample_item(self, position: int, sample: Dict, test_data: Dict = None) -> QWidget:
        """创建着火点单个样品项（包含测试数据）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 3px;
                padding: 6px 8px;
            }
            QWidget:hover {
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 第一行：样品名称和温度
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        
        # 样品名称
        name = sample.get('name', f'样品{position}')
        name_label = QLabel(f"样品{position}: {name}")
        name_label.setStyleSheet("color: #00d9ff; font-size: 10px; font-weight: bold;")
        row1.addWidget(name_label)
        
        row1.addStretch()
        
        # 着火温度
        temp_value = None
        if test_data and test_data.get('ignition_temperature') is not None:
            temp_value = test_data['ignition_temperature']
        
        if temp_value is not None:
            temp_label = QLabel(f"着火温度：{temp_value:.1f}°C")
            temp_label.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold;")
            row1.addWidget(temp_label)
        else:
            # 显示未着火
            no_temp_label = QLabel("未着火")
            no_temp_label.setStyleSheet("color: #666; font-size: 10px;")
            row1.addWidget(no_temp_label)
        
        layout.addLayout(row1)
        
        # 第二行：测试数据（如果有且温度有效）
        if test_data and temp_value is not None:
            row2 = QHBoxLayout()
            row2.setSpacing(10)
            
            rise_rate = test_data.get('temperature_rise_rate')
            is_valid = test_data.get('is_valid', True)
            valid_text = "有效" if is_valid else "无效"
            
            if rise_rate is not None:
                test_info = f"温升速率: {rise_rate:.2f}°C/min  |  数据: {valid_text}"
            else:
                test_info = f"数据: {valid_text}"
            
            test_label = QLabel(test_info)
            test_label.setStyleSheet("color: #aaa; font-size: 9px;")
            row2.addWidget(test_label)
            
            layout.addLayout(row2)
        
        return widget

