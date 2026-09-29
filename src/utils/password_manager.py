"""Persist the confirmation password without plaintext or silent resets."""
import json
import os
import tempfile
from typing import Optional

from .path_manager import PathManager
from .logger import get_logger
from .password_hash import hash_password, is_hashed, verify_password


class PasswordManager:
    """Manage the password used to confirm deletion of experiment records."""

    DEFAULT_PASSWORD = "1952"
    MIN_PASSWORD_LENGTH = 4

    def __init__(self, config_file: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config_file = config_file or PathManager.get_config_path('password_config.json')
        self._password_hash = None
        self.load_config()

    def load_config(self):
        self._password_hash = None
        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                config = json.load(file)
            if not isinstance(config, dict):
                raise ValueError('invalid password configuration')
            # An invalid configured password must never enable the default.
            if 'admin_password_hash' in config:
                stored = config['admin_password_hash']
                if not is_hashed(stored):
                    raise ValueError('invalid password hash format')
                self._password_hash = stored
            elif isinstance(config.get('admin_password'), str) and config['admin_password']:
                self._password_hash = hash_password(config['admin_password'])
                if self.save_config():
                    self.logger.info('已将旧版口令配置升级为哈希存储')
            else:
                raise ValueError('missing password configuration')
        except FileNotFoundError:
            self._password_hash = hash_password(self.DEFAULT_PASSWORD)
        except (OSError, ValueError, TypeError) as error:
            self.logger.error(f'加载密码配置失败，密码确认已禁用: {error}')

    def save_config(self, password_hash=None) -> bool:
        """Atomically replace the file, preserving its previous contents on failure."""
        target_hash = self._password_hash if password_hash is None else password_hash
        temporary = None
        try:
            directory = os.path.dirname(os.path.abspath(self.config_file))
            os.makedirs(directory, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                             prefix='.password-', delete=False) as file:
                temporary = file.name
                json.dump({'admin_password_hash': target_hash}, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.config_file)
            return True
        except (OSError, ValueError, TypeError) as error:
            self.logger.error(f'保存密码配置失败: {error}')
            return False
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    self.logger.warning('无法清理未完成的密码配置临时文件')

    def verify_password(self, password: str) -> bool:
        return verify_password(password, self._password_hash)

    def is_default_password(self) -> bool:
        return self.verify_password(self.DEFAULT_PASSWORD)

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.verify_password(old_password):
            return False
        if not isinstance(new_password, str) or len(new_password) < self.MIN_PASSWORD_LENGTH:
            return False
        new_hash = hash_password(new_password)
        if not self.save_config(new_hash):
            return False
        self._password_hash = new_hash
        self.logger.info('管理员确认口令已修改')
        return True
