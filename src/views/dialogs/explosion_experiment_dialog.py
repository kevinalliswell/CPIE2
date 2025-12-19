"""
爆炸性实验参数设置对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Signal


class ExplosionExperimentDialog(QDialog):
    """
    爆炸性实验参数设置对话框
    
    字段说明：
    - 实验编号（experiment_id）：自动生成（EXP-YYYYMMDD-XXX），用于识别实验
    - 实验名称（experiment_name）：可选，有默认值（煤粉爆炸性测试）
    - 样品名称（sample_name）：必填
    - 委托单位（client）：可选，有默认值
    - 操作员（operator）：可选，有默认值
    - 备注（note）：可选
    """
    
    # 信号：对话框确认时发出，传递实验配置数据
    confirmed = Signal(dict)
    
    def __init__(self, experiment_id: str, parent=None):
        super().__init__(parent)
        self.experiment_id = experiment_id
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("爆炸性实验参数设置")
        self.setMinimumWidth(600)
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
        exp_name_layout = self.create_form_row("实验名称:", placeholder="默认：煤粉爆炸性测试")
        self.exp_name_input = exp_name_layout[1]
        self.exp_name_input.setText("煤粉爆炸性测试")  # 设置默认值
        main_layout.addLayout(exp_name_layout[0])
        
        # 样品名称（必填）
        sample_name_layout = self.create_form_row("样品名称:", placeholder="请输入样品名称")
        self.sample_name_input = sample_name_layout[1]
        main_layout.addLayout(sample_name_layout[0])
        
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
        
        # 按钮区域
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
    
    def create_form_row(self, label_text: str, placeholder: str = "", readonly: bool = False):
        """
        创建表单行
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
        """应用对话框样式"""
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
        """确认按钮点击"""
        # 验证必填项
        experiment_name = self.exp_name_input.text().strip()
        sample_name = self.sample_name_input.text().strip()
        
        # 实验名称可选，使用默认值
        if not experiment_name:
            experiment_name = "煤粉爆炸性测试"
        
        if not sample_name:
            QMessageBox.warning(
                self,
                "提示",
                "请填写样品名称！"
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
        
        # 构建描述信息（包含所有实验相关信息）
        description_parts = [f"实验编号：{self.experiment_id}"]
        if client:
            description_parts.append(f"委托单位：{client}")
        if operator:
            description_parts.append(f"操作员：{operator}")
        if note:
            description_parts.append(f"备注：{note}")
        
        description = " | ".join(description_parts)
        
        # 收集所有参数
        config = {
            # 数据库所需字段
            "experiment_name": experiment_name,  # 实验名称
            "sample_name": sample_name,          # 样品名称
            "client": client,                    # 委托单位（数据库字段）
            "operator": operator,                # 操作员（数据库字段）
            "description": description,          # 描述（包含编号、单位、操作员、备注）
            
            # 额外字段（用于UI显示和报告生成）
            "experiment_id": self.experiment_id,  # 实验编号
            "note": note                          # 备注
        }
        
        # 发出确认信号
        self.confirmed.emit(config)
        
        # 关闭对话框
        self.accept()
    
    def get_config_data(self) -> dict:
        """获取配置数据（不关闭对话框）"""
        # 获取实验名称和样品名称
        experiment_name = self.exp_name_input.text().strip()
        # 实验名称可选，使用默认值
        if not experiment_name:
            experiment_name = "煤粉爆炸性测试"
        
        sample_name = self.sample_name_input.text().strip()
        
        # 获取委托单位和操作员，使用默认值
        client = self.client_input.text().strip()
        if not client:
            client = "北京科技大学"
        
        operator = self.operator_input.text().strip()
        if not operator:
            operator = "实验员"
        
        # 获取备注
        note = self.note_input.toPlainText().strip()
        
        # 构建描述信息（包含所有实验相关信息）
        description_parts = [f"实验编号：{self.experiment_id}"]
        if client:
            description_parts.append(f"委托单位：{client}")
        if operator:
            description_parts.append(f"操作员：{operator}")
        if note:
            description_parts.append(f"备注：{note}")
        
        description = " | ".join(description_parts)
        
        # 收集所有参数
        config = {
            # 数据库所需字段
            "experiment_name": experiment_name,  # 实验名称
            "sample_name": sample_name,          # 样品名称
            "client": client,                    # 委托单位（数据库字段）
            "operator": operator,                # 操作员（数据库字段）
            "description": description,          # 描述（包含编号、单位、操作员、备注）
            
            # 额外字段（用于UI显示和报告生成）
            "experiment_id": self.experiment_id,  # 实验编号
            "note": note                          # 备注
        }
        
        return config

