#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
配置管理模块
Configuration Manager Module
"""
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import yaml
import cv2

# 动态添加src路径以支持导入
if getattr(sys, 'frozen', False):
    # 打包后的环境
    current_dir = Path(sys.executable).parent
else:
    # 开发环境
    current_dir = Path(__file__).resolve().parent
    
# 尝试导入PathManager
try:
    from utils.path_manager import PathManager
    HAS_PATH_MANAGER = True
except ImportError:
    # 如果无法导入，使用备用方案
    HAS_PATH_MANAGER = False
    import tempfile


class FlameAnalyzerConfig:
    """火焰分析仪配置类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径,如果为None则使用默认路径
        """
        if config_path is None:
            # 使用PathManager获取配置目录（打包后安全）
            if HAS_PATH_MANAGER:
                config_dir = PathManager.get_config_path()
                config_path = os.path.join(config_dir, "flame_analyzer_config.yaml")
            else:
                # 备用方案：使用用户临时目录
                config_dir = os.path.join(tempfile.gettempdir(), "CPIE_configs")
                os.makedirs(config_dir, exist_ok=True)
                config_path = os.path.join(config_dir, "flame_analyzer_config.yaml")
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> dict:
        """加载YAML配置文件"""
        try:
            if not self.config_path.exists():
                print(f"配置文件不存在，将创建默认配置: {self.config_path}")
                # 获取默认配置并保存
                default_config = self._get_default_config()
                self._config = default_config
                try:
                    self.save_config()
                except:
                    pass  # 如果保存失败，仍然返回默认配置
                return default_config
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                raise ValueError("配置文件为空")
            
            return config
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            # 返回默认配置
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            'image_processing': {
                'flame_threshold': 128,
                'mm_per_pixel': 0.1
            },
            'paths': {
                'history_csv': 'data/exp_explosion/history_explosion.csv',
                'exp_data_json': 'data/exp_explosion/explosion_experiment_data.json',
                'temp_folder_prefix': 'flame_analysis_temp'
            },
            'image_formats': ['.jpg', '.jpeg', '.png'],
            'ui': {
                'window_title': '火焰图像分析',
                'progress_update_interval': 10,
                'max_display_failed_files': 5
            },
            'opencv': {
                'font': 'FONT_HERSHEY_SIMPLEX',
                'font_scale': 0.5,
                'text_color': [0, 255, 0],
                'text_thickness': 2,
                'bbox_color': [0, 255, 0],
                'bbox_thickness': 1
            },
            'performance': {
                'stream_processing': True,
                'batch_size': 50
            },
            'logging': {
                'enable': True,
                'level': 'INFO',
                'file': 'logs/flame_analyzer.log'
            }
        }
    
    def _validate_config(self):
        """验证配置参数"""
        # 验证必要的配置项
        required_keys = ['image_processing', 'paths', 'image_formats', 'ui', 'opencv']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"配置文件缺少必要项: {key}")
        
        # 验证数值范围
        threshold = self.flame_threshold
        if not 0 <= threshold <= 255:
            raise ValueError(f"flame_threshold 必须在 0-255 之间,当前值: {threshold}")
        
        if self.mm_per_pixel <= 0:
            raise ValueError(f"mm_per_pixel 必须大于0,当前值: {self.mm_per_pixel}")
    
    # ========== 图像处理参数 ==========
    @property
    def flame_threshold(self) -> int:
        """火焰检测阈值"""
        return self._config['image_processing']['flame_threshold']
    
    @property
    def mm_per_pixel(self) -> float:
        """每像素对应的毫米数 (mm/pixel)"""
        return self._config['image_processing']['mm_per_pixel']
    
    # ========== 路径配置 ==========
    @property
    def history_csv_path(self) -> Path:
        """历史数据CSV路径"""
        return Path(self._config['paths']['history_csv'])
    
    @property
    def exp_data_json_path(self) -> Path:
        """实验数据JSON路径"""
        return Path(self._config['paths']['exp_data_json'])
    
    @property
    def temp_folder(self) -> str:
        """临时文件夹路径"""
        folder = self._config['paths'].get('temp_folder', 'data/temp_captures')
        return Path(folder)
    
    @property
    def flame_output_folder(self) -> Path:
        """火焰分析结果保存文件夹"""
        folder = self._config['paths'].get('flame_output_folder', 'data/flame_results')
        return Path(folder)
    
    @property
    def max_flame_save_folder(self) -> Path:
        """最大火焰图片保存文件夹"""
        folder = self._config['paths'].get('max_flame_save_folder', 'data/max_flame_images')
        return Path(folder)
    
    # ========== 图像格式 ==========
    @property
    def image_formats(self) -> Tuple[str, ...]:
        """支持的图像格式"""
        return tuple(self._config['image_formats'])
    
    # ========== UI配置 ==========
    @property
    def window_title(self) -> str:
        """窗口标题"""
        return self._config['ui']['window_title']
    
    @property
    def progress_update_interval(self) -> int:
        """进度更新间隔"""
        return self._config['ui']['progress_update_interval']
    
    @property
    def max_display_failed_files(self) -> int:
        """最多显示的失败文件数量"""
        return self._config['ui']['max_display_failed_files']
    
    # ========== OpenCV参数 ==========
    @property
    def cv_font(self) -> int:
        """OpenCV字体"""
        font_name = self._config['opencv']['font']
        return getattr(cv2, font_name, cv2.FONT_HERSHEY_SIMPLEX)
    
    @property
    def font_scale(self) -> float:
        """字体缩放"""
        return self._config['opencv']['font_scale']
    
    @property
    def text_color(self) -> Tuple[int, int, int]:
        """文字颜色 (BGR)"""
        return tuple(self._config['opencv']['text_color'])
    
    @property
    def text_thickness(self) -> int:
        """文字粗细"""
        return self._config['opencv']['text_thickness']
    
    @property
    def bbox_color(self) -> Tuple[int, int, int]:
        """边界框颜色 (BGR)"""
        return tuple(self._config['opencv']['bbox_color'])
    
    @property
    def bbox_thickness(self) -> int:
        """边界框粗细"""
        return self._config['opencv']['bbox_thickness']
    
    # ========== 性能配置 ==========
    @property
    def stream_processing(self) -> bool:
        """是否启用流式处理"""
        return self._config['performance'].get('stream_processing', True)
    
    @property
    def batch_size(self) -> int:
        """批处理大小"""
        return self._config['performance'].get('batch_size', 50)
    
    # ========== 日志配置 ==========
    @property
    def logging_enabled(self) -> bool:
        """是否启用日志"""
        return self._config['logging'].get('enable', True)
    
    @property
    def log_level(self) -> str:
        """日志级别"""
        return self._config['logging'].get('level', 'INFO')
    
    @property
    def log_file(self) -> Path:
        """日志文件路径"""
        return Path(self._config['logging'].get('file', 'logs/flame_analyzer.log'))
    
    def save_config(self, output_path: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            output_path: 输出路径,如果为None则覆盖原文件
        """
        save_path = Path(output_path) if output_path else self.config_path
        
        try:
            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            
            print(f"配置已保存到: {save_path}")
        except Exception as e:
            print(f"✗ 保存标定参数失败: {e}")
            raise
    
    def update_config(self, key_path: str, value):
        """
        更新配置项
        
        Args:
            key_path: 配置项路径,使用点号分隔,如 'image_processing.flame_threshold'
            value: 新值
        """
        keys = key_path.split('.')
        config = self._config
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        
        # 重新验证配置
        self._validate_config()
    
    def __repr__(self) -> str:
        return f"FlameAnalyzerConfig(config_path='{self.config_path}')"
    
    def print_config(self):
        """打印当前配置"""
        print("=" * 50)
        print("火焰分析仪配置")
        print("=" * 50)
        print(f"配置文件: {self.config_path}")
        print(f"\n图像处理:")
        print(f"  - 火焰阈值: {self.flame_threshold}")
        print(f"  - 像素比例: {self.mm_per_pixel} mm/pixel")
        print(f"\n路径配置:")
        print(f"  - 历史CSV: {self.history_csv_path}")
        print(f"  - 实验JSON: {self.exp_data_json_path}")
        print(f"\n图像格式: {', '.join(self.image_formats)}")
        print(f"\nUI配置:")
        print(f"  - 窗口标题: {self.window_title}")
        print(f"  - 进度更新间隔: {self.progress_update_interval}")
        print(f"\n性能配置:")
        print(f"  - 流式处理: {self.stream_processing}")
        print("=" * 50)


if __name__ == "__main__":
    # 测试配置类
    config = FlameAnalyzerConfig()
    config.print_config()
