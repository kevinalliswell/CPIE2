"""
爆炸性实验详情卡片组件
显示爆炸性实验的完整信息，包括基本信息、参数、测试结果等
"""

from typing import Dict
import statistics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt

# 导入基类
from src.views.ui_components.base_detail_card import BaseDetailCard
# 导入图片查看对话框
from src.views.dialogs.image_viewer_dialog import ImageViewerDialog


class ExplosionDetailCard(BaseDetailCard):
    """
    爆炸性实验详情卡片
    专门用于显示爆炸性实验的详细信息
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def load_experiment_detail(self, exp_id: int, exp_data: Dict, explosion_db=None):
        """
        加载爆炸性实验详情
        Args:
            exp_id: 实验ID
            exp_data: 实验数据字典
            explosion_db: 爆炸性实验数据库实例
        """
        self.experiment_data = exp_data
        
        # 清空现有内容
        self.clear_content()
        
        # 查询测试数据
        if 'tests' not in exp_data and explosion_db:
            tests = explosion_db.get_session_test_rounds(exp_id)
            if tests:
                # 转换为详情卡片需要的格式
                exp_data['tests'] = [
                    {
                        'test_sequence': t['round_number'],
                        'flame_length_mm': t['flame_length'],
                        'image_path': t.get('max_flame_image_path')
                    } for t in tests
                ]
        
        # 如果没有结论，自动生成
        if not exp_data.get('conclusion') and explosion_db:
            try:
                exp_data['conclusion'] = explosion_db.generate_conclusion(exp_id)
            except Exception:
                pass  # 生成失败时使用默认值或不显示
        
        # 显示爆炸性实验详情
        self.show_explosion_detail(exp_data)
        
        # 显示按钮区域
        self.button_widget.setVisible(True)
    
    # ==================== 爆炸性实验详情 ====================
    
    def show_explosion_detail(self, data: Dict):
        """显示爆炸性实验详情"""
        # 标题区域
        title_section = self.create_title_section(
            data.get('experiment_code', 'N/A'),
            "🔥 爆炸性实验"
        )
        self.content_layout.addWidget(title_section)
        
        # 基本信息
        basic_info = self.create_info_section(
            "📋 基本信息",
            [
                ("检测人员", data.get('inspector', 'N/A'), "#00d9ff"),
                ("委托单位", data.get('client_organization', 'N/A'), "#aaa"),
                ("重复次数", f"{data.get('repeat_times', 5)} 次", "#aaa"),
            ]
        )
        self.content_layout.addWidget(basic_info)
        
        # 样品信息（只保留样品名称）
        sample_name = data.get('sample_name', 'N/A')
        if sample_name and sample_name != 'N/A':
            sample_info = self.create_info_section(
                "🧪 样品信息",
                [
                    ("样品名称", sample_name, "#00d9ff"),
                ]
            )
            self.content_layout.addWidget(sample_info)
        
        # 测试结果
        max_flame = data.get('max_flame_length')
        if max_flame is not None:
            results_items = [
                ("最大火焰长度", f"{max_flame:.1f} mm", "#00ff00"),
            ]
            
            # 如果有爆炸性等级
            level = data.get('explosion_level')
            if level:
                results_items.append(("爆炸性等级", level, "#ff9800"))
            
            results_info = self.create_info_section("📊 测试结果", results_items)
            self.content_layout.addWidget(results_info)
        
        # 统计分析（如果有tests数据）
        if 'tests' in data and data['tests']:
            stats_section = self.create_explosion_stats_section(data)
            self.content_layout.addWidget(stats_section)
        
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
    
    def create_explosion_stats_section(self, data: Dict) -> QWidget:
        """创建爆炸性实验统计分析区域"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 8px 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("📈 统计分析")
        title_label.setStyleSheet("color: #00d9ff; font-size: 11px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: rgba(255, 255, 255, 0.1); max-height: 1px;")
        layout.addWidget(separator)
        
        # 从测试数据计算统计值
        tests = data.get('tests', [])
        if tests:
            flame_lengths = [t.get('flame_length_mm', 0) for t in tests]
            stats = {
                'avg': statistics.mean(flame_lengths) if flame_lengths else 0,
                'max': max(flame_lengths) if flame_lengths else 0,
                'min': min(flame_lengths) if flame_lengths else 0,
                'std_dev': statistics.stdev(flame_lengths) if len(flame_lengths) > 1 else 0,
                'count': len(flame_lengths)
            }
            # 计算变异系数
            if stats['avg'] > 0:
                stats['cv'] = (stats['std_dev'] / stats['avg']) * 100
            else:
                stats['cv'] = 0
        else:
            stats = {'avg': 0, 'max': 0, 'min': 0, 'std_dev': 0, 'cv': 0, 'count': 0}
        
        # 统计信息
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        
        stats_items = [
            ("平均值", f"{stats.get('avg', 0):.1f} mm", "#00d9ff"),
            ("最大值", f"{stats.get('max', 0):.1f} mm", "#00ff00"),
            ("最小值", f"{stats.get('min', 0):.1f} mm", "#5555ff"),
            ("标准差", f"{stats.get('std_dev', 0):.2f} mm", "#ff9800"),
            ("变异系数", f"{stats.get('cv', 0):.2f} %", "#ff9800"),
            ("数据点数", f"{stats.get('count', 0)} 个", "#aaa"),
        ]
        
        for i, (label, value, color) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            
            label_widget = QLabel(f"{label}:")
            label_widget.setStyleSheet("color: #888; font-size: 10px;")
            label_widget.setFixedWidth(70)
            grid_layout.addWidget(label_widget, row, col)
            
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
            grid_layout.addWidget(value_widget, row, col + 1)
        
        layout.addLayout(grid_layout)
        
        # 测试数据列表
        tests = data.get('tests', [])
        if tests:
            tests_label = QLabel(f"\n测试数据 ({len(tests)}次):")
            tests_label.setStyleSheet("color: #888; font-size: 10px;")
            layout.addWidget(tests_label)
            
            # 显示所有测试数据，适配不同工况（5次或10次）
            for test in tests:
                test_row = self.create_test_item_with_image_btn(test)
                layout.addWidget(test_row)
        
        return widget
    
    def create_test_item_with_image_btn(self, test: Dict) -> QWidget:
        """创建带图片查看按钮的测试项"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        
        row_layout = QHBoxLayout(widget)
        row_layout.setSpacing(8)
        row_layout.setContentsMargins(0, 2, 0, 2)
        
        # 测试数据文本
        test_text = f"  测试{test['test_sequence']}: {test['flame_length_mm']:.1f} mm"
        test_label = QLabel(test_text)
        test_label.setStyleSheet("color: #aaa; font-size: 9px;")
        row_layout.addWidget(test_label)
        
        row_layout.addStretch()
        
        # 查看图片按钮
        if test.get('image_path'):
            view_btn = QPushButton("🖼️ 查看")
            view_btn.setFixedSize(50, 20)
            view_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 217, 255, 0.2);
                    border: 1px solid rgba(0, 217, 255, 0.4);
                    color: #00d9ff;
                    border-radius: 3px;
                    font-size: 9px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background: rgba(0, 217, 255, 0.3);
                    border: 1px solid rgba(0, 217, 255, 0.6);
                }
                QPushButton:pressed {
                    background: rgba(0, 217, 255, 0.4);
                }
            """)
            view_btn.clicked.connect(lambda: self.show_flame_image(test))
            row_layout.addWidget(view_btn)
        
        return widget
    
    def show_flame_image(self, test: Dict):
        """显示火焰图片"""
        # 获取实验编号和样品名称
        experiment_id = self.experiment_data.get('experiment_code', '') if hasattr(self, 'experiment_data') else ''
        sample_name = self.experiment_data.get('sample_name', '') if hasattr(self, 'experiment_data') else ''
        
        # 使用独立的图片查看对话框
        dialog = ImageViewerDialog(test, self, experiment_id=experiment_id, sample_name=sample_name)
        dialog.exec()

