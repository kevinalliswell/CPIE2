import json
import os
from typing import Optional

from .path_manager import PathManager
from .logger import get_logger
from .password_hash import hash_password, is_hashed, verify_password


class PasswordManager:
    """
    管理员口令管理工具（用于删除记录等敏感操作的确认）

    口令以带盐的 PBKDF2-SHA256 哈希保存在 configs/password_config.json 中；
    旧版本保存的明文 `admin_password` 会在首次加载时自动升级为哈希。
    未配置时使用默认口令 DEFAULT_PASSWORD，建议在"历史数据"页面通过 Ctrl+Alt+P 修改。
    """

    DEFAULT_PASSWORD = "1952"
    MIN_PASSWORD_LENGTH = 4

    def __init__(self, config_file: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config_file = config_file or PathManager.get_config_path('password_config.json')
        self._password_hash: Optional[str] = None
        self.load_config()

    # ------------------------------------------------------------------ 持久化
    def load_config(self):
        """加载配置；明文旧配置自动升级为哈希"""
        self._password_hash = None
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                stored_hash = config.get("admin_password_hash")
                legacy_plain = config.get("admin_password")
                if is_hashed(stored_hash):
                    self._password_hash = stored_hash
                elif legacy_plain:
                    # 旧版本明文存储：升级为哈希并回写，不再保留明文
                    self._password_hash = hash_password(str(legacy_plain))
                    self.save_config()
                    self.logger.info("已将旧版明文口令配置升级为哈希存储")
        except Exception as e:
            self.logger.error(f"加载密码配置失败: {e}")
            self._password_hash = None

        if self._password_hash is None:
            self._password_hash = hash_password(self.DEFAULT_PASSWORD)

    def save_config(self):
        """保存配置（只写哈希，不写明文）"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({"admin_password_hash": self._password_hash}, f, indent=2)
        except Exception as e:
            self.logger.error(f"保存密码配置失败: {e}")

    # ------------------------------------------------------------------ 校验/修改
    def verify_password(self, password: str) -> bool:
        """验证口令"""
        return verify_password(password, self._password_hash)

    def is_default_password(self) -> bool:
        """当前口令是否仍为默认口令"""
        return self.verify_password(self.DEFAULT_PASSWORD)

    def change_password(self, old_password: str, new_password: str) -> bool:
        """修改口令：旧口令正确且新口令长度达标时保存"""
        if not self.verify_password(old_password):
            return False
        if not new_password or len(new_password) < self.MIN_PASSWORD_LENGTH:
            return False
        self._password_hash = hash_password(new_password)
        self.save_config()
        self.logger.info("管理员口令已修改")
        return True
