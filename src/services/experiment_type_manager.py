# src/services/experiment_type_manager.py
"""
实验类型管理器
统一管理标准实验类型和自定义实验类型，解决枚举与动态配置的冲突问题
"""

from enum import Enum
from importlib import import_module
from typing import Any, Dict, List, Optional
import json
import logging
import os

from src.utils.path_manager import PathManager


logger = logging.getLogger(__name__)

try:
    experiment_modes_module = import_module("src.services.experiment_modes")
except ImportError as exc:
    experiment_modes_module = None
    EXPERIMENT_MODES_IMPORT_ERROR = exc
else:
    EXPERIMENT_MODES_IMPORT_ERROR = None

ExperimentModeManager = getattr(experiment_modes_module, "ExperimentModeManager", None)
ExperimentType = getattr(experiment_modes_module, "ExperimentType", None)

STANDARD_EXPERIMENT_MODE_NAMES = {
    "GB_13241_2017": "REDUCIBILITY",
    "GB_13242_2017": "LOW_TEMP_DEGRADATION",
    "GB_13240_2018": "FREE_SWELLING",
}


class ExperimentTypeCategory(Enum):
    """实验类型分类"""
    STANDARD = "standard"
    CUSTOM = "custom"


class ExperimentTypeInfo:
    """实验类型信息类"""

    def __init__(
        self,
        type_id: str,
        name: str,
        description: str = "",
        category: ExperimentTypeCategory = ExperimentTypeCategory.STANDARD,
        enabled: bool = True,
        **kwargs,
    ):
        self.type_id = type_id
        self.name = name
        self.description = description
        self.category = category
        self.enabled = enabled
        self.extra_data = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type_id": self.type_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "enabled": self.enabled,
            **self.extra_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentTypeInfo':
        """从字典创建实例"""
        return cls(
            type_id=data["type_id"],
            name=data["name"],
            description=data.get("description", ""),
            category=ExperimentTypeCategory(data.get("category", "standard")),
            enabled=data.get("enabled", True),
            **{
                k: v
                for k, v in data.items()
                if k not in ["type_id", "name", "description", "category", "enabled"]
            },
        )


class ExperimentTypeManager:
    """实验类型管理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.experiment_mode_manager = self._create_experiment_mode_manager()
        self._standard_types = self._initialize_standard_types()
        self._custom_types: Dict[str, ExperimentTypeInfo] = {}
        self._load_custom_types()

    def _create_experiment_mode_manager(self):
        if ExperimentModeManager is None:
            if EXPERIMENT_MODES_IMPORT_ERROR is not None:
                self.logger.warning(
                    "实验模式模块不可用，标准实验阶段信息将返回空列表: %s",
                    EXPERIMENT_MODES_IMPORT_ERROR,
                )
            return None

        try:
            return ExperimentModeManager()
        except Exception as exc:
            self.logger.warning("初始化实验模式管理器失败，标准实验阶段信息将返回空列表: %s", exc)
            return None

    def _initialize_standard_types(self) -> Dict[str, ExperimentTypeInfo]:
        """初始化标准实验类型"""
        return {
            "GB_13241_2017": ExperimentTypeInfo(
                type_id="GB_13241_2017",
                name="GB/T 13241-2017 铁矿石还原性测定方法",
                description="标准铁矿石还原性测定实验",
                category=ExperimentTypeCategory.STANDARD,
                enabled=True,
            ),
            "GB_13242_2017": ExperimentTypeInfo(
                type_id="GB_13242_2017",
                name="GB/T 13242-2017 铁矿石低温粉化试验方法",
                description="低温条件下铁矿石粉化特性测试",
                category=ExperimentTypeCategory.STANDARD,
                enabled=True,
            ),
            "GB_13240_2018": ExperimentTypeInfo(
                type_id="GB_13240_2018",
                name="GB/T 13240-2018 球团矿自由膨胀指数测定方法",
                description="球团矿在还原气氛下的膨胀特性测试",
                category=ExperimentTypeCategory.STANDARD,
                enabled=True,
            ),
        }

    def _get_config_path(self) -> str:
        return PathManager.get_config_path("experiment_modes.json")

    def _load_custom_types(self):
        """从配置文件加载自定义实验类型"""
        try:
            config_path = self._get_config_path()
            if not os.path.exists(config_path):
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            custom_modes = config.get("experiment_modes", {}).get("custom_modes", {})
            for mode_id, mode_data in custom_modes.items():
                if mode_data.get("enabled", True):
                    self._custom_types[mode_id] = ExperimentTypeInfo(
                        type_id=mode_id,
                        name=mode_data.get("name", mode_id),
                        description=mode_data.get("description", ""),
                        category=ExperimentTypeCategory.CUSTOM,
                        enabled=mode_data.get("enabled", True),
                        created_by=mode_data.get("created_by", "unknown"),
                        created_time=mode_data.get("created_time", ""),
                        stages=mode_data.get("stages", []),
                    )
        except Exception as e:
            self.logger.error(f"加载自定义实验类型失败: {str(e)}")

    def get_all_types(self) -> Dict[str, ExperimentTypeInfo]:
        """获取所有实验类型"""
        all_types = {}
        all_types.update(self._standard_types)
        all_types.update(self._custom_types)
        return all_types

    def get_standard_types(self) -> Dict[str, ExperimentTypeInfo]:
        """获取标准实验类型"""
        return self._standard_types.copy()

    def get_custom_types(self) -> Dict[str, ExperimentTypeInfo]:
        """获取自定义实验类型"""
        return self._custom_types.copy()

    def get_enabled_types(self) -> Dict[str, ExperimentTypeInfo]:
        """获取启用的实验类型"""
        return {k: v for k, v in self.get_all_types().items() if v.enabled}

    def get_type_by_id(self, type_id: str) -> Optional[ExperimentTypeInfo]:
        """根据ID获取实验类型"""
        return self.get_all_types().get(type_id)

    def get_type_by_name(self, name: str) -> Optional[ExperimentTypeInfo]:
        """根据名称获取实验类型"""
        for type_info in self.get_all_types().values():
            if type_info.name == name:
                return type_info
        return None

    def is_standard_type(self, type_id: str) -> bool:
        """判断是否为标准实验类型"""
        return type_id in self._standard_types

    def is_custom_type(self, type_id: str) -> bool:
        """判断是否为自定义实验类型"""
        return type_id in self._custom_types

    def get_type_category(self, type_id: str) -> Optional[ExperimentTypeCategory]:
        """获取实验类型分类"""
        type_info = self.get_type_by_id(type_id)
        return type_info.category if type_info else None

    def get_experiment_type_for_mode_id(self, mode_id: str) -> Optional[str]:
        """根据模式ID获取对应的实验类型"""
        if not mode_id:
            return None

        if mode_id in STANDARD_EXPERIMENT_MODE_NAMES:
            return mode_id

        if self.is_custom_type(mode_id):
            return mode_id

        return None

    def get_mode_id_for_experiment_type(self, experiment_type: str) -> Optional[str]:
        """根据实验类型获取对应的模式ID"""
        if not experiment_type:
            return None

        if experiment_type in self._standard_types or experiment_type in self._custom_types:
            return experiment_type

        return None

    def add_custom_type(self, type_info: ExperimentTypeInfo) -> bool:
        """添加自定义实验类型"""
        try:
            self._custom_types[type_info.type_id] = type_info
            self._save_custom_types()
            return True
        except Exception as e:
            self.logger.error(f"添加自定义实验类型失败: {str(e)}")
            return False

    def remove_custom_type(self, type_id: str) -> bool:
        """删除自定义实验类型"""
        try:
            if type_id in self._custom_types:
                del self._custom_types[type_id]
                self._save_custom_types()
                return True
            return False
        except Exception as e:
            self.logger.error(f"删除自定义实验类型失败: {str(e)}")
            return False

    def update_custom_type(self, type_id: str, type_info: ExperimentTypeInfo) -> bool:
        """更新自定义实验类型"""
        try:
            if type_id in self._custom_types:
                self._custom_types[type_id] = type_info
                self._save_custom_types()
                return True
            return False
        except Exception as e:
            self.logger.error(f"更新自定义实验类型失败: {str(e)}")
            return False

    def _save_custom_types(self):
        """保存自定义实验类型到配置文件"""
        try:
            config_path = self._get_config_path()
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            experiment_modes = config.setdefault("experiment_modes", {})
            experiment_modes["custom_modes"] = {
                type_id: type_info.to_dict()
                for type_id, type_info in self._custom_types.items()
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存自定义实验类型失败: {str(e)}")
            raise

    def get_type_display_list(self) -> List[tuple]:
        """获取用于UI显示的类型列表"""
        display_list = []

        for type_info in self._standard_types.values():
            if type_info.enabled:
                display_list.append((type_info.name, type_info.type_id))

        for type_info in self._custom_types.values():
            if type_info.enabled:
                display_list.append((type_info.name, type_info.type_id))

        return display_list

    def validate_type_id(self, type_id: str) -> bool:
        """验证类型ID是否有效"""
        return type_id in self.get_all_types()

    def get_type_stages(self, type_id: str) -> List[Dict[str, Any]]:
        """获取实验类型的阶段信息"""
        type_info = self.get_type_by_id(type_id)
        if not type_info:
            return []

        if self.is_standard_type(type_id):
            if self.experiment_mode_manager is None or ExperimentType is None:
                return []

            enum_name = STANDARD_EXPERIMENT_MODE_NAMES.get(type_id)
            experiment_type = getattr(ExperimentType, enum_name, None) if enum_name else None
            if experiment_type is None:
                self.logger.warning("未找到标准实验类型映射: %s", type_id)
                return []

            try:
                return self.experiment_mode_manager.get_experiment_program(experiment_type)
            except Exception as e:
                self.logger.error(f"获取标准类型阶段信息失败: {str(e)}")
                return []

        return type_info.extra_data.get("stages", [])
