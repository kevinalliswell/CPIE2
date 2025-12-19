"""
导出对话框组件
支持导出实验数据为Excel、CSV或PDF格式
"""

import os
from typing import List
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QButtonGroup,
    QLineEdit, QFileDialog, QCheckBox, QGroupBox, QMessageBox
)
from PySide6.QtCore import Signal


class ExportDialog(QDialog):
    """
    导出对话框
    选择导出格式、文件路径和导出选项
    """
    
    # 信号
    export_confirmed = Signal(dict)  # 导出配置字典
    
    def __init__(self, experiment_ids: List[int], exp_type: str, parent=None):
        super().__init__(parent)
        
        self.experiment_ids = experiment_ids
        self.exp_type = exp_type  # explosion 或 ignition
        self.export_config = {}
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("导出实验数据")
        self.setModal(True)
        self.setFixedSize(600, 800)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        exp_type_text = {
            'explosion': '爆炸性',
            'ignition': '着火点'
        }.get(self.exp_type, '实验')
        
        title_label = QLabel(f"导出 {len(self.experiment_ids)} 条{exp_type_text}实验数据")
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #00d9ff; margin-bottom: 5px;")
        main_layout.addWidget(title_label)
        
        # 添加标题下方的间距
        main_layout.addSpacing(5)
        
        # 格式选择
        format_group = self.create_format_group()
        main_layout.addWidget(format_group)
        
        # 文件路径选择
        path_group = self.create_path_group()
        main_layout.addWidget(path_group)
        
        # 导出选项
        options_group = self.create_options_group()
        main_layout.addWidget(options_group)
        
        main_layout.addStretch()
        
        # 按钮
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)
    
    def create_format_group(self) -> QGroupBox:
        """创建格式选择组"""
        group = QGroupBox("导出格式")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.format_group = QButtonGroup(self)
        
        # 检查 openpyxl 是否安装
        import importlib.util
        excel_available = importlib.util.find_spec("openpyxl") is not None
        
        # Excel格式
        if excel_available:
            self.excel_radio = QRadioButton("📊 Excel (.xlsx) - 推荐")
            self.excel_radio.setChecked(True)
            excel_hint_text = "   适合数据分析，支持多个工作表"
        else:
            self.excel_radio = QRadioButton("📊 Excel (.xlsx) - 需要安装openpyxl")
            self.excel_radio.setEnabled(False)
            excel_hint_text = "   需要安装: pip install openpyxl"
        
        self.format_group.addButton(self.excel_radio, 0)
        layout.addWidget(self.excel_radio)
        
        excel_hint = QLabel(excel_hint_text)
        if excel_available:
            excel_hint.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px; margin-top: 2px;")
        else:
            excel_hint.setStyleSheet("color: #ff9800; font-size: 11px; margin-left: 24px; margin-top: 2px;")
        layout.addWidget(excel_hint)
        
        layout.addSpacing(8)
        
        # CSV格式
        self.csv_radio = QRadioButton("📄 CSV (.csv)")
        self.format_group.addButton(self.csv_radio, 1)
        layout.addWidget(self.csv_radio)
        
        csv_hint = QLabel("   纯文本格式，兼容性好")
        csv_hint.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px; margin-top: 2px;")
        layout.addWidget(csv_hint)
        
        # 设置默认选中项（在所有按钮创建后）
        if excel_available:
            self.excel_radio.setChecked(True)
        else:
            self.csv_radio.setChecked(True)  # Excel不可用时默认选择CSV
        
        # PDF格式（暂不支持）
        self.pdf_radio = QRadioButton("📑 PDF (.pdf) - 开发中")
        self.pdf_radio.setEnabled(False)
        self.format_group.addButton(self.pdf_radio, 2)
        layout.addWidget(self.pdf_radio)
        
        return group
    
    def create_path_group(self) -> QGroupBox:
        """创建文件路径选择组"""
        group = QGroupBox("保存位置")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择保存路径...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setMinimumHeight(32)
        
        # 默认路径
        default_filename = f"实验数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(os.path.expanduser("~"), "Desktop", default_filename)
        self.path_edit.setText(default_path)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(90)
        browse_btn.setMinimumHeight(32)
        browse_btn.clicked.connect(self.on_browse_clicked)
        
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(browse_btn)
        
        return group
    
    def create_options_group(self) -> QGroupBox:
        """创建导出选项组"""
        group = QGroupBox("导出选项")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # 包含基本信息
        self.include_basic_checkbox = QCheckBox("包含基本信息（样品名称、检测人员等）")
        self.include_basic_checkbox.setChecked(True)
        layout.addWidget(self.include_basic_checkbox)
        
        # 包含测试结果
        self.include_results_checkbox = QCheckBox("包含测试结果")
        self.include_results_checkbox.setChecked(True)
        layout.addWidget(self.include_results_checkbox)
        
        # 根据实验类型显示不同的选项
        if self.exp_type == 'explosion':
            # 爆炸性实验：包含测试轮次详情
            self.include_rounds_checkbox = QCheckBox("包含测试轮次详情（仅Excel格式）")
            self.include_rounds_checkbox.setChecked(False)
            layout.addWidget(self.include_rounds_checkbox)
            
            rounds_hint = QLabel("   将在单独的工作表中列出每个实验的所有测试轮次数据")
            rounds_hint.setStyleSheet("color: #888; font-size: 10px; margin-left: 24px; margin-top: -5px;")
            layout.addWidget(rounds_hint)
            
        elif self.exp_type == 'ignition':
            # 着火点实验：包含样品详情
            self.include_samples_checkbox = QCheckBox("包含样品详情（仅Excel格式）")
            self.include_samples_checkbox.setChecked(False)
            layout.addWidget(self.include_samples_checkbox)
            
            samples_hint = QLabel("   将在单独的工作表中列出每个实验的所有样品数据")
            samples_hint.setStyleSheet("color: #888; font-size: 10px; margin-left: 24px; margin-top: -5px;")
            layout.addWidget(samples_hint)
        
        # 打开文件
        self.open_after_export_checkbox = QCheckBox("导出完成后打开文件")
        self.open_after_export_checkbox.setChecked(True)
        layout.addWidget(self.open_after_export_checkbox)
        
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(110, 40)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("开始导出")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.setFixedSize(110, 40)
        self.export_btn.clicked.connect(self.on_export_clicked)
        layout.addWidget(self.export_btn)
        
        return layout
    
    def setup_connections(self):
        """设置信号连接"""
        # 格式变更时更新文件扩展名
        self.format_group.buttonClicked.connect(self.on_format_changed)
    
    # ==================== 事件处理 ====================
    
    def on_format_changed(self, button):
        """格式变更"""
        current_path = self.path_edit.text()
        if not current_path:
            return
        
        # 获取新扩展名
        if button == self.excel_radio:
            new_ext = '.xlsx'
        elif button == self.csv_radio:
            new_ext = '.csv'
        elif button == self.pdf_radio:
            new_ext = '.pdf'
        else:
            return
        
        # 替换扩展名
        base_path = os.path.splitext(current_path)[0]
        new_path = base_path + new_ext
        self.path_edit.setText(new_path)
    
    def on_browse_clicked(self):
        """浏览按钮点击"""
        # 获取当前格式
        if self.excel_radio.isChecked():
            filter_str = "Excel文件 (*.xlsx)"
            default_ext = ".xlsx"
        elif self.csv_radio.isChecked():
            filter_str = "CSV文件 (*.csv)"
            default_ext = ".csv"
        else:
            filter_str = "所有文件 (*.*)"
            default_ext = ""
        
        # 打开文件对话框
        default_path = self.path_edit.text() or os.path.join(
            os.path.expanduser("~"), "Desktop", f"实验数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}{default_ext}"
        )
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择保存路径",
            default_path,
            filter_str
        )
        
        if file_path:
            self.path_edit.setText(file_path)
    
    def on_export_clicked(self):
        """导出按钮点击"""
        # 检查Excel格式是否需要库
        if self.excel_radio.isChecked():
            import importlib.util
            if importlib.util.find_spec("openpyxl") is None:
                QMessageBox.warning(
                    self,
                    "警告",
                    "导出Excel需要openpyxl库，请先安装：\npip install openpyxl\n\n或者选择CSV格式导出。"
                )
                return
        
        # 获取文件路径
        file_path = self.path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "警告", "请选择保存路径！")
            return
        
        # 检查目录是否存在
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            QMessageBox.warning(self, "警告", f"目录不存在：{dir_path}")
            return
        
        # 收集导出配置
        self.export_config = {
            'file_path': file_path,
            'format': 'excel' if self.excel_radio.isChecked() else ('csv' if self.csv_radio.isChecked() else 'pdf'),
            'experiment_ids': self.experiment_ids,
            'exp_type': self.exp_type,
            'include_basic': self.include_basic_checkbox.isChecked(),
            'include_results': self.include_results_checkbox.isChecked(),
            'open_after_export': self.open_after_export_checkbox.isChecked(),
        }
        
        # 根据实验类型添加特定选项
        if self.exp_type == 'explosion' and hasattr(self, 'include_rounds_checkbox'):
            self.export_config['include_rounds'] = self.include_rounds_checkbox.isChecked()
        elif self.exp_type == 'ignition' and hasattr(self, 'include_samples_checkbox'):
            self.export_config['include_samples'] = self.include_samples_checkbox.isChecked()
        
        print(f"[导出] 配置: {self.export_config}")
        
        # 发出信号
        self.export_confirmed.emit(self.export_config)
        
        # 关闭对话框
        self.accept()


if __name__ == "__main__":
    """测试导出对话框"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 测试数据
    test_ids = [1, 2, 3]
    
    dialog = ExportDialog(test_ids, 'explosion')
    dialog.export_confirmed.connect(lambda config: print(f"\n导出配置:\n{config}"))
    
    result = dialog.exec()
    print(f"\n对话框结果: {'确认' if result else '取消'}")
    
    sys.exit(0)

