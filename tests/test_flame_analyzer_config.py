#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰分析器配置参数测试脚本
测试配置参数的获取和使用情况
"""

import sys
import os
from pathlib import Path
import yaml
import tempfile
import shutil

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from views.dialogs.flame_analyzer.config_manager import FlameAnalyzerConfig
from views.dialogs.flame_analyzer.flame_processor import FlameImageProcessor


class TestFlameAnalyzerConfig:
    """火焰分析器配置测试类"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        self.test_config_path = None
        self.temp_dir = None
    
    def setup(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="flame_test_")
        self.test_config_path = os.path.join(self.temp_dir, "test_flame_analyzer_config.yaml")
        
        # 创建测试配置文件
        test_config = {
            'image_processing': {
                'flame_threshold': 150,
                'mm_per_pixel': 0.816082
            },
            'paths': {
                'history_csv': 'data/exp_explosion/history_explosion.csv',
                'exp_data_json': 'data/exp_explosion/explosion_experiment_data.json',
                'temp_folder': 'data/temp_captures',
                'flame_output_folder': 'data/flame_results',
                'max_flame_save_folder': 'data/max_flame_images'
            },
            'image_formats': ['.jpg', '.jpeg', '.png', '.bmp'],
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
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.test_config_path), exist_ok=True)
        
        # 写入测试配置文件
        with open(self.test_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, allow_unicode=True, default_flow_style=False)
        
        print("✓ 测试环境准备完成\n")
    
    def teardown(self):
        """测试后清理"""
        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        print("\n✓ 测试环境清理完成")
    
    def assert_test(self, condition, test_name, error_msg=""):
        """断言测试"""
        self.total_tests += 1
        if condition:
            self.passed_tests += 1
            print(f"✓ {test_name}")
            return True
        else:
            self.failed_tests += 1
            print(f"✗ {test_name}")
            if error_msg:
                print(f"  错误: {error_msg}")
            return False
    
    def test_config_initialization(self):
        """测试配置对象初始化"""
        print("\n=== 测试配置对象初始化 ===")
        
        # 测试使用指定路径初始化
        config = FlameAnalyzerConfig(config_path=self.test_config_path)
        self.assert_test(
            config is not None,
            "配置对象创建成功",
            "配置对象为None"
        )
        
        # 测试配置文件路径
        self.assert_test(
            str(config.config_path) == self.test_config_path,
            "配置文件路径正确",
            f"期望: {self.test_config_path}, 实际: {config.config_path}"
        )
        
        return config
    
    def test_image_processing_params(self, config):
        """测试图像处理参数"""
        print("\n=== 测试图像处理参数 ===")
        
        # 测试 flame_threshold
        threshold = config.flame_threshold
        self.assert_test(
            isinstance(threshold, int) and 0 <= threshold <= 255,
            "flame_threshold 参数获取成功",
            f"值: {threshold}, 类型: {type(threshold)}"
        )
        self.assert_test(
            threshold == 150,
            "flame_threshold 值正确",
            f"期望: 150, 实际: {threshold}"
        )
        
        # 测试 mm_per_pixel
        mm_per_pixel = config.mm_per_pixel
        self.assert_test(
            isinstance(mm_per_pixel, (int, float)) and mm_per_pixel > 0,
            "mm_per_pixel 参数获取成功",
            f"值: {mm_per_pixel}, 类型: {type(mm_per_pixel)}"
        )
        self.assert_test(
            abs(mm_per_pixel - 0.816082) < 0.000001,
            "mm_per_pixel 值正确",
            f"期望: 0.816082, 实际: {mm_per_pixel}"
        )
    
    def test_path_params(self, config):
        """测试路径参数"""
        print("\n=== 测试路径参数 ===")
        
        # 测试 history_csv_path
        csv_path = config.history_csv_path
        self.assert_test(
            isinstance(csv_path, Path),
            "history_csv_path 类型正确",
            f"类型: {type(csv_path)}"
        )
        
        # 测试 exp_data_json_path
        json_path = config.exp_data_json_path
        self.assert_test(
            isinstance(json_path, Path),
            "exp_data_json_path 类型正确",
            f"类型: {type(json_path)}"
        )
        
        # 测试 flame_output_folder
        output_folder = config.flame_output_folder
        self.assert_test(
            isinstance(output_folder, Path),
            "flame_output_folder 类型正确",
            f"类型: {type(output_folder)}"
        )
        
        # 测试 max_flame_save_folder
        max_flame_folder = config.max_flame_save_folder
        self.assert_test(
            isinstance(max_flame_folder, Path),
            "max_flame_save_folder 类型正确",
            f"类型: {type(max_flame_folder)}"
        )
    
    def test_image_formats(self, config):
        """测试图像格式参数"""
        print("\n=== 测试图像格式参数 ===")
        
        formats = config.image_formats
        self.assert_test(
            isinstance(formats, tuple),
            "image_formats 类型正确",
            f"类型: {type(formats)}"
        )
        
        expected_formats = ('.jpg', '.jpeg', '.png', '.bmp')
        self.assert_test(
            formats == expected_formats,
            "image_formats 值正确",
            f"期望: {expected_formats}, 实际: {formats}"
        )
    
    def test_ui_params(self, config):
        """测试UI参数"""
        print("\n=== 测试UI参数 ===")
        
        # 测试 window_title
        title = config.window_title
        self.assert_test(
            isinstance(title, str) and len(title) > 0,
            "window_title 参数获取成功",
            f"值: {title}"
        )
        
        # 测试 progress_update_interval
        interval = config.progress_update_interval
        self.assert_test(
            isinstance(interval, int) and interval > 0,
            "progress_update_interval 参数获取成功",
            f"值: {interval}"
        )
        
        # 测试 max_display_failed_files
        max_display = config.max_display_failed_files
        self.assert_test(
            isinstance(max_display, int) and max_display > 0,
            "max_display_failed_files 参数获取成功",
            f"值: {max_display}"
        )
    
    def test_opencv_params(self, config):
        """测试OpenCV参数"""
        print("\n=== 测试OpenCV参数 ===")
        
        import cv2
        
        # 测试 cv_font
        font = config.cv_font
        self.assert_test(
            isinstance(font, int),
            "cv_font 参数获取成功",
            f"值: {font}, 类型: {type(font)}"
        )
        self.assert_test(
            font == cv2.FONT_HERSHEY_SIMPLEX,
            "cv_font 值正确",
            f"期望: {cv2.FONT_HERSHEY_SIMPLEX}, 实际: {font}"
        )
        
        # 测试 font_scale
        font_scale = config.font_scale
        self.assert_test(
            isinstance(font_scale, (int, float)) and font_scale > 0,
            "font_scale 参数获取成功",
            f"值: {font_scale}"
        )
        
        # 测试 text_color
        text_color = config.text_color
        self.assert_test(
            isinstance(text_color, tuple) and len(text_color) == 3,
            "text_color 参数获取成功",
            f"值: {text_color}"
        )
        
        # 测试 bbox_color
        bbox_color = config.bbox_color
        self.assert_test(
            isinstance(bbox_color, tuple) and len(bbox_color) == 3,
            "bbox_color 参数获取成功",
            f"值: {bbox_color}"
        )
    
    def test_performance_params(self, config):
        """测试性能参数"""
        print("\n=== 测试性能参数 ===")
        
        # 测试 stream_processing
        stream = config.stream_processing
        self.assert_test(
            isinstance(stream, bool),
            "stream_processing 参数获取成功",
            f"值: {stream}, 类型: {type(stream)}"
        )
        
        # 测试 batch_size
        batch_size = config.batch_size
        self.assert_test(
            isinstance(batch_size, int) and batch_size > 0,
            "batch_size 参数获取成功",
            f"值: {batch_size}"
        )
    
    def test_logging_params(self, config):
        """测试日志参数"""
        print("\n=== 测试日志参数 ===")
        
        # 测试 logging_enabled
        enabled = config.logging_enabled
        self.assert_test(
            isinstance(enabled, bool),
            "logging_enabled 参数获取成功",
            f"值: {enabled}"
        )
        
        # 测试 log_level
        log_level = config.log_level
        self.assert_test(
            isinstance(log_level, str) and log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            "log_level 参数获取成功",
            f"值: {log_level}"
        )
        
        # 测试 log_file
        log_file = config.log_file
        self.assert_test(
            isinstance(log_file, Path),
            "log_file 参数获取成功",
            f"值: {log_file}, 类型: {type(log_file)}"
        )
    
    def test_processor_uses_config(self, config):
        """测试处理器使用配置参数"""
        print("\n=== 测试处理器使用配置参数 ===")
        
        # 创建处理器
        processor = FlameImageProcessor(config)
        self.assert_test(
            processor is not None,
            "处理器创建成功",
            "处理器为None"
        )
        
        # 测试处理器是否正确使用配置
        self.assert_test(
            processor.config == config,
            "处理器配置对象正确",
            "配置对象不匹配"
        )
        
        # 测试处理器可以访问配置参数
        threshold = processor.config.flame_threshold
        self.assert_test(
            threshold == 150,
            "处理器可以访问 flame_threshold",
            f"值: {threshold}"
        )
        
        mm_per_pixel = processor.config.mm_per_pixel
        self.assert_test(
            abs(mm_per_pixel - 0.816082) < 0.000001,
            "处理器可以访问 mm_per_pixel",
            f"值: {mm_per_pixel}"
        )
    
    def test_config_save_and_load(self):
        """测试配置保存和加载"""
        print("\n=== 测试配置保存和加载 ===")
        
        # 创建配置对象
        config1 = FlameAnalyzerConfig(config_path=self.test_config_path)
        original_threshold = config1.flame_threshold
        
        # 修改配置
        config1.update_config('image_processing.flame_threshold', 200)
        new_threshold = config1.flame_threshold
        self.assert_test(
            new_threshold == 200,
            "配置更新成功",
            f"期望: 200, 实际: {new_threshold}"
        )
        
        # 保存配置
        try:
            config1.save_config()
            self.assert_test(True, "配置保存成功", "")
        except Exception as e:
            self.assert_test(False, "配置保存成功", str(e))
            return
        
        # 重新加载配置
        config2 = FlameAnalyzerConfig(config_path=self.test_config_path)
        loaded_threshold = config2.flame_threshold
        self.assert_test(
            loaded_threshold == 200,
            "配置加载成功",
            f"期望: 200, 实际: {loaded_threshold}"
        )
        
        # 恢复原始值
        config2.update_config('image_processing.flame_threshold', original_threshold)
        config2.save_config()
    
    def test_config_validation(self):
        """测试配置验证"""
        print("\n=== 测试配置验证 ===")
        
        # 测试无效的阈值（应该使用默认值或抛出异常）
        invalid_config_path = os.path.join(self.temp_dir, "invalid_config.yaml")
        invalid_config = {
            'image_processing': {
                'flame_threshold': 300,  # 无效值，超出0-255范围
                'mm_per_pixel': -0.1     # 无效值，负数
            },
            'paths': {},
            'image_formats': [],
            'ui': {},
            'opencv': {}
        }
        
        with open(invalid_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)
        
        try:
            config = FlameAnalyzerConfig(config_path=invalid_config_path)
            # 如果验证失败，应该抛出异常
            self.assert_test(False, "配置验证失败（应该抛出异常）", "配置验证未检测到无效值")
        except ValueError as e:
            self.assert_test(True, "配置验证成功检测到无效值", f"异常: {e}")
    
    def print_all_config_values(self, config):
        """打印所有配置参数值"""
        print("\n" + "=" * 60)
        print("从配置文件获取的所有参数值")
        print("=" * 60)
        
        print("\n【图像处理参数】")
        print(f"  flame_threshold: {config.flame_threshold}")
        print(f"  mm_per_pixel: {config.mm_per_pixel}")
        
        print("\n【路径配置】")
        print(f"  history_csv_path: {config.history_csv_path}")
        print(f"  exp_data_json_path: {config.exp_data_json_path}")
        print(f"  temp_folder: {config.temp_folder}")
        print(f"  flame_output_folder: {config.flame_output_folder}")
        print(f"  max_flame_save_folder: {config.max_flame_save_folder}")
        
        print("\n【图像格式】")
        print(f"  image_formats: {config.image_formats}")
        
        print("\n【UI配置】")
        print(f"  window_title: {config.window_title}")
        print(f"  progress_update_interval: {config.progress_update_interval}")
        print(f"  max_display_failed_files: {config.max_display_failed_files}")
        
        print("\n【OpenCV参数】")
        print(f"  cv_font: {config.cv_font}")
        print(f"  font_scale: {config.font_scale}")
        print(f"  text_color: {config.text_color}")
        print(f"  text_thickness: {config.text_thickness}")
        print(f"  bbox_color: {config.bbox_color}")
        print(f"  bbox_thickness: {config.bbox_thickness}")
        
        print("\n【性能配置】")
        print(f"  stream_processing: {config.stream_processing}")
        print(f"  batch_size: {config.batch_size}")
        
        print("\n【日志配置】")
        print(f"  logging_enabled: {config.logging_enabled}")
        print(f"  log_level: {config.log_level}")
        print(f"  log_file: {config.log_file}")
        
        print("\n【配置文件路径】")
        print(f"  config_path: {config.config_path}")
        
        print("=" * 60)
    
    def test_load_real_config(self):
        """测试加载实际配置文件"""
        print("\n=== 测试加载实际配置文件 ===")
        
        try:
            # 尝试使用PathManager获取配置文件路径
            try:
                from utils.path_manager import PathManager
                real_config_path = PathManager.get_config_path('flame_analyzer_config.yaml')
            except ImportError:
                # 备用方案：使用相对路径
                project_root = Path(__file__).parent.parent
                real_config_path = project_root / 'configs' / 'flame_analyzer_config.yaml'
            
            print(f"配置文件路径: {real_config_path}")
            
            if not os.path.exists(real_config_path):
                print(f"⚠ 警告: 配置文件不存在: {real_config_path}")
                print("   将使用默认配置")
                config = FlameAnalyzerConfig()
            else:
                print(f"✓ 找到配置文件: {real_config_path}")
                config = FlameAnalyzerConfig(config_path=str(real_config_path))
            
            # 打印所有配置值
            self.print_all_config_values(config)
            
            return config
            
        except Exception as e:
            print(f"✗ 加载实际配置文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("火焰分析器配置参数测试")
        print("=" * 60)
        
        # 首先测试加载实际配置文件并打印所有参数
        real_config = self.test_load_real_config()
        
        self.setup()
        
        try:
            # 测试配置初始化
            config = self.test_config_initialization()
            
            # 测试各个参数组
            self.test_image_processing_params(config)
            self.test_path_params(config)
            self.test_image_formats(config)
            self.test_ui_params(config)
            self.test_opencv_params(config)
            self.test_performance_params(config)
            self.test_logging_params(config)
            
            # 测试处理器使用配置
            self.test_processor_uses_config(config)
            
            # 测试配置保存和加载
            self.test_config_save_and_load()
            
            # 测试配置验证
            self.test_config_validation()
            
        finally:
            self.teardown()
        
        # 打印测试结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests} ✓")
        print(f"失败: {self.failed_tests} ✗")
        if self.total_tests > 0:
            print(f"通过率: {self.passed_tests / self.total_tests * 100:.1f}%")
        print("=" * 60)
        
        return self.failed_tests == 0


def print_config_from_file():
    """直接从配置文件读取并打印所有参数"""
    print("=" * 60)
    print("从配置文件读取参数")
    print("=" * 60)
    
    try:
        # 尝试使用PathManager获取配置文件路径
        try:
            from utils.path_manager import PathManager
            config_path = PathManager.get_config_path('flame_analyzer_config.yaml')
        except ImportError:
            # 备用方案：使用相对路径
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'configs' / 'flame_analyzer_config.yaml'
        
        print(f"\n配置文件路径: {config_path}")
        
        if not os.path.exists(config_path):
            print(f"⚠ 警告: 配置文件不存在: {config_path}")
            print("   使用默认配置")
            config = FlameAnalyzerConfig()
        else:
            print(f"✓ 找到配置文件，正在加载...")
            config = FlameAnalyzerConfig(config_path=str(config_path))
        
        # 打印所有配置值
        tester = TestFlameAnalyzerConfig()
        tester.print_all_config_values(config)
        
        # 打印原始YAML内容
        print("\n" + "=" * 60)
        print("原始YAML文件内容")
        print("=" * 60)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("配置文件不存在，无法显示原始内容")
        
        return config
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='火焰分析器配置参数测试')
    parser.add_argument('--print-only', action='store_true', 
                       help='仅打印配置文件内容，不运行完整测试')
    args = parser.parse_args()
    
    if args.print_only:
        # 仅打印配置
        print_config_from_file()
    else:
        # 运行完整测试
        tester = TestFlameAnalyzerConfig()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

