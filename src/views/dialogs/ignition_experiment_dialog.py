"""
着火点实验参数设置对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton,
    QWidget, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import json


class IgnitionExperimentDialog(QDialog):
    """
    着火点实验参数设置对话框
    
    字段说明：
    - 实验编号（experiment_id）：自动生成（IGN-YYYYMMDD-XXX），用于识别实验
    - 实验名称（experiment_name）：可选，有默认值（煤粉着火点测试）
    - 样品名称（sample_names）：必填，6个样品输入框
    - 委托单位（client）：可选，有默认值
    - 操作员（operator）：可选，有默认值
    - 备注（note）：可选
    """
    
    # 信号：对话框确认时发出，传递实验配置数据
    confirmed = Signal(dict)
    
    def __init__(self, experiment_id: str, parent=None):
        super().__init__(parent)
        self.experiment_id = experiment_id
        self.sample_name_inputs = []  # 样品名称输入框列表
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("着火点实验参数设置")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 实验编号（只读）
        exp_id_layout = self.create_form_row("实验编号:", readonly=True)
        self.exp_id_input = exp_id_layout[1]
        self.exp_id_input.setText(self.experiment_id)
        main_layout.addLayout(exp_id_layout[0])
        
        # 实验名称（可选，有默认值）
        exp_name_layout = self.create_form_row("实验名称:", placeholder="默认：煤粉着火点测试")
        self.exp_name_input = exp_name_layout[1]
        self.exp_name_input.setText("煤粉着火点测试")  # 设置默认值
        main_layout.addLayout(exp_name_layout[0])
        
        # 样品名称输入区域（6个样品）
        sample_label = QLabel("样品名称:")
        sample_label.setStyleSheet("color: #aaa; font-size: 14px; background: transparent;")
        main_layout.addWidget(sample_label)
        
        sample_group = self.create_sample_group(6)
        main_layout.addWidget(sample_group)
        
        # 委托单位（可选，有默认值）
        client_layout = self.create_form_row("委托单位:", placeholder="默认：北京科技大学")
        self.client_input = client_layout[1]
        main_layout.addLayout(client_layout[0])
        
        # 操作员（可选，有默认值）
        operator_layout = self.create_form_row("操作员:", placeholder="默认：实验员")
        self.operator_input = operator_layout[1]
        main_layout.addLayout(operator_layout[0])
        
        # 备注
        note_label = QLabel("备注:")
        note_label.setStyleSheet("color: #aaa; font-size: 14px; background: transparent;")
        main_layout.addWidget(note_label)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("请输入备注信息...")
        self.note_input.setMaximumHeight(80)
        main_layout.addWidget(self.note_input)
        
        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        self._style_button(cancel_btn, "#6c757d")
        
        confirm_btn = QPushButton("确认启动")
        confirm_btn.clicked.connect(self.on_confirm)
        self._style_button(confirm_btn, "#28a745")
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        main_layout.addLayout(button_layout)
    
    def create_sample_group(self, count=6) -> QWidget:
        """
        创建所有样品名称输入（两列网格布局）
        优化标签和输入框宽度比例
        """
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(15, 12, 15, 12)
        grid.setColumnStretch(1, 1)  # 第1列输入框可拉伸
        grid.setColumnStretch(3, 1)  # 第3列输入框可拉伸

        for i in range(count):
            row = i % 3
            col = i // 3

            sample_index = i + 1
            name_label = QLabel(f"样品#{sample_index}:")
            name_label.setStyleSheet("""
                color: #aaa; 
                font-size: 13px;
                background: transparent;
            """)
            name_label.setFixedWidth(70)  # 固定标签宽度为70px

            name_input = QLineEdit()
            name_input.setPlaceholderText("请输入样品名称")
            name_input.setMinimumWidth(150)  # 最小宽度150px，可拉伸
            self.sample_name_inputs.append(name_input)

            grid.addWidget(name_label, row, col * 2, Qt.AlignmentFlag.AlignRight)
            grid.addWidget(name_input, row, col * 2 + 1)

        container.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        return container
    
    def create_form_row(self, label_text: str, placeholder: str = "", readonly: bool = False):
        """
        创建表单行（保持与爆炸性实验对话框一致）
        Returns:
            (layout, input_widget)
        """
        layout = QHBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #aaa; font-size: 14px; min-width: 80px; background: transparent;")
        
        input_widget = QLineEdit()
        input_widget.setPlaceholderText(placeholder)
        
        if readonly:
            input_widget.setReadOnly(True)
        
        layout.addWidget(label)
        layout.addWidget(input_widget)
        
        return (layout, input_widget)
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #16213e,
                    stop: 1 #0f3460
                );
            }
            
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
                font-size: 14px;
            }
            
            QLineEdit:focus {
                border: 1px solid #00d9ff;
                background-color: rgba(255, 255, 255, 0.08);
            }
            
            QLineEdit[readOnly="true"] {
                background-color: rgba(255, 255, 255, 0.02);
                color: #888;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
                font-size: 14px;
            }
            
            QTextEdit:focus {
                border: 1px solid #00d9ff;
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
    
    def _style_button(self, button, color):
        """设置按钮样式"""
        button.setMinimumHeight(36)
        button.setMinimumWidth(100)
        button.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 25px;
            }}
            QPushButton:hover {{
                background: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background: {self._darken_color(color, 0.8)};
            }}
        """)
    
    def _darken_color(self, color, factor=0.85):
        """使颜色变暗"""
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color
    
    def on_confirm(self):
        """确认按钮点击处理"""
        # 获取实验名称（可选，使用默认值）
        experiment_name = self.exp_name_input.text().strip()
        if not experiment_name:
            experiment_name = "煤粉着火点测试"
        
        # 收集样品名称
        sample_names = []
        for input_widget in self.sample_name_inputs:
            name = input_widget.text().strip()
            sample_names.append(name)
        
        # 检查是否至少有一个样品有名称
        if not any(sample_names):
            QMessageBox.warning(
                self,
                "提示",
                "请至少为一个样品输入名称！"
            )
            return
        
        # 获取委托单位和操作员，使用默认值
        client = self.client_input.text().strip()
        if not client:
            client = "北京科技大学"
        
        operator = self.operator_input.text().strip()
        if not operator:
            operator = "实验员"
        
        # 获取备注
        note = self.note_input.toPlainText().strip()
        
        # 构建描述信息
        description_parts = [f"实验编号：{self.experiment_id}"]
        if client:
            description_parts.append(f"委托单位：{client}")
        if operator:
            description_parts.append(f"操作员：{operator}")
        if note:
            description_parts.append(f"备注：{note}")
        
        description = " | ".join(description_parts)
        
        # 构建配置数据（用于数据库存储和UI显示）
        config_data = {
            # 数据库所需字段
            'experiment_name': experiment_name,  # 实验名称
            'sample_names': json.dumps(sample_names, ensure_ascii=False),  # JSON字符串存储
            'client': client,
            'operator': operator,
            'description': description,
            
            # 额外字段（用于UI显示）
            'experiment_id': self.experiment_id,
            'sample_names_list': sample_names,  # 原始列表
            'note': note
        }
        
        # 发出信号
        self.confirmed.emit(config_data)
        
        # 关闭对话框
        self.accept()
    
    def get_config_data(self) -> dict:
        """获取配置数据"""
        # 获取实验名称（可选，使用默认值）
        experiment_name = self.exp_name_input.text().strip()
        if not experiment_name:
            experiment_name = "煤粉着火点测试"
        
        # 收集样品名称
        sample_names = [input_widget.text().strip() for input_widget in self.sample_name_inputs]
        
        # 获取委托单位和操作员，使用默认值
        client = self.client_input.text().strip()
        if not client:
            client = "北京科技大学"
        
        operator = self.operator_input.text().strip()
        if not operator:
            operator = "实验员"
        
        # 获取备注
        note = self.note_input.toPlainText().strip()
        
        # 构建描述信息
        description_parts = [f"实验编号：{self.experiment_id}"]
        if client:
            description_parts.append(f"委托单位：{client}")
        if operator:
            description_parts.append(f"操作员：{operator}")
        if note:
            description_parts.append(f"备注：{note}")
        
        description = " | ".join(description_parts)
        
        return {
            # 数据库所需字段
            'experiment_name': experiment_name,
            'sample_names': json.dumps(sample_names, ensure_ascii=False),
            'client': client,
            'operator': operator,
            'description': description,
            
            # 额外字段
            'experiment_id': self.experiment_id,
            'sample_names_list': sample_names,
            'note': note
        }

