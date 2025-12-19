"""
配置管理：支持包内默认配置、用户目录配置和当前目录配置
优先级：当前目录 > 用户目录 > 包内默认配置
"""
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
	"""配置管理器"""

	def __init__(self, config_file: Optional[str] = None):
		"""
		初始化配置管理器
		
		Args:
			config_file: 可选，指定配置文件路径。如果为 None，则按优先级查找：
				1. 当前目录的 config.json
				2. 用户目录的 config.json (~/.flamekit/config.json 或 %APPDATA%/flamekit/config.json)
				3. 包内默认配置
		"""
		if config_file:
			self.config_file = config_file
		else:
			self.config_file = self._find_config_file()
		
		self.config: Dict[str, Any] = {}
		self.load_config()

	def _get_package_default_config_path(self) -> Path:
		"""获取包内默认配置文件路径"""
		return Path(__file__).parent / "config_default.json"

	def _get_user_config_dir(self) -> Path:
		"""获取用户配置目录"""
		if os.name == 'nt':  # Windows
			appdata = os.getenv('APPDATA', os.path.expanduser('~'))
			return Path(appdata) / "flamekit"
		else:  # Linux/Mac
			return Path.home() / ".flamekit"

	def _get_user_config_file(self) -> Path:
		"""获取用户配置文件路径"""
		return self._get_user_config_dir() / "config.json"

	def _find_config_file(self) -> str:
		"""
		按优先级查找配置文件
		优先级：当前目录 > 用户目录 > 包内默认配置
		"""
		# 1. 检查当前目录
		current_dir_config = Path("config.json")
		if current_dir_config.exists():
			return str(current_dir_config.resolve())

		# 2. 检查用户目录
		user_config = self._get_user_config_file()
		if user_config.exists():
			return str(user_config)

		# 3. 使用包内默认配置，并复制到用户目录
		default_config = self._get_package_default_config_path()
		if default_config.exists():
			# 确保用户配置目录存在
			user_config_dir = self._get_user_config_dir()
			user_config_dir.mkdir(parents=True, exist_ok=True)
			
			# 复制默认配置到用户目录
			try:
				shutil.copy2(default_config, user_config)
				print(f"已创建用户配置文件: {user_config}")
			except Exception as e:
				print(f"复制默认配置到用户目录失败: {e}，将使用包内默认配置")
				return str(default_config)
			
			return str(user_config)
		
		# 如果包内默认配置也不存在，返回用户目录路径（将在 load_config 中创建）
		return str(self._get_user_config_file())

	def load_config(self):
		"""加载配置文件"""
		config_path = Path(self.config_file)
		
		if config_path.exists():
			try:
				with open(config_path, 'r', encoding='utf-8') as f:
					self.config = json.load(f)
				print(f"配置已加载: {self.config_file}")
			except Exception as e:
				print(f"加载配置文件失败: {e}")
				self.config = self._load_default_config()
		else:
			# 配置文件不存在，从包内默认配置加载
			self.config = self._load_default_config()
			# 保存到用户目录
			if not str(config_path).startswith(str(self._get_package_default_config_path())):
				self.save_config()

	def _load_default_config(self) -> Dict[str, Any]:
		"""从包内默认配置加载"""
		default_config = self._get_package_default_config_path()
		if default_config.exists():
			try:
				with open(default_config, 'r', encoding='utf-8') as f:
					return json.load(f)
			except Exception as e:
				print(f"加载包内默认配置失败: {e}")
		return self._get_default_config()

	def save_config(self) -> bool:
		"""保存配置文件"""
		# 如果当前使用的是包内默认配置，则保存到用户目录
		if self.config_file == str(self._get_package_default_config_path()):
			user_config = self._get_user_config_file()
			user_config_dir = user_config.parent
			user_config_dir.mkdir(parents=True, exist_ok=True)
			self.config_file = str(user_config)
		
		try:
			config_path = Path(self.config_file)
			config_path.parent.mkdir(parents=True, exist_ok=True)
			with open(config_path, 'w', encoding='utf-8') as f:
				json.dump(self.config, f, indent=4, ensure_ascii=False)
			print(f"配置已保存: {self.config_file}")
			return True
		except Exception as e:
			print(f"保存配置文件失败: {e}")
			return False

	def get(self, key: str, default: Any = None) -> Any:
		keys = key.split('.')
		value: Any = self.config
		for k in keys:
			if isinstance(value, dict):
				value = value.get(k)
			else:
				return default
		return value if value is not None else default

	def set(self, key: str, value: Any, save: bool = True):
		keys = key.split('.')
		cfg = self.config
		for k in keys[:-1]:
			if k not in cfg:
				cfg[k] = {}
			cfg = cfg[k]
		cfg[keys[-1]] = value
		if save:
			self.save_config()

	def _get_default_config(self) -> Dict[str, Any]:
		"""获取默认配置（当所有配置文件都不可用时使用）"""
		return {
			"camera": {
				"exposure_us": 4000,
				"resolution_index": 1,
				"force_mono": True,
				"capture_duration": 1.0
			},
			"calibration": {
				"mm_per_pixel": 0.3152,
				"reference_length_mm": 200.0
			},
			"analysis": {
				"binary_threshold": 0,
				"min_flame_area": 1000,
				"use_otsu": True
			},
			"paths": {
				"temp_dir": "./temp_captures",
				"output_dir": "./results"
			},
			"playback": {
				"default_fps": 30,
				"speed_options": [0.25, 0.5, 1.0, 2.0, 4.0]
			}
		}


_config_instance = None


def get_config() -> ConfigManager:
	global _config_instance
	if _config_instance is None:
		_config_instance = ConfigManager()
	return _config_instance


