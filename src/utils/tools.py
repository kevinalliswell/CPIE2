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
        defaults = {
            "version": "未知", "author": "北京科技大学",
            "description": "CPIE-3000A 煤粉着火点及爆炸性检测系统",
            "release_date": "未知", "copyright": "© 北京科技大学",
            "contact": "", "website": "", "build_date": "未知",
            "python_version": "未知", "platforms": [],
        }
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                raise ValueError("软件信息必须为对象")
            defaults.update(loaded)
        except (OSError, ValueError) as exc:
            logger.warning("软件信息不可用，使用默认字段: %s", exc)
        return defaults

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