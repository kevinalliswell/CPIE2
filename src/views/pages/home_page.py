

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from utils.tools import Tools
from utils.path_manager import PathManager
    
class HomePage(QWidget):
    """主页"""
    def __init__(self):
        super().__init__()

        # 软件信息
        self.software_info = Tools.load_software_info()
        self.init_ui()
        
    def init_ui(self):

        # 设置帮助页面对象名称，用于样式应用
        self.setObjectName("helpPage")

        layout = QVBoxLayout(self)
        logo_label = QLabel()
        pixmap = QPixmap(PathManager.get_resources_path("images/USTB_logo_horizontal.png"))
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)

        welcome_text = QLabel("欢迎使用")
        welcome_text.setAlignment(Qt.AlignCenter)
        welcome_text.setStyleSheet("font-size: 36px; font-weight: bold;")

        title_text = QLabel(f"{self.software_info['description']}")
        title_text.setAlignment(Qt.AlignCenter)
        title_text.setStyleSheet("font-size: 28px; font-weight: bold;")

        # 软件信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)
        
        # 版本信息
        version_text = QLabel(f"版本: {self.software_info['version']}")
        version_text.setAlignment(Qt.AlignCenter)
        version_text.setStyleSheet("font-size: 14px; color: #888888;")
        
        # # 作者信息
        # author_text = QLabel(f"作者: {self.software_info['author']}")
        # author_text.setAlignment(Qt.AlignCenter)
        # author_text.setStyleSheet("font-size: 14px; color: #888888;")
        
        # 发布日期
        release_text = QLabel(f"发布日期: {self.software_info['release_date']}")
        release_text.setAlignment(Qt.AlignCenter)
        release_text.setStyleSheet("font-size: 14px; color: #888888;")
        
        # 版权信息
        copyright_text = QLabel(self.software_info['copyright'])
        copyright_text.setAlignment(Qt.AlignCenter)
        copyright_text.setStyleSheet("font-size: 12px; color: #888888;")

        # 版权说明
        copyright_info_text = QLabel("版权所有 © 2025 北京科技大学")
        copyright_info_text.setAlignment(Qt.AlignCenter)
        copyright_info_text.setStyleSheet("font-size: 12px; color: #888888;")
        
        # 联系方式
        contact_text = QLabel(f"联系方式: {self.software_info['contact']}")
        contact_text.setAlignment(Qt.AlignCenter)
        contact_text.setStyleSheet("font-size: 12px; color: #888888;")
        
        # 网站
        website_text = QLabel(f"官网: {self.software_info['website']}")
        website_text.setAlignment(Qt.AlignCenter)
        website_text.setStyleSheet("font-size: 12px; color: #888888;")
        
        info_layout.addWidget(version_text)
        # info_layout.addWidget(author_text)
        info_layout.addWidget(release_text)
        # info_layout.addWidget(copyright_text)
        info_layout.addWidget(copyright_info_text)
        # info_layout.addWidget(contact_text)
        info_layout.addWidget(website_text)

        layout.addStretch()
        layout.addWidget(logo_label)
        layout.addWidget(welcome_text)
        layout.addWidget(title_text)
        layout.addSpacing(20)  # 添加间距
        layout.addWidget(info_widget)
        layout.addStretch()

