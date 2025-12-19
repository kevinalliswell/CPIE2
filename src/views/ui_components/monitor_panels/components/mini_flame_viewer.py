"""
小型火焰图像查看器
适用于触摸屏显示火焰图像的紧凑版本
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
import numpy as np


class MiniFlameViewer(QFrame):
    """
    小型火焰图像查看器
    显示火焰图像的缩略版
    """
    
    def __init__(self, width: int = 380, height: int = 220, parent=None):
        super().__init__(parent)
        
        self.setObjectName("miniFlameViewer")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.view_width = width
        self.view_height = height
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("🔥 火焰图像")
        title_label.setObjectName("miniFlameTitle")
        title_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(title_label)
        
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setObjectName("miniFlameImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(self.view_width, self.view_height)
        self.image_label.setStyleSheet(
            "QLabel { "
            "background-color: #2c3e50; "
            "border: 2px solid #34495e; "
            "border-radius: 4px; "
            "color: #95a5a6; "
            "}"
        )
        self.image_label.setText("等待图像...")
        
        layout.addWidget(self.image_label)
        
        # 火焰长度标签
        self.length_label = QLabel("火焰长度: --")
        self.length_label.setObjectName("miniFlameLength")
        self.length_label.setStyleSheet("color: #7f8c8d;")
        self.length_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.length_label)
    
    def update_image(self, image_data):
        """
        更新火焰图像
        Args:
            image_data: numpy数组、QImage或QPixmap
        """
        try:
            if image_data is None:
                self.image_label.setText("无图像")
                return
            
            # 转换为QPixmap
            if isinstance(image_data, np.ndarray):
                # numpy数组转QImage
                if len(image_data.shape) == 2:
                    # 灰度图
                    height, width = image_data.shape
                    bytes_per_line = width
                    q_image = QImage(image_data.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
                else:
                    # 彩色图
                    height, width, channels = image_data.shape
                    bytes_per_line = channels * width
                    if channels == 3:
                        q_image = QImage(image_data.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                    elif channels == 4:
                        q_image = QImage(image_data.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
                    else:
                        self.image_label.setText("不支持的图像格式")
                        return
                
                pixmap = QPixmap.fromImage(q_image)
            
            elif isinstance(image_data, QImage):
                pixmap = QPixmap.fromImage(image_data)
            
            elif isinstance(image_data, QPixmap):
                pixmap = image_data
            
            else:
                self.image_label.setText("不支持的图像类型")
                return
            
            # 缩放到合适大小
            scaled_pixmap = pixmap.scaled(
                self.view_width, self.view_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
        
        except Exception as e:
            print(f"更新火焰图像失败: {e}")
            self.image_label.setText("图像显示错误")
    
    def set_flame_length(self, length: float):
        """
        设置火焰长度
        Args:
            length: 火焰长度（单位：像素或mm）
        """
        if length is None or length < 0:
            self.length_label.setText("火焰长度: --")
        else:
            self.length_label.setText(f"火焰长度: {length:.1f} mm")
    
    def clear(self):
        """清空图像"""
        self.image_label.clear()
        self.image_label.setText("等待图像...")
        self.length_label.setText("火焰长度: --")

