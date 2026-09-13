import os
import json

import yaml
from PySide6.QtWidgets import QApplication
from .path_manager import PathManager
from .logger import get_logger
from utils.logger import LoggerManager

class Tools:
    """工具类"""
    @staticmethod
    def load_software_info():
        logger = LoggerManager.get_logger(__name__)
        info_path = PathManager.get_config_path("software.info")
        if not os.path.exists(info_path):
            logger.error(f"软件信息文件不存在: {info_path}")
            # 兜底信息必须包含页面会直接索引的全部键（HomePage/AboutPage 使用 contact、website）
            return {
                "version": "1.0.0",
                "author": "北京科技大学",
                "description": "CPIE-3000A 煤粉着火点及爆炸性检测系统",
                "release_date": "2025-11-21",
                "copyright": "© 2025 北京科技大学",
                "contact": "",
                "website": "",
                "build_date": "",
                "python_version": "",
                "platforms": [],
            }
        with open(info_path, "r", encoding="utf-8") as f:
            logger.info(f"软件信息文件加载成功: {info_path}")
            return json.load(f)

    @staticmethod
    def apply_stylesheet(theme="dark"):
        logger = LoggerManager.get_logger(__name__)
        qss_file = "dark_theme.qss" if theme == "dark" else "light_theme.qss"
        # 样式文件在 resources/styles/ 目录中
        qss_path = PathManager.get_styles_path(qss_file)
        logger.info(f"qss_path: {qss_path}")
        if os.path.exists(qss_path):
            app = QApplication.instance()
            if app is not None:
                with open(qss_path, "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
            else:
                logger.error("警告: QApplication 实例不存在，无法应用样式表")
        else:
            logger.error(f"样式文件不存在: {qss_path}")

    @staticmethod
    def load_config(config_path):
        """加载配置文件"""
        logger = LoggerManager.get_logger(__name__)
        # 配置文件路径 在configs目录下
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return None