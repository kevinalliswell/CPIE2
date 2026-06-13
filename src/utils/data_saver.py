# src/utils/data_saver.py
"""
数据保存工具模块
支持将实验数据保存为CSV、XLS、TXT格式
"""

import csv
import datetime
from typing import List, Optional
from PySide6.QtWidgets import QTableWidget, QFileDialog
from PySide6.QtCore import QObject, Signal

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class DataSaver(QObject):
    """
    数据保存器
    支持CSV、XLS、TXT格式的数据导出
    """
    
    # 信号定义
    save_progress = Signal(int)  # 保存进度信号
    save_finished = Signal(bool, str)  # 保存完成信号 (成功, 消息)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.supported_formats = ['csv', 'xls', 'txt']
        
    def save_data(self, data_table: QTableWidget, file_path: str = None, 
                  format_type: str = 'csv', include_headers: bool = True, 
                  experiment_info: dict = None) -> bool:
        """
        保存表格数据到文件
        
        Args:
            data_table: QTableWidget对象，包含要保存的数据
            file_path: 保存路径，如果为None则弹出文件选择对话框
            format_type: 文件格式 ('csv', 'xls', 'txt')
            include_headers: 是否包含表头
            experiment_info: 实验信息字典，包含实验基本信息
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 验证格式
            if format_type.lower() not in self.supported_formats:
                raise ValueError(f"不支持的格式: {format_type}")
            
            # 获取数据
            data = self._extract_table_data(data_table, include_headers, experiment_info)
            if not data:
                raise ValueError("没有数据可保存")
            
            # 如果没有指定路径，弹出文件选择对话框
            if file_path is None:
                file_path = self._get_save_file_path(format_type, experiment_info)
                if not file_path:
                    return False
            
            # 根据格式保存数据
            if format_type.lower() == 'csv':
                return self._save_csv(data, file_path)
            elif format_type.lower() == 'xls':
                return self._save_xls(data, file_path, experiment_info)
            elif format_type.lower() == 'txt':
                return self._save_txt(data, file_path)
                
        except Exception as e:
            self.save_finished.emit(False, f"保存失败: {str(e)}")
            return False
    
    def _extract_table_data(self, data_table: QTableWidget, include_headers: bool = True, 
                           experiment_info: dict = None) -> List[List[str]]:
        """
        从QTableWidget中提取数据
        
        Args:
            data_table: QTableWidget对象
            include_headers: 是否包含表头
            experiment_info: 实验信息字典
            
        Returns:
            List[List[str]]: 提取的数据列表
        """
        data = []
        
        # 添加实验信息（如果有）
        if experiment_info:
            data.extend(self._format_experiment_info(experiment_info))
            data.append([])  # 空行分隔
        
        # 添加表头
        if include_headers:
            headers = []
            for col in range(data_table.columnCount()):
                header_item = data_table.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else f"列{col+1}")
            data.append(headers)
        
        # 添加数据行
        for row in range(data_table.rowCount()):
            row_data = []
            for col in range(data_table.columnCount()):
                item = data_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        
        return data
    
    def _format_experiment_info(self, experiment_info: dict) -> List[List[str]]:
        """
        格式化实验信息为表格行
        
        Args:
            experiment_info: 实验信息字典
            
        Returns:
            List[List[str]]: 格式化的实验信息行
        """
        info_rows = []
        
        # 实验基本信息
        basic_info = [
            ["实验信息", ""],
            ["实验ID", experiment_info.get("experiment_id", "")],
            ["实验名称", experiment_info.get("experiment_name", "")],
            ["样品名称", experiment_info.get("sample_name", "")],
            ["样品重量", f"{experiment_info.get('sample_weight', 0):.3f} g"],
            ["实验类型", experiment_info.get("experiment_type", "")],
            ["操作员", experiment_info.get("operator", "")],
            ["开始时间", experiment_info.get("start_time", "")],
            ["结束时间", experiment_info.get("end_time", "")],
            ["描述", experiment_info.get("description", "")],
        ]
        
        info_rows.extend(basic_info)
        
        # 实验参数（如果有）
        if "experiment_params" in experiment_info:
            info_rows.append(["", ""])
            info_rows.append(["实验参数", ""])
            params = experiment_info["experiment_params"]
            for key, value in params.items():
                if key not in ["project_name", "sample_name", "sample_weight", "operator", "notes", "experiment_type"]:
                    info_rows.append([key, str(value)])
        
        # 分析结果（如果有）
        if "analysis_results" in experiment_info:
            info_rows.append(["", ""])
            info_rows.append(["分析结果", ""])
            results = experiment_info["analysis_results"]
            for key, value in results.items():
                info_rows.append([key, str(value)])
        
        return info_rows
    
    def _get_save_file_path(self, format_type: str, experiment_info: dict = None) -> Optional[str]:
        """
        获取保存文件路径
        
        Args:
            format_type: 文件格式
            experiment_info: 实验信息字典
            
        Returns:
            Optional[str]: 文件路径，如果取消则返回None
        """
        # 生成默认文件名
        if experiment_info:
            default_name = self._generate_filename_from_experiment_info(experiment_info, format_type)
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"实验数据_{timestamp}.{format_type.lower()}"
        
        # 文件过滤器
        filters = {
            'csv': "CSV文件 (*.csv)",
            'xls': "Excel文件 (*.xlsx)",
            'txt': "文本文件 (*.txt)"
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            f"保存实验数据为{format_type.upper()}格式",
            default_name,
            filters.get(format_type.lower(), "所有文件 (*.*)")
        )
        
        return file_path if file_path else None
    
    def _generate_filename_from_experiment_info(self, experiment_info: dict, format_type: str) -> str:
        """
        根据实验信息生成文件名
        
        Args:
            experiment_info: 实验信息字典
            format_type: 文件格式
            
        Returns:
            str: 生成的文件名
        """
        # 获取基本信息
        experiment_name = experiment_info.get("experiment_name", "未知实验")
        sample_name = experiment_info.get("sample_name", "未知样品")
        operator = experiment_info.get("operator", "未知操作员")
        experiment_type = experiment_info.get("experiment_type", "未知类型")
        
        # 获取时间信息
        start_time = experiment_info.get("start_time", "")
        if start_time:
            try:
                # 解析时间字符串
                if "T" in start_time:
                    # ISO格式: 2024-01-01T10:00:00
                    dt = datetime.datetime.fromisoformat(start_time.replace("T", " "))
                else:
                    # 标准格式: 2024-01-01 10:00:00
                    dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                time_str = dt.strftime("%Y%m%d_%H%M%S")
            except (ValueError, TypeError):
                time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理文件名中的非法字符
        def clean_filename(name):
            # Windows文件名非法字符
            illegal_chars = r'<>:"/\|?*'
            for char in illegal_chars:
                name = name.replace(char, '_')
            # 限制长度
            return name[:20] if len(name) > 20 else name
        
        # 生成文件名组件
        clean_experiment_name = clean_filename(experiment_name)
        clean_sample_name = clean_filename(sample_name)
        clean_operator = clean_filename(operator)
        clean_experiment_type = clean_filename(experiment_type)
        
        # 构建文件名: 实验名称_样品名称_操作员_实验类型_时间.格式
        filename = f"{clean_experiment_name}_{clean_sample_name}_{clean_operator}_{clean_experiment_type}_{time_str}.{format_type.lower()}"
        
        # 确保文件名不会太长（Windows限制255字符，我们限制在150字符以内）
        if len(filename) > 150:
            # 如果太长，简化格式：实验名称_样品名称_时间.格式
            filename = f"{clean_experiment_name}_{clean_sample_name}_{time_str}.{format_type.lower()}"
            
            # 如果还是太长，进一步简化：实验名称_时间.格式
            if len(filename) > 150:
                filename = f"{clean_experiment_name}_{time_str}.{format_type.lower()}"
                
                # 如果还是太长，使用最简格式：时间.格式
                if len(filename) > 150:
                    filename = f"实验数据_{time_str}.{format_type.lower()}"
        
        return filename
    
    def _save_csv(self, data: List[List[str]], file_path: str) -> bool:
        """
        保存为CSV格式
        
        Args:
            data: 数据列表
            file_path: 文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                for i, row in enumerate(data):
                    writer.writerow(row)
                    # 发送进度信号
                    progress = int((i + 1) / len(data) * 100)
                    self.save_progress.emit(progress)
            
            self.save_finished.emit(True, f"CSV文件保存成功: {file_path}")
            return True
            
        except Exception as e:
            self.save_finished.emit(False, f"CSV保存失败: {str(e)}")
            return False
    
    def _save_xls(self, data: List[List[str]], file_path: str, experiment_info: dict = None) -> bool:
        """
        保存为Excel格式
        
        Args:
            data: 数据列表
            file_path: 文件路径
            experiment_info: 实验信息字典
            
        Returns:
            bool: 保存是否成功
        """
        if not OPENPYXL_AVAILABLE:
            self.save_finished.emit(False, "Excel保存失败: 未安装openpyxl库")
            return False
        
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "实验数据"
            
            # 设置表头样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # 计算表头行位置
            header_row = 1
            if experiment_info:
                header_row = len(self._format_experiment_info(experiment_info)) + 2  # 实验信息 + 空行 + 表头
            
            for row_idx, row in enumerate(data, 1):
                for col_idx, value in enumerate(row, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    
                    # 设置样式
                    if row_idx == header_row:
                        # 表头行
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                    elif experiment_info and row_idx < header_row:
                        # 实验信息行
                        if col_idx == 1:  # 第一列（标签列）
                            cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal="left", vertical="center")
                    else:
                        # 数据行
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # 发送进度信号
                progress = int(row_idx / len(data) * 100)
                self.save_progress.emit(progress)
            
            # 自动调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (TypeError, AttributeError):
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(file_path)
            self.save_finished.emit(True, f"Excel文件保存成功: {file_path}")
            return True
            
        except Exception as e:
            self.save_finished.emit(False, f"Excel保存失败: {str(e)}")
            return False
    
    def _save_txt(self, data: List[List[str]], file_path: str) -> bool:
        """
        保存为TXT格式
        
        Args:
            data: 数据列表
            file_path: 文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as txtfile:
                for i, row in enumerate(data):
                    # 使用制表符分隔
                    line = '\t'.join(str(cell) for cell in row)
                    txtfile.write(line + '\n')
                    
                    # 发送进度信号
                    progress = int((i + 1) / len(data) * 100)
                    self.save_progress.emit(progress)
            
            self.save_finished.emit(True, f"文本文件保存成功: {file_path}")
            return True
            
        except Exception as e:
            self.save_finished.emit(False, f"文本保存失败: {str(e)}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的格式列表
        
        Returns:
            List[str]: 支持的格式列表
        """
        return self.supported_formats.copy()
    
    def is_format_supported(self, format_type: str) -> bool:
        """
        检查格式是否支持
        
        Args:
            format_type: 格式类型
            
        Returns:
            bool: 是否支持
        """
        return format_type.lower() in self.supported_formats
    
    def check_dependencies(self) -> dict:
        """
        检查依赖库是否可用
        
        Returns:
            dict: 依赖库状态
        """
        return {
            'openpyxl': OPENPYXL_AVAILABLE,
            'csv': True,  # 内置库
        }


class DataExportDialog:
    """
    数据导出对话框
    提供格式选择和保存选项
    """
    
    @staticmethod
    def show_export_dialog(data_table: QTableWidget, parent=None, experiment_info: dict = None) -> bool:
        """
        显示数据导出对话框
        
        Args:
            data_table: 要导出的数据表格
            parent: 父窗口
            experiment_info: 实验信息字典
            
        Returns:
            bool: 是否成功导出
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QCheckBox, QMessageBox
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("导出实验数据")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout()
        
        # 格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("导出格式:"))
        format_combo = QComboBox()
        format_combo.addItems(['CSV', 'XLS', 'TXT'])
        format_layout.addWidget(format_combo)
        layout.addLayout(format_layout)
        
        # 选项
        include_headers = QCheckBox("包含表头")
        include_headers.setChecked(True)
        layout.addWidget(include_headers)
        
        # 按钮
        button_layout = QHBoxLayout()
        export_btn = QPushButton("导出")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(export_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # 连接信号
        export_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.Accepted:
            # 执行导出
            format_type = format_combo.currentText().lower()
            saver = DataSaver()
            
            # 连接信号以显示进度
            def on_progress(progress):
                export_btn.setText(f"导出中... {progress}%")
            
            def on_finished(success, message):
                if success:
                    QMessageBox.information(dialog, "成功", message)
                else:
                    QMessageBox.critical(dialog, "错误", message)
            
            saver.save_progress.connect(on_progress)
            saver.save_finished.connect(on_finished)
            
            return saver.save_data(
                data_table, 
                format_type=format_type, 
                include_headers=include_headers.isChecked(),
                experiment_info=experiment_info
            )
        
        return False
