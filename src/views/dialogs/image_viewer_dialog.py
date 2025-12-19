"""
图片查看对话框
用于查看实验火焰图片
"""

import os
import shutil
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QStandardPaths


class ImageViewerDialog(QDialog):
    """
    图片查看对话框
    支持显示640x480尺寸的火焰图片
    """
    
    def __init__(self, test_data: Dict, parent=None, experiment_id: Optional[str] = None, sample_name: Optional[str] = None):
        super().__init__(parent)
        
        self.test_data = test_data
        self.image_path = test_data.get('image_path', '')
        self.experiment_id = experiment_id or ''
        self.sample_name = sample_name or ''
        
        self.setup_ui()
        self.load_image()
    
    def setup_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle(f"火焰图片 - 测试{self.test_data.get('test_sequence', '')}")
        self.setModal(True)
        self.resize(680, 540)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 图片标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(640, 480)
        self.image_label.setStyleSheet("""
            QLabel {
                background: #000;
                border: 2px solid rgba(0, 217, 255, 0.3);
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.image_label)
        
        # 信息标签
        self.create_info_section(layout)
        
        # 按钮区域
        self.create_button_section(layout)
        
        # 对话框样式
        self.setStyleSheet("""
            QDialog {
                background: #1a1a2e;
            }
        """)
    
    def create_info_section(self, parent_layout):
        """创建信息区域"""
        info_text = f"测试序号: {self.test_data.get('test_sequence', 'N/A')}  |  " \
                   f"火焰长度: {self.test_data.get('flame_length_mm', 0):.1f} mm"
        
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #aaa; font-size: 10px;")
        parent_layout.addWidget(info_label)
    
    def create_button_section(self, parent_layout):
        """创建按钮区域"""
        btn_layout = QHBoxLayout()
        
        # 另存为按钮
        save_as_btn = QPushButton("另存为")
        save_as_btn.setFixedSize(100, 40)
        save_as_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #000;
                border-radius: 5px;
                font-size: 12px;
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
        save_as_btn.clicked.connect(self.save_image_as)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d9ff,
                    stop: 1 #0096b8
                );
                border: none;
                color: #000;
                border-radius: 5px;
                font-size: 12px;
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
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_as_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        parent_layout.addLayout(btn_layout)
    
    def load_image(self):
        """加载图片"""
        if not self.image_path:
            self.show_error("未指定图片路径")
            return
        
        if not os.path.exists(self.image_path):
            self.show_error(f"图片文件不存在\n{self.image_path}")
            return
        
        # 加载图片
        pixmap = QPixmap(self.image_path)
        if pixmap.isNull():
            self.show_error("无法加载图片")
            return
        
        # 缩放图片以适应640x480，保持宽高比
        scaled_pixmap = pixmap.scaled(
            640, 480, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
    
    def show_error(self, message: str):
        """显示错误信息"""
        self.image_label.setText(message)
        self.image_label.setStyleSheet("""
            QLabel {
                background: #000;
                border: 2px solid rgba(255, 85, 85, 0.3);
                border-radius: 5px;
                color: #ff5555;
                font-size: 12px;
            }
        """)
    
    def save_image_as(self):
        """另存为图片"""
        if not self.image_path or not os.path.exists(self.image_path):
            QMessageBox.warning(self, "警告", "图片文件不存在，无法保存！")
            return
        
        # 获取桌面路径
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        
        # 生成默认文件名
        default_filename = self.generate_default_filename()
        
        # 获取原始图片扩展名
        _, ext = os.path.splitext(self.image_path)
        if not ext:
            ext = '.jpg'
        
        # 完整的默认保存路径
        default_save_path = os.path.join(desktop_path, default_filename + ext)
        
        # 弹出保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            default_save_path,
            f"图片文件 (*{ext});;所有文件 (*.*)"
        )
        
        # 如果用户取消了保存
        if not file_path:
            return
        
        # 复制文件
        try:
            shutil.copy(self.image_path, file_path)
            QMessageBox.information(self, "成功", f"图片已保存至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存图片失败:\n{str(e)}")
    
    def generate_default_filename(self) -> str:
        """生成默认文件名"""
        # 获取测试序号和火焰长度
        test_seq = self.test_data.get('test_sequence', '')
        flame_length = self.test_data.get('flame_length_mm', 0)
        
        # 构建文件名各部分
        parts = []
        
        # 添加实验编号
        if self.experiment_id:
            # 清理文件名中的非法字符
            exp_id_clean = self.sanitize_filename(self.experiment_id)
            parts.append(exp_id_clean)
        
        # 添加样品名称
        if self.sample_name:
            sample_clean = self.sanitize_filename(self.sample_name)
            parts.append(sample_clean)
        
        # 添加测试序号
        if test_seq:
            parts.append(f"test_{test_seq}")
        
        # 添加火焰长度
        if flame_length:
            parts.append(f"flame_{flame_length:.1f}mm")
        
        # 如果没有任何信息，使用默认名称
        if not parts:
            parts.append("flame_image")
        
        return "_".join(parts)
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows文件名非法字符: < > : " / \ | ? *
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
if __name__ == "__main__":
    """测试图片查看对话框"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 测试数据
    test_data = {
        'test_sequence': 1,
        'flame_length_mm': 285.5,
        'capture_time': '2025-11-13 09:45:23',
        'image_path': 'data/images/explosion/EXP20251113001/test1_max_flame.jpg'
    }
    
    dialog = ImageViewerDialog(test_data)
    dialog.exec()
    
    sys.exit(0)

