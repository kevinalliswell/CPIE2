"""
实验报告生成对话框
用于预览和导出标准格式的实验报告
"""

from typing import Dict
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QFileDialog, QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# 导入matplotlib相关库
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class GenerateReportDialog(QDialog):
    """
    实验报告生成对话框
    显示标准格式的实验报告预览，支持导出Word/PDF
    """
    
    report_exported = Signal(str)  # 导出路径
    
    def __init__(self, exp_id: int, exp_type: str, exp_data: Dict, 
                 explosion_db=None, ignition_db=None, parent=None):
        super().__init__(parent)
        
        self.exp_id = exp_id
        self.exp_type = exp_type
        self.exp_data = exp_data
        self.explosion_db = explosion_db
        self.ignition_db = ignition_db
        
        self.setWindowTitle(f"实验报告 - {exp_data.get('experiment_code', '未知')}")
        self.setModal(True)
        self.resize(900, 700)
        
        self.setup_ui()
        self.load_report_content()
    
    def setup_ui(self):
        """初始化UI"""
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #ffffff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📄 实验报告预览")
        title_label.setStyleSheet("color: #00d9ff; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        type_label = QLabel("💥 爆炸性实验报告" if self.exp_type == "explosion" else "🔥 着火点实验报告")
        type_label.setStyleSheet("color: #aaa; font-size: 14px;")
        header_layout.addWidget(type_label)
        
        main_layout.addLayout(header_layout)
        
        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: rgba(0, 217, 255, 0.3);")
        main_layout.addWidget(separator)
        
        # 报告内容区域（可滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.2);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 217, 255, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 217, 255, 0.5);
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(15)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        
        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area, 1)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 导出Word按钮
        self.export_word_btn = QPushButton("📝 导出Word")
        self.export_word_btn.setStyleSheet("""
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
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00e8ff,
                    stop: 1 #00a8d0
                );
            }
        """)
        self.export_word_btn.clicked.connect(self.on_export_word)
        
        # 导出PDF按钮
        self.export_pdf_btn = QPushButton("📄 导出PDF")
        self.export_pdf_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 217, 255, 0.2);
                border: 1px solid rgba(0, 217, 255, 0.4);
                color: #00d9ff;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 217, 255, 0.3);
            }
        """)
        self.export_pdf_btn.clicked.connect(self.on_export_pdf)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #fff;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        close_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.export_word_btn)
        button_layout.addWidget(self.export_pdf_btn)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def load_report_content(self):
        """加载报告内容"""
        if self.exp_type == "explosion":
            self.create_explosion_report()
        else:
            self.create_ignition_report()
    
    def create_explosion_report(self):
        """创建爆炸性实验报告"""
        # 报告标题
        title = self.create_report_title("煤粉爆炸性检测实验报告")
        self.content_layout.addWidget(title)
        
        # 实验信息
        info_section = self.create_info_section()
        self.content_layout.addWidget(info_section)
        
        # 样品信息
        sample_section = self.create_sample_section()
        self.content_layout.addWidget(sample_section)
        
        # 实验方法
        method_section = self.create_method_section_explosion()
        self.content_layout.addWidget(method_section)
        
        # 测试结果
        result_section = self.create_result_section_explosion()
        self.content_layout.addWidget(result_section)
        
        # 结论
        conclusion_section = self.create_conclusion_section()
        self.content_layout.addWidget(conclusion_section)
        
        # 附加信息
        additional_section = self.create_additional_section()
        self.content_layout.addWidget(additional_section)
        
        self.content_layout.addStretch()
    
    def create_ignition_report(self):
        """创建着火点实验报告"""
        # 报告标题
        title = self.create_report_title("煤粉着火点检测实验报告")
        self.content_layout.addWidget(title)
        
        # 实验信息
        info_section = self.create_info_section()
        self.content_layout.addWidget(info_section)
        
        # 样品信息
        sample_section = self.create_sample_section_ignition()
        self.content_layout.addWidget(sample_section)
        
        # 实验方法
        method_section = self.create_method_section_ignition()
        self.content_layout.addWidget(method_section)
        
        # 测试结果
        result_section = self.create_result_section_ignition()
        self.content_layout.addWidget(result_section)
        
        # 温度曲线图
        chart_section = self.create_temperature_chart_section()
        if chart_section:
            self.content_layout.addWidget(chart_section)
        
        # 结论
        conclusion_section = self.create_conclusion_section()
        self.content_layout.addWidget(conclusion_section)
        
        # 附加信息
        additional_section = self.create_additional_section()
        self.content_layout.addWidget(additional_section)
        
        self.content_layout.addStretch()
    
    def create_report_title(self, title_text: str) -> QWidget:
        """创建报告标题"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                padding: 10px 0;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title_label)
        
        code_label = QLabel(f"实验编号: {self.exp_data.get('experiment_code', 'N/A')}")
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(code_label)
        
        return widget
    
    def create_info_section(self) -> QWidget:
        """创建实验基本信息部分"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("一、实验基本信息")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 信息网格
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(10, 5, 10, 5)
        
        info_items = [
            ("实验编号:", self.exp_data.get('experiment_code', 'N/A')),
            ("检测人员:", self.exp_data.get('inspector', 'N/A')),
            ("委托单位:", self.exp_data.get('client_organization', 'N/A')),
            ("开始时间:", self.format_time(self.exp_data.get('start_time'))),
            ("结束时间:", self.format_time(self.exp_data.get('end_time'))),
            ("实验日期:", self.format_date(self.exp_data.get('start_time'))),
        ]
        
        for i, (label, value) in enumerate(info_items):
            row = i // 2
            col = (i % 2) * 2
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #888; font-size: 12px;")
            label_widget.setFixedWidth(80)
            grid.addWidget(label_widget, row, col)
            
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet("color: #fff; font-size: 12px;")
            grid.addWidget(value_widget, row, col + 1)
        
        layout.addLayout(grid)
        
        return widget
    
    def create_sample_section(self) -> QWidget:
        """创建样品信息部分（爆炸性实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("二、样品信息")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 样品信息
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        label_widget = QLabel("样品名称:")
        label_widget.setStyleSheet("color: #888; font-size: 12px;")
        label_widget.setFixedWidth(80)
        info_layout.addWidget(label_widget)
        
        value_widget = QLabel(str(self.exp_data.get('sample_name', 'N/A')))
        value_widget.setStyleSheet("color: #fff; font-size: 12px;")
        info_layout.addWidget(value_widget)
        
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # 样品描述
        if self.exp_data.get('sample_description'):
            desc_label = QLabel("样品描述:")
            desc_label.setStyleSheet("color: #888; font-size: 12px; margin-top: 5px;")
            layout.addWidget(desc_label)
            
            desc_value = QLabel(self.exp_data.get('sample_description'))
            desc_value.setWordWrap(True)
            desc_value.setStyleSheet("color: #fff; font-size: 12px; padding-left: 10px;")
            layout.addWidget(desc_value)
        
        return widget
    
    def create_sample_section_ignition(self) -> QWidget:
        """创建样品信息部分（着火点实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("二、样品信息")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 样品数量
        samples = self.exp_data.get('samples', [])
        sample_count_label = QLabel(f"共 {len(samples)} 个样品")
        sample_count_label.setStyleSheet("color: #aaa; font-size: 12px; margin-left: 10px;")
        layout.addWidget(sample_count_label)
        
        # 样品列表（按样品实际位置编号，未填写的槽位不占用编号）
        if samples:
            for i, sample in enumerate(samples, 1):
                sample_item = self.create_sample_item_ignition(sample.get('position', i), sample)
                layout.addWidget(sample_item)

        return widget

    @staticmethod
    def _sample_name_for_position(samples, pos):
        """按样品位置（1-6）查找样品名称；samples 列表只包含已填写名称的样品，不能按下标取"""
        default_name = f"样品{pos}"
        for sample in samples or []:
            if sample.get('position') == pos:
                return sample.get('name') or default_name
        return default_name
    
    def create_sample_item_ignition(self, position: int, sample: Dict) -> QWidget:
        """创建单个样品项（着火点实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 5px;
                padding: 8px;
                margin-left: 10px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        pos_label = QLabel(f"样品{position}:")
        pos_label.setStyleSheet("color: #00d9ff; font-size: 11px; font-weight: bold;")
        pos_label.setFixedWidth(60)
        layout.addWidget(pos_label)
        
        name = sample.get('name', f'样品{position}')
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #fff; font-size: 11px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        return widget
    
    def create_method_section_explosion(self) -> QWidget:
        """创建实验方法部分（爆炸性实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("三、实验方法")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 方法描述
        method_text = """
依据 GB/T AQ/T 1045-2010《煤尘爆炸性鉴定规范》进行测试。

实验步骤:
1. 样品准备：将煤样研磨至规定粒度，干燥后备用
2. 装置准备：清理实验装置，检查气密性
3. 样品投放：将规定质量的煤粉投入实验容器
4. 点火测试：启动点火装置，记录火焰传播情况
5. 数据采集：测量最大火焰长度，记录实验现象
6. 重复测试：进行多次重复实验，确保数据可靠性
        """
        
        method_label = QLabel(method_text.strip())
        method_label.setWordWrap(True)
        method_label.setStyleSheet("color: #ccc; font-size: 11px; line-height: 1.6; padding-left: 10px;")
        layout.addWidget(method_label)
        
        # 测试参数
        params_label = QLabel(f"重复测试次数: {self.exp_data.get('repeat_times', 5)} 次")
        params_label.setStyleSheet("color: #fff; font-size: 12px; margin-top: 5px; padding-left: 10px;")
        layout.addWidget(params_label)
        
        return widget
    
    def create_method_section_ignition(self) -> QWidget:
        """创建实验方法部分（着火点实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("三、实验方法")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 方法描述
        method_text = """
依据 GB/T 18511-2017《煤的着火温度测定方法》进行测试。

实验步骤:
1. 样品准备：将煤样研磨至规定粒度，干燥后备用
2. 装置准备：校准温度控制系统，检查测温装置
3. 样品装填：将煤粉样品装入坩埚，放置于加热炉中
4. 程序升温：按照规定的升温速率进行加热
5. 温度监测：实时监测样品温度变化，记录着火时刻
6. 数据记录：记录各样品的着火温度及相关参数
        """
        
        method_label = QLabel(method_text.strip())
        method_label.setWordWrap(True)
        method_label.setStyleSheet("color: #ccc; font-size: 11px; line-height: 1.6; padding-left: 10px;")
        layout.addWidget(method_label)
        
        # 测试参数
        params_text = f"样品数量: {len(self.exp_data.get('samples', []))} 个\n升温速率: 5°C/min（标准）"
        params_label = QLabel(params_text)
        params_label.setStyleSheet("color: #fff; font-size: 11px; margin-top: 5px; padding-left: 10px;")
        layout.addWidget(params_label)
        
        return widget
    
    def create_result_section_explosion(self) -> QWidget:
        """创建测试结果部分（爆炸性实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("四、测试结果")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 从测试数据计算统计值
        tests = self.exp_data.get('tests', [])
        if tests:
            import statistics
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
        
        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)
        stats_grid.setContentsMargins(10, 5, 10, 5)
        
        stats_items = [
            ("最大火焰长度:", f"{stats.get('max', 0):.1f} mm", "#00ff00"),
            ("平均火焰长度:", f"{stats.get('avg', 0):.1f} mm", "#00d9ff"),
            ("最小火焰长度:", f"{stats.get('min', 0):.1f} mm", "#aaa"),
            ("标准差:", f"{stats.get('std_dev', 0):.2f} mm", "#ff9800"),
            ("变异系数:", f"{stats.get('cv', 0):.2f} %", "#ff9800"),
            ("有效数据:", f"{stats.get('count', 0)} 次", "#aaa"),
        ]
        
        for i, (label, value, color) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #888; font-size: 12px;")
            label_widget.setFixedWidth(100)
            stats_grid.addWidget(label_widget, row, col)
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            stats_grid.addWidget(value_widget, row, col + 1)
        
        layout.addLayout(stats_grid)
        
        # 各次测试数据
        tests = self.exp_data.get('tests', [])
        if tests:
            tests_title = QLabel("\n各次测试详细数据:")
            tests_title.setStyleSheet("color: #aaa; font-size: 12px;")
            layout.addWidget(tests_title)
            
            # 创建6列网格布局
            tests_grid = QGridLayout()
            tests_grid.setSpacing(5)
            tests_grid.setContentsMargins(10, 5, 10, 5)
            
            # 每5个测试为一组，每组占用2行（测试轮次行和火焰长度行）
            batch_size = 5
            for batch_idx in range(0, len(tests), batch_size):
                batch_tests = tests[batch_idx:batch_idx + batch_size]
                row_base = (batch_idx // batch_size) * 2
                
                # 第一行：测试轮次标题和数据
                test_sequence_label = QLabel("测试轮次")
                test_sequence_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
                test_sequence_label.setFixedWidth(100)
                tests_grid.addWidget(test_sequence_label, row_base, 0)
                
                for col_idx, test in enumerate(batch_tests):
                    test_seq_label = QLabel(str(f"第{test['test_sequence']}次测试"))
                    test_seq_label.setStyleSheet("color: #ccc; font-size: 11px;")
                    test_seq_label.setAlignment(Qt.AlignCenter)
                    tests_grid.addWidget(test_seq_label, row_base, col_idx + 1)
                
                # 第二行：火焰长度标题和数据
                flame_length_label = QLabel("火焰长度 (mm)")
                flame_length_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
                flame_length_label.setFixedWidth(100)
                tests_grid.addWidget(flame_length_label, row_base + 1, 0)
                
                for col_idx, test in enumerate(batch_tests):
                    flame_len_label = QLabel(f"{test['flame_length_mm']:.1f}")
                    flame_len_label.setStyleSheet("color: #ccc; font-size: 11px;")
                    flame_len_label.setAlignment(Qt.AlignCenter)
                    tests_grid.addWidget(flame_len_label, row_base + 1, col_idx + 1)
            
            layout.addLayout(tests_grid)
        
        return widget
    
    def create_result_section_ignition(self) -> QWidget:
        """创建测试结果部分（着火点实验）"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("四、测试结果")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 统计数据
        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)
        stats_grid.setContentsMargins(10, 5, 10, 5)
        
        avg_temp = self.exp_data.get('avg_ignition_temperature')
        highest_temp = self.exp_data.get('highest_ignition_temp')
        lowest_temp = self.exp_data.get('lowest_ignition_temp')
        
        stats_items = [
            ("平均着火温度:", f"{avg_temp:.1f} °C" if avg_temp else "N/A", "#00d9ff"),
            ("最高温度:", f"{highest_temp:.1f} °C" if highest_temp else "N/A", "#ff5555"),
            ("最低温度:", f"{lowest_temp:.1f} °C" if lowest_temp else "N/A", "#5555ff"),
        ]
        
        if highest_temp and lowest_temp:
            temp_range = highest_temp - lowest_temp
            stats_items.append(("温度范围:", f"{temp_range:.1f} °C", "#ff9800"))
        
        for i, (label, value, color) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #888; font-size: 12px;")
            label_widget.setFixedWidth(100)
            stats_grid.addWidget(label_widget, row, col)
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            stats_grid.addWidget(value_widget, row, col + 1)
        
        layout.addLayout(stats_grid)
        
        # 各样品测试数据
        sample_data = self.exp_data.get('sample_data', [])
        samples = self.exp_data.get('samples', [])
        
        if sample_data:
            samples_title = QLabel("\n各样品测试详细数据:")
            samples_title.setStyleSheet("color: #aaa; font-size: 12px;")
            layout.addWidget(samples_title)
            
            for data in sample_data:
                pos = data['sample_position']
                temp = data.get('ignition_temperature')
                
                # 获取样品名称（按样品位置查找：samples 列表会跳过未填写的样品槽位，不能按下标取）
                sample_name = self._sample_name_for_position(samples, pos)
                
                if temp is not None:
                    test_label = QLabel(
                        f"  {sample_name}: {temp:.1f} °C"
                    )
                    test_label.setStyleSheet("color: #ccc; font-size: 11px; padding-left: 10px;")
                else:
                    test_label = QLabel(f"  {sample_name}: 未着火")
                    test_label.setStyleSheet("color: #666; font-size: 11px; padding-left: 10px;")
                
                layout.addWidget(test_label)
        
        return widget
    
    def create_conclusion_section(self) -> QWidget:
        """创建实验结论部分"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题（根据实验类型动态设置章节编号）
        # 爆炸性实验: 五、实验结论
        # 着火点实验: 六、实验结论（因为有"五、升温过程曲线"）
        section_number = "六" if self.exp_type == "ignition" else "五"
        section_title = QLabel(f"{section_number}、实验结论")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 结论内容
        conclusion = self.exp_data.get('conclusion') or '实验结论未填写，待确认。'
        conclusion_label = QLabel(conclusion)
        conclusion_label.setWordWrap(True)
        conclusion_label.setStyleSheet("color: #fff; font-size: 12px; padding-left: 10px; line-height: 1.5;")
        layout.addWidget(conclusion_label)
        
        return widget
    
    def create_additional_section(self) -> QWidget:
        """创建附加信息部分"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题（根据实验类型动态设置章节编号）
        # 爆炸性实验: 六、备注
        # 着火点实验: 七、备注（因为有"五、升温过程曲线"和"六、实验结论"）
        section_number = "七" if self.exp_type == "ignition" else "六"
        section_title = QLabel(f"{section_number}、备注")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 备注内容
        notes = self.exp_data.get('notes', '无')
        notes_label = QLabel(notes)
        notes_label.setWordWrap(True)
        notes_label.setStyleSheet("color: #aaa; font-size: 11px; padding-left: 10px; line-height: 1.5;")
        layout.addWidget(notes_label)
        
        # 报告生成时间
        report_time = QLabel(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_time.setStyleSheet("color: #666; font-size: 10px; text-align: right;")
        report_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(report_time)
        
        return widget
    
    def format_time(self, time_str):
        """格式化时间字符串"""
        if not time_str:
            return 'N/A'
        if isinstance(time_str, str) and len(time_str) > 19:
            return time_str[:19]
        return str(time_str)
    
    def format_date(self, time_str):
        """格式化日期字符串"""
        if not time_str:
            return 'N/A'
        if isinstance(time_str, str) and len(time_str) >= 10:
            return time_str[:10]
        return str(time_str)
    
    def _get_temperature_series(self):
        """获取温度序列数据（着火点实验）"""
        if not self.ignition_db or self.exp_type != "ignition":
            return []
        
        try:
            # 按会话ID读取该实验的全部温度数据（含相对实验开始的 elapsed_seconds）。
            # 旧实现按 start_time/end_time 做时间范围查询，而实时数据的时间戳曾由
            # SQLite CURRENT_TIMESTAMP（UTC）写入，与本地时间的会话时间不在同一时区，
            # 查询结果为空，报告中的温度曲线会被静默省略。
            session_data = self.ignition_db.get_session_temperature_data(self.exp_id)
            if not session_data:
                return []

            temp_series = []
            for record in session_data:
                temp_series.append({
                    'elapsed_seconds': record.get('elapsed_seconds', 0.0),
                    'sample1_temperature': record.get('sample1_temperature'),
                    'sample2_temperature': record.get('sample2_temperature'),
                    'sample3_temperature': record.get('sample3_temperature'),
                    'sample4_temperature': record.get('sample4_temperature'),
                    'sample5_temperature': record.get('sample5_temperature'),
                    'sample6_temperature': record.get('sample6_temperature'),
                })

            return temp_series
        except Exception as e:
            print(f"获取温度序列失败: {e}")
            return []
    
    def _get_explosion_statistics(self):
        """获取爆炸性实验统计数据"""
        tests = self.exp_data.get('tests', [])
        if tests:
            import statistics
            flame_lengths = [t.get('flame_length_mm', 0) for t in tests]
            stats = {
                'avg': statistics.mean(flame_lengths) if flame_lengths else 0,
                'max': max(flame_lengths) if flame_lengths else 0,
                'min': min(flame_lengths) if flame_lengths else 0,
                'std_dev': statistics.stdev(flame_lengths) if len(flame_lengths) > 1 else 0,
                'count': len(flame_lengths)
            }
            if stats['avg'] > 0:
                stats['cv'] = (stats['std_dev'] / stats['avg']) * 100
            else:
                stats['cv'] = 0
            return stats
        return {'avg': 0, 'max': 0, 'min': 0, 'std_dev': 0, 'cv': 0, 'count': 0}
    
    def on_export_word(self):
        """导出Word文档"""
        try:
            from docx import Document
            from docx.shared import Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            QMessageBox.warning(
                self,
                "警告",
                "Word报告导出功能需要python-docx库，请先安装：\npip install python-docx"
            )
            return
        
        from datetime import datetime
        
        exp_code = self.exp_data.get('experiment_code', 'UNKNOWN')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"实验报告_{exp_code}_{timestamp}.docx"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出Word报告",
            default_filename,
            "Word文档 (*.docx);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 创建Word文档
            doc = Document()
            
            # 设置默认字体
            style = doc.styles['Normal']
            font = style.font
            font.name = '宋体'
            font.size = Pt(12)
            
            # 标题
            title = doc.add_heading('煤粉爆炸性检测实验报告' if self.exp_type == 'explosion' else '煤粉着火点检测实验报告', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 实验编号
            code_para = doc.add_paragraph(f"实验编号: {exp_code}")
            code_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 基本信息
            doc.add_heading('一、实验基本信息', 1)
            info_table = doc.add_table(rows=6, cols=2)
            info_table.style = 'Light Grid Accent 1'
            
            info_items = [
                ("实验编号", exp_code),
                ("检测人员", self.exp_data.get('inspector', 'N/A')),
                ("委托单位", self.exp_data.get('client_organization', 'N/A')),
                ("开始时间", self.format_time(self.exp_data.get('start_time'))),
                ("结束时间", self.format_time(self.exp_data.get('end_time'))),
                ("实验日期", self.format_date(self.exp_data.get('start_time'))),
            ]
            
            for i, (label, value) in enumerate(info_items):
                info_table.rows[i].cells[0].text = label
                info_table.rows[i].cells[1].text = str(value)
            
            # 样品信息
            doc.add_heading('二、样品信息', 1)
            if self.exp_type == 'explosion':
                doc.add_paragraph(f"样品名称: {self.exp_data.get('sample_name', 'N/A')}")
            else:
                samples = self.exp_data.get('samples', [])
                doc.add_paragraph(f"共 {len(samples)} 个样品")
                for i, sample in enumerate(samples, 1):
                    pos = sample.get('position', i)
                    doc.add_paragraph(f"样品{pos}: {sample.get('name', f'样品{pos}')}", style='List Bullet')
            
            # 实验方法
            doc.add_heading('三、实验方法', 1)
            if self.exp_type == 'explosion':
                doc.add_paragraph('依据 GB/T AQ/T 1045-2010《煤尘爆炸性鉴定规范》进行测试。')
                doc.add_paragraph(f"重复测试次数: {self.exp_data.get('repeat_times', 5)} 次")
            else:
                doc.add_paragraph('依据 GB/T 18511-2017《煤的着火温度测定方法》进行测试。')
                doc.add_paragraph(f"样品数量: {len(self.exp_data.get('samples', []))} 个")
            
            # 测试结果
            doc.add_heading('四、测试结果', 1)
            if self.exp_type == 'explosion':
                stats = self._get_explosion_statistics()
                result_table = doc.add_table(rows=6, cols=2)
                result_table.style = 'Light Grid Accent 1'
                
                result_items = [
                    ("最大火焰长度", f"{stats.get('max', 0):.1f} mm"),
                    ("平均火焰长度", f"{stats.get('avg', 0):.1f} mm"),
                    ("最小火焰长度", f"{stats.get('min', 0):.1f} mm"),
                    ("标准差", f"{stats.get('std_dev', 0):.2f} mm"),
                    ("变异系数", f"{stats.get('cv', 0):.2f} %"),
                    ("有效数据", f"{stats.get('count', 0)} 次"),
                ]
                
                for i, (label, value) in enumerate(result_items):
                    result_table.rows[i].cells[0].text = label
                    result_table.rows[i].cells[1].text = value
                
                # 各次测试数据
                tests = self.exp_data.get('tests', [])
                if tests:
                    doc.add_paragraph('各次测试详细数据:')
                    # 创建6列表格：第1列为标题列，第2-6列为数据列
                    batch_size = 5
                    for batch_idx in range(0, len(tests), batch_size):
                        batch_tests = tests[batch_idx:batch_idx + batch_size]
                        # 每组需要2行：测试轮次行和火焰长度行
                        test_table = doc.add_table(rows=2, cols=6)
                        test_table.style = 'Light Grid Accent 1'
                        
                        # 第一行：测试轮次
                        test_table.rows[0].cells[0].text = "测试轮次"
                        for col_idx, test in enumerate(batch_tests):
                            test_table.rows[0].cells[col_idx + 1].text = str(test['test_sequence'])
                        
                        # 第二行：火焰长度
                        test_table.rows[1].cells[0].text = "火焰长度 (mm)"
                        for col_idx, test in enumerate(batch_tests):
                            test_table.rows[1].cells[col_idx + 1].text = f"{test['flame_length_mm']:.1f}"
                        
                        # 如果不足5个测试，清空多余的列
                        for col_idx in range(len(batch_tests), batch_size):
                            test_table.rows[0].cells[col_idx + 1].text = ""
                            test_table.rows[1].cells[col_idx + 1].text = ""
                        
                        doc.add_paragraph()  # 添加空行分隔
            else:
                stats_table = doc.add_table(rows=3, cols=2)
                stats_table.style = 'Light Grid Accent 1'
                
                avg_temp = self.exp_data.get('avg_ignition_temperature')
                highest_temp = self.exp_data.get('highest_ignition_temp')
                lowest_temp = self.exp_data.get('lowest_ignition_temp')
                
                stats_items = [
                    ("平均着火温度", f"{avg_temp:.1f} °C" if avg_temp else "N/A"),
                    ("最高温度", f"{highest_temp:.1f} °C" if highest_temp else "N/A"),
                    ("最低温度", f"{lowest_temp:.1f} °C" if lowest_temp else "N/A"),
                ]
                
                for i, (label, value) in enumerate(stats_items):
                    stats_table.rows[i].cells[0].text = label
                    stats_table.rows[i].cells[1].text = value
                
                # 各样品测试数据
                sample_data = self.exp_data.get('sample_data', [])
                samples = self.exp_data.get('samples', [])
                if sample_data:
                    doc.add_paragraph('各样品测试详细数据:')
                    # 创建6列表格：第1列为标题列，第2-6列为数据列
                    batch_size = 5
                    for batch_idx in range(0, len(sample_data), batch_size):
                        batch_data = sample_data[batch_idx:batch_idx + batch_size]
                        # 每组需要2行：样品名称行和着火温度行
                        sample_table = doc.add_table(rows=2, cols=6)
                        sample_table.style = 'Light Grid Accent 1'
                        
                        # 第一行：样品名称
                        sample_table.rows[0].cells[0].text = "样品名称"
                        for col_idx, data in enumerate(batch_data):
                            pos = data['sample_position']
                            sample_name = self._sample_name_for_position(samples, pos)
                            sample_table.rows[0].cells[col_idx + 1].text = sample_name
                        
                        # 第二行：着火温度
                        sample_table.rows[1].cells[0].text = "着火温度 (°C)"
                        for col_idx, data in enumerate(batch_data):
                            temp = data.get('ignition_temperature')
                            if temp is not None:
                                sample_table.rows[1].cells[col_idx + 1].text = f"{temp:.1f}"
                            else:
                                sample_table.rows[1].cells[col_idx + 1].text = "未着火"
                        
                        # 如果不足5个样品，清空多余的列
                        for col_idx in range(len(batch_data), batch_size):
                            sample_table.rows[0].cells[col_idx + 1].text = ""
                            sample_table.rows[1].cells[col_idx + 1].text = ""
                        
                        doc.add_paragraph()  # 添加空行分隔
            
            # 实验结论
            section_num = "六" if self.exp_type == "ignition" else "五"
            doc.add_heading(f'{section_num}、实验结论', 1)
            conclusion = self.exp_data.get('conclusion') or '实验结论未填写，待确认。'
            doc.add_paragraph(conclusion)
            
            # 备注
            section_num = "七" if self.exp_type == "ignition" else "六"
            doc.add_heading(f'{section_num}、备注', 1)
            notes = self.exp_data.get('notes', '无')
            doc.add_paragraph(notes)
            
            # 报告生成时间
            report_time_para = doc.add_paragraph(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_time_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            
            # 保存文档
            doc.save(file_path)
            
            QMessageBox.information(
                self,
                "成功",
                f"Word报告已成功导出到:\n{file_path}"
            )
            self.report_exported.emit(file_path)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"导出Word报告失败：\n{str(e)}"
            )
    
    def on_export_pdf(self):
        """导出PDF文档"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            QMessageBox.warning(
                self,
                "警告",
                "PDF报告导出功能需要reportlab库，请先安装：\npip install reportlab"
            )
            return
        
        from datetime import datetime
        import os
        import platform
        from xml.sax.saxutils import escape  # reportlab Paragraph 会解析 XML 标记，用户文本必须转义
        
        exp_code = self.exp_data.get('experiment_code', 'UNKNOWN')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"实验报告_{exp_code}_{timestamp}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出PDF报告",
            default_filename,
            "PDF文档 (*.pdf);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 注册中文字体
            chinese_font_name = 'ChineseFont'
            chinese_font_bold_name = 'ChineseFontBold'
            
            # Windows系统字体路径
            if platform.system() == 'Windows':
                font_paths = [
                    r'C:\Windows\Fonts\simhei.ttf',  # 黑体
                    r'C:\Windows\Fonts\simsun.ttc',  # 宋体
                    r'C:\Windows\Fonts\msyh.ttc',    # 微软雅黑
                ]
            else:
                # Linux/Mac系统字体路径（可根据实际情况调整）
                font_paths = [
                    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驿微米黑
                    '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
                ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(chinese_font_name, font_path))
                        pdfmetrics.registerFont(TTFont(chinese_font_bold_name, font_path))
                        font_registered = True
                        break
                    except Exception:
                        continue
            
            # 如果找不到字体文件，尝试使用系统默认字体
            if not font_registered:
                try:
                    # 尝试注册SimHei（黑体）
                    pdfmetrics.registerFont(TTFont(chinese_font_name, 'SimHei'))
                    pdfmetrics.registerFont(TTFont(chinese_font_bold_name, 'SimHei'))
                    font_registered = True
                except Exception:
                    # 如果还是失败，使用reportlab内置的字体（可能不支持中文）
                    chinese_font_name = 'Helvetica'
                    chinese_font_bold_name = 'Helvetica-Bold'
            
            # 创建PDF文档
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # 标题样式（使用中文字体）
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=chinese_font_bold_name,
                fontSize=18,
                textColor=colors.HexColor('#00d9ff'),
                spaceAfter=30,
                alignment=1  # 居中
            )
            
            # 标题
            title_text = '煤粉爆炸性检测实验报告' if self.exp_type == 'explosion' else '煤粉着火点检测实验报告'
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 0.5*cm))
            
            # 实验编号（使用中文字体）
            code_style = ParagraphStyle(
                'CodeStyle',
                parent=styles['Normal'],
                fontName=chinese_font_name,
                fontSize=12,
                alignment=1  # 居中
            )
            story.append(Paragraph(f"实验编号: {escape(str(exp_code))}", code_style))
            story.append(Spacer(1, 1*cm))
            
            # 创建支持中文的样式
            heading2_style = ParagraphStyle(
                'ChineseHeading2',
                parent=styles['Heading2'],
                fontName=chinese_font_bold_name,
                fontSize=14,
                spaceAfter=12
            )
            
            normal_style = ParagraphStyle(
                'ChineseNormal',
                parent=styles['Normal'],
                fontName=chinese_font_name,
                fontSize=11,
                leading=16
            )
            
            # 一、实验基本信息
            story.append(Paragraph('一、实验基本信息', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            
            info_data = [
                ['实验编号', exp_code],
                ['检测人员', self.exp_data.get('inspector', 'N/A')],
                ['委托单位', self.exp_data.get('client_organization', 'N/A')],
                ['开始时间', self.format_time(self.exp_data.get('start_time'))],
                ['结束时间', self.format_time(self.exp_data.get('end_time'))],
                ['实验日期', self.format_date(self.exp_data.get('start_time'))],
            ]
            
            info_table = Table(info_data, colWidths=[4*cm, 12*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), chinese_font_bold_name),
                ('FONTNAME', (1, 0), (1, -1), chinese_font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.5*cm))
            
            # 二、样品信息
            story.append(Paragraph('二、样品信息', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            
            if self.exp_type == 'explosion':
                story.append(Paragraph(f"样品名称: {escape(str(self.exp_data.get('sample_name', 'N/A')))}", normal_style))
            else:
                samples = self.exp_data.get('samples', [])
                story.append(Paragraph(f"共 {len(samples)} 个样品", normal_style))
                for i, sample in enumerate(samples, 1):
                    pos = sample.get('position', i)
                    story.append(Paragraph(f"样品{pos}: {escape(str(sample.get('name', f'样品{pos}')))}", normal_style))
            
            story.append(Spacer(1, 0.5*cm))
            
            # 三、实验方法
            story.append(Paragraph('三、实验方法', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            
            if self.exp_type == 'explosion':
                story.append(Paragraph('依据 GB/T AQ/T 1045-2010《煤尘爆炸性鉴定规范》进行测试。', normal_style))
                story.append(Paragraph(f"重复测试次数: {self.exp_data.get('repeat_times', 5)} 次", normal_style))
            else:
                story.append(Paragraph('依据 GB/T 18511-2017《煤的着火温度测定方法》进行测试。', normal_style))
                story.append(Paragraph(f"样品数量: {len(self.exp_data.get('samples', []))} 个", normal_style))
            
            story.append(Spacer(1, 0.5*cm))
            
            # 四、测试结果
            story.append(Paragraph('四、测试结果', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            
            if self.exp_type == 'explosion':
                stats = self._get_explosion_statistics()
                result_data = [
                    ['最大火焰长度', f"{stats.get('max', 0):.1f} mm"],
                    ['平均火焰长度', f"{stats.get('avg', 0):.1f} mm"],
                    ['最小火焰长度', f"{stats.get('min', 0):.1f} mm"],
                    ['标准差', f"{stats.get('std_dev', 0):.2f} mm"],
                    ['变异系数', f"{stats.get('cv', 0):.2f} %"],
                    ['有效数据', f"{stats.get('count', 0)} 次"],
                ]
                
                result_table = Table(result_data, colWidths=[4*cm, 12*cm])
                result_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), chinese_font_bold_name),
                    ('FONTNAME', (1, 0), (1, -1), chinese_font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(result_table)
                story.append(Spacer(1, 0.3*cm))
                
                # 各次测试数据
                tests = self.exp_data.get('tests', [])
                if tests:
                    story.append(Paragraph('各次测试详细数据:', normal_style))
                    story.append(Spacer(1, 0.2*cm))
                    # 创建6列表格：第1列为标题列，第2-6列为数据列
                    batch_size = 5
                    for batch_idx in range(0, len(tests), batch_size):
                        batch_tests = tests[batch_idx:batch_idx + batch_size]
                        # 每组需要2行：测试轮次行和火焰长度行
                        test_data = [
                            ["测试轮次"] + [str(test['test_sequence']) for test in batch_tests] + [""] * (batch_size - len(batch_tests)),
                            ["火焰长度 (mm)"] + [f"{test['flame_length_mm']:.1f}" for test in batch_tests] + [""] * (batch_size - len(batch_tests))
                        ]
                        
                        test_table = Table(test_data, colWidths=[2.5*cm] + [2.5*cm] * 5)
                        test_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (0, -1), chinese_font_bold_name),
                            ('FONTNAME', (1, 0), (-1, -1), chinese_font_name),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(test_table)
                        story.append(Spacer(1, 0.2*cm))
            else:
                avg_temp = self.exp_data.get('avg_ignition_temperature')
                highest_temp = self.exp_data.get('highest_ignition_temp')
                lowest_temp = self.exp_data.get('lowest_ignition_temp')
                
                stats_data = [
                    ['平均着火温度', f"{avg_temp:.1f} °C" if avg_temp else "N/A"],
                    ['最高温度', f"{highest_temp:.1f} °C" if highest_temp else "N/A"],
                    ['最低温度', f"{lowest_temp:.1f} °C" if lowest_temp else "N/A"],
                ]
                
                stats_table = Table(stats_data, colWidths=[4*cm, 12*cm])
                stats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), chinese_font_bold_name),
                    ('FONTNAME', (1, 0), (1, -1), chinese_font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(stats_table)
                story.append(Spacer(1, 0.3*cm))
                
                # 各样品测试数据
                sample_data = self.exp_data.get('sample_data', [])
                samples = self.exp_data.get('samples', [])
                if sample_data:
                    story.append(Paragraph('各样品测试详细数据:', normal_style))
                    story.append(Spacer(1, 0.2*cm))
                    # 创建6列表格：第1列为标题列，第2-6列为数据列
                    batch_size = 5
                    for batch_idx in range(0, len(sample_data), batch_size):
                        batch_data = sample_data[batch_idx:batch_idx + batch_size]
                        # 每组需要2行：样品名称行和着火温度行
                        sample_names = []
                        sample_temps = []
                        for data in batch_data:
                            pos = data['sample_position']
                            sample_name = self._sample_name_for_position(samples, pos)
                            sample_names.append(sample_name)
                            
                            temp = data.get('ignition_temperature')
                            if temp is not None:
                                sample_temps.append(f"{temp:.1f}")
                            else:
                                sample_temps.append("未着火")
                        
                        sample_table_data = [
                            ["样品名称"] + sample_names + [""] * (batch_size - len(batch_data)),
                            ["着火温度 (°C)"] + sample_temps + [""] * (batch_size - len(batch_data))
                        ]
                        
                        sample_table = Table(sample_table_data, colWidths=[2.5*cm] + [2.5*cm] * 5)
                        sample_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (0, -1), chinese_font_bold_name),
                            ('FONTNAME', (1, 0), (-1, -1), chinese_font_name),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(sample_table)
                        story.append(Spacer(1, 0.2*cm))
            
            story.append(Spacer(1, 0.5*cm))
            
            # 实验结论
            section_num = "六" if self.exp_type == "ignition" else "五"
            story.append(Paragraph(f'{section_num}、实验结论', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            conclusion = self.exp_data.get('conclusion') or '实验结论未填写，待确认。'
            story.append(Paragraph(escape(str(conclusion)).replace('\n', '<br/>'), normal_style))
            story.append(Spacer(1, 0.5*cm))
            
            # 备注
            section_num = "七" if self.exp_type == "ignition" else "六"
            story.append(Paragraph(f'{section_num}、备注', heading2_style))
            story.append(Spacer(1, 0.3*cm))
            notes = self.exp_data.get('notes', '无')
            story.append(Paragraph(escape(str(notes)).replace('\n', '<br/>'), normal_style))
            story.append(Spacer(1, 1*cm))
            
            # 报告生成时间（使用中文字体）
            report_time_style = ParagraphStyle(
                'ReportTime',
                parent=normal_style,
                fontName=chinese_font_name,
                fontSize=9,
                alignment=2  # 右对齐
            )
            story.append(Paragraph(
                f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                report_time_style
            ))
            
            # 构建PDF
            doc.build(story)
            
            QMessageBox.information(
                self,
                "成功",
                f"PDF报告已成功导出到:\n{file_path}"
            )
            self.report_exported.emit(file_path)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"导出PDF报告失败：\n{str(e)}"
            )
    
    def create_temperature_chart_section(self) -> QWidget:
        """创建温度曲线图部分（着火点实验）"""
        # 从数据库获取温度序列数据
        temp_series = self._get_temperature_series()
        
        if not temp_series:
            return None
        
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        section_title = QLabel("五、样品温度实时监测曲线")
        section_title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(section_title)
        
        # 说明
        desc_label = QLabel(f"记录数据点: {len(temp_series)} 个  |  自动标注各样品着火点温度")
        desc_label.setStyleSheet("color: #aaa; font-size: 11px; padding-left: 10px;")
        layout.addWidget(desc_label)
        
        # 创建图表
        chart_widget = self.create_temperature_chart(temp_series)
        if chart_widget:
            layout.addWidget(chart_widget)
        
        return widget
    
    def create_temperature_chart(self, temp_series: list) -> QWidget:
        """创建温度曲线图"""
        if not temp_series:
            return None
        
        # 配置matplotlib支持中文
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        # 创建matplotlib图表
        fig = Figure(figsize=(8, 5), dpi=100)
        fig.patch.set_facecolor('#1a1a2e')
        
        ax = fig.add_subplot(111)
        ax.set_facecolor('#1a1a2e')
        
        # 提取数据
        times = []  # 时间（分钟）
        sample1_temps = []
        sample2_temps = []
        sample3_temps = []
        sample4_temps = []
        sample5_temps = []
        sample6_temps = []
        
        for data in temp_series:
            elapsed_minutes = data['elapsed_seconds'] / 60.0
            times.append(elapsed_minutes)
            sample1_temps.append(data.get('sample1_temperature'))
            sample2_temps.append(data.get('sample2_temperature'))
            sample3_temps.append(data.get('sample3_temperature'))
            sample4_temps.append(data.get('sample4_temperature'))
            sample5_temps.append(data.get('sample5_temperature'))
            sample6_temps.append(data.get('sample6_temperature'))
        
        # 获取各样品的着火点温度数据
        sample_data = self.exp_data.get('sample_data', [])
        ignition_temps = {}  # {position: temperature}
        for data in sample_data:
            pos = data['sample_position']
            temp = data.get('ignition_temperature')
            if temp is not None:
                ignition_temps[pos] = temp
        
        # 绘制各样品温度曲线
        sample_colors = ['#00d9ff', '#00ff00', '#ff9800', '#ff5555', '#9c27b0', '#ffeb3b']
        sample_data_list = [sample1_temps, sample2_temps, sample3_temps, 
                           sample4_temps, sample5_temps, sample6_temps]
        
        # 定义标注偏移位置（避免重叠）
        # 使用不同的方向和距离，让标注分散开
        annotation_offsets = [
            (15, 30),   # 样品1：右上
            (15, -30),  # 样品2：右下
            (-15, 30),  # 样品3：左上
            (-15, -30), # 样品4：左下
            (25, 15),   # 样品5：右偏上
            (-25, 15),  # 样品6：左偏上
        ]
        
        for i, (temps, color) in enumerate(zip(sample_data_list, sample_colors), 1):
            # 过滤None值
            valid_times = [t for t, temp in zip(times, temps) if temp is not None]
            valid_temps = [temp for temp in temps if temp is not None]
            
            if valid_temps:
                # 绘制温度曲线
                ax.plot(valid_times, valid_temps, '-', color=color, 
                       linewidth=2, label=f'样品{i}', alpha=0.8)
                
                # 标注着火点温度
                if i in ignition_temps:
                    ignition_temp = ignition_temps[i]
                    # 找到最接近着火温度的时间点
                    closest_idx = None
                    min_diff = float('inf')
                    for idx, temp in enumerate(valid_temps):
                        diff = abs(temp - ignition_temp)
                        if diff < min_diff:
                            min_diff = diff
                            closest_idx = idx
                    
                    if closest_idx is not None:
                        ignition_time = valid_times[closest_idx]
                        # 绘制着火点标记（大圆点）
                        ax.plot(ignition_time, ignition_temp, 'o', 
                               color=color, markersize=10, 
                               markeredgecolor='white', markeredgewidth=1.5,
                               zorder=5)
                        
                        # 获取该样品的偏移量
                        offset_x, offset_y = annotation_offsets[i-1]
                        
                        # 添加箭头标注
                        ax.annotate(f'样品{i}：{ignition_temp:.1f}°C', 
                                   xy=(ignition_time, ignition_temp),  # 箭头指向的点
                                   xytext=(offset_x, offset_y),  # 文字位置偏移
                                   textcoords='offset points',
                                   fontsize=9, 
                                   color='white',  # 文字颜色改为白色更清晰
                                   fontweight='bold',
                                   bbox=dict(boxstyle='round,pad=0.4', 
                                           facecolor=color,  # 背景色使用样品颜色
                                           edgecolor='white',
                                           linewidth=1.5,
                                           alpha=0.9),
                                   arrowprops=dict(
                                       arrowstyle='->',  # 箭头样式
                                       connectionstyle='arc3,rad=0.2',  # 带弧度的连接线
                                       color=color,  # 箭头颜色
                                       linewidth=1.5,
                                       alpha=0.8
                                   ),
                                   zorder=6)
        
        # 设置标签和标题
        ax.set_xlabel('时间 (分钟)', color='#aaa', fontsize=10)
        ax.set_ylabel('温度 (°C)', color='#aaa', fontsize=10)
        ax.set_title('样品温度实时监测曲线（标注着火点）', color='#00d9ff', fontsize=12, fontweight='bold', pad=15)
        
        # 设置网格
        ax.grid(True, alpha=0.2, color='#666', linestyle='--', linewidth=0.5)
        
        # 设置坐标轴颜色
        ax.tick_params(colors='#aaa', labelsize=9)
        ax.spines['bottom'].set_color('#666')
        ax.spines['top'].set_color('#666')
        ax.spines['left'].set_color('#666')
        ax.spines['right'].set_color('#666')
        
        # 设置图例
        legend = ax.legend(loc='upper left', fontsize=8, framealpha=0.8)
        legend.get_frame().set_facecolor('#1a1a2e')
        legend.get_frame().set_edgecolor('#00d9ff')
        for text in legend.get_texts():
            text.set_color('#aaa')
        
        # 调整布局
        fig.tight_layout()
        
        # 创建Qt画布
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(400)
        canvas.setStyleSheet("background: transparent;")
        
        return canvas


if __name__ == "__main__":
    """测试对话框"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 测试数据 - 爆炸性实验
    test_explosion_data = {
        'id': 1,
        'experiment_code': 'EXP-20251116-001',
        'inspector': '张三',
        'client_organization': 'XX煤矿有限公司',
        'sample_name': '烟煤样品A',
        'sample_code': 'M2025001',
        'sample_source': '山西',
        'sample_batch': 'B20251116',
        'sample_description': '测试样品，用于爆炸性能测试',
        'repeat_times': 5,
        'max_flame_length': 285.5,
        'start_time': '2025-11-16 09:30:00',
        'end_time': '2025-11-16 10:15:00',
        'conclusion': '该样品经5次重复测试，火焰传播特性符合标准要求。',
        'notes': '测试环境温度: 20℃，湿度: 45%',
        'tests': [
            {'test_sequence': 1, 'flame_length_mm': 275.5},
            {'test_sequence': 2, 'flame_length_mm': 285.5},
            {'test_sequence': 3, 'flame_length_mm': 280.0},
            {'test_sequence': 4, 'flame_length_mm': 270.5},
            {'test_sequence': 5, 'flame_length_mm': 282.0},
        ]
    }
    
    dialog = GenerateReportDialog(1, 'explosion', test_explosion_data)
    dialog.exec()
    
    sys.exit(app.exec())
