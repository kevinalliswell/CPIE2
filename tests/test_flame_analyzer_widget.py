#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰分析器窗口组件测试脚本
测试FlameAnalyzerWidget的初始化和基本功能
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import cv2

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from views.dialogs.flame_analyzer.flame_analyzer_widget import FlameAnalyzerWidget
from views.dialogs.flame_analyzer.config_manager import FlameAnalyzerConfig
from views.dialogs.flame_analyzer.flame_processor import (
    FlameImageProcessor, 
    FlameAnalysisResult, 
    FlameStatistics
)


class TestFlameAnalyzerWidget:
    """火焰分析器窗口测试类"""
    
    def __init__(self):
        self.app = None
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        self.temp_dir = None
        self.test_image_folder = None
        self.test_output_folder = None
    
    def setup(self):
        """测试前准备"""
        # 创建QApplication（如果不存在）
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="flame_widget_test_")
        self.test_image_folder = os.path.join(self.temp_dir, "test_images")
        self.test_output_folder = os.path.join(self.temp_dir, "test_output")
        os.makedirs(self.test_image_folder, exist_ok=True)
        os.makedirs(self.test_output_folder, exist_ok=True)
        
        # 创建测试图像文件
        self._create_test_images()
        
        print("✓ 测试环境准备完成\n")
    
    def _create_test_images(self, count=3):
        """创建测试图像文件"""
        for i in range(count):
            # 创建一个简单的测试图像（白色背景，中间有红色矩形模拟火焰）
            img = np.ones((200, 300, 3), dtype=np.uint8) * 255
            # 添加一个红色矩形（模拟火焰）
            cv2.rectangle(img, (100, 50), (200, 150), (0, 0, 255), -1)
            
            image_path = os.path.join(self.test_image_folder, f"test_image_{i+1:03d}.jpg")
            cv2.imwrite(image_path, img)
    
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
    
    def test_widget_initialization(self):
        """测试窗口初始化"""
        print("\n=== 测试窗口初始化 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            self.assert_test(
                widget is not None,
                "窗口对象创建成功",
                "窗口对象为None"
            )
            
            self.assert_test(
                widget.config == config,
                "配置对象正确注入",
                "配置对象不匹配"
            )
            
            self.assert_test(
                widget.input_folder == self.test_image_folder,
                "输入文件夹路径正确",
                f"期望: {self.test_image_folder}, 实际: {widget.input_folder}"
            )
            
            self.assert_test(
                widget.processor is not None,
                "处理器对象创建成功",
                "处理器对象为None"
            )
            
            self.assert_test(
                widget.analysis_completed == False,
                "初始状态：分析未完成",
                f"分析完成标志: {widget.analysis_completed}"
            )
            
            self.assert_test(
                widget.is_playing == False,
                "初始状态：未播放",
                f"播放状态: {widget.is_playing}"
            )
            
            self.assert_test(
                widget.play_speed == 1.0,
                "初始播放速度正确",
                f"播放速度: {widget.play_speed}"
            )
            
            widget.close()
            return widget
            
        except Exception as e:
            self.assert_test(False, "窗口初始化", str(e))
            import traceback
            traceback.print_exc()
            return None
    
    def test_ui_components(self):
        """测试UI组件创建"""
        print("\n=== 测试UI组件创建 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 测试信息标签
            self.assert_test(
                widget.max_label is not None,
                "最大值标签存在",
                "最大值标签为None"
            )
            
            self.assert_test(
                widget.min_label is not None,
                "最小值标签存在",
                "最小值标签为None"
            )
            
            self.assert_test(
                widget.avg_label is not None,
                "平均值标签存在",
                "平均值标签为None"
            )
            
            # 测试列表控件
            self.assert_test(
                widget.list_widget is not None,
                "列表控件存在",
                "列表控件为None"
            )
            
            # 测试按钮
            self.assert_test(
                widget.prev_button is not None,
                "上一张按钮存在",
                "上一张按钮为None"
            )
            
            self.assert_test(
                widget.next_button is not None,
                "下一张按钮存在",
                "下一张按钮为None"
            )
            
            self.assert_test(
                widget.play_pause_button is not None,
                "播放/暂停按钮存在",
                "播放/暂停按钮为None"
            )
            
            self.assert_test(
                widget.btn_quit is not None,
                "关闭按钮存在",
                "关闭按钮为None"
            )
            
            # 测试图像显示
            self.assert_test(
                widget.lb_img_viewer is not None,
                "图像显示标签存在",
                "图像显示标签为None"
            )
            
            # 测试速度控制
            self.assert_test(
                widget.speed_slider is not None,
                "速度滑块存在",
                "速度滑块为None"
            )
            
            self.assert_test(
                widget.speed_value_label is not None,
                "速度值标签存在",
                "速度值标签为None"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "UI组件创建", str(e))
            import traceback
            traceback.print_exc()
    
    def test_window_title(self):
        """测试窗口标题"""
        print("\n=== 测试窗口标题 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            expected_title = config.window_title
            actual_title = widget.windowTitle()
            
            self.assert_test(
                actual_title == expected_title,
                "窗口标题正确",
                f"期望: {expected_title}, 实际: {actual_title}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "窗口标题测试", str(e))
    
    def test_play_control_initialization(self):
        """测试播放控制初始化"""
        print("\n=== 测试播放控制初始化 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 测试播放按钮初始状态
            button_text = widget.play_pause_button.text()
            self.assert_test(
                "▶ 播放" in button_text,
                "播放按钮初始文本正确",
                f"按钮文本: {button_text}"
            )
            
            # 测试速度滑块初始值
            slider_value = widget.speed_slider.value()
            self.assert_test(
                slider_value == 2,  # 默认1.0倍速对应索引2
                "速度滑块初始值正确",
                f"滑块值: {slider_value}"
            )
            
            # 测试速度标签初始值
            speed_label_text = widget.speed_value_label.text()
            self.assert_test(
                "1.0x" in speed_label_text,
                "速度标签初始值正确",
                f"标签文本: {speed_label_text}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "播放控制初始化", str(e))
    
    def test_speed_change(self):
        """测试速度变化"""
        print("\n=== 测试速度变化 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 测试速度映射
            speed_map = {
                1: 0.5,
                2: 1.0,
                3: 2.0,
                4: 4.0,
                5: 8.0,
                6: 16.0
            }
            
            for slider_value, expected_speed in speed_map.items():
                widget.speed_slider.setValue(slider_value)
                widget.on_speed_changed(slider_value)
                
                self.assert_test(
                    abs(widget.play_speed - expected_speed) < 0.001,
                    f"速度映射正确 (滑块值={slider_value}, 速度={expected_speed}x)",
                    f"期望: {expected_speed}, 实际: {widget.play_speed}"
                )
                
                speed_label_text = widget.speed_value_label.text()
                self.assert_test(
                    f"{expected_speed:.1f}x" in speed_label_text,
                    f"速度标签更新正确 ({expected_speed}x)",
                    f"标签文本: {speed_label_text}"
                )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "速度变化测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_play_pause_functionality(self):
        """测试播放/暂停功能"""
        print("\n=== 测试播放/暂停功能 ===")
        
        try:
            config = FlameAnalyzerConfig()
            
            # 创建模拟的分析结果
            mock_results = [
                FlameAnalysisResult(
                    filename="test1.jpg",
                    flame_size_mm=100,
                    flame_region=(10, 10, 50, 50),
                    success=True
                ),
                FlameAnalysisResult(
                    filename="test2.jpg",
                    flame_size_mm=150,
                    flame_region=(20, 20, 60, 60),
                    success=True
                )
            ]
            
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 模拟分析结果
            widget.analysis_results = mock_results
            widget.analysis_completed = True
            
            # 填充列表
            for result in mock_results:
                widget.list_widget.addItem(f"{result.filename}: {result.flame_size_mm} mm")
            
            # 测试初始状态
            self.assert_test(
                not widget.is_playing,
                "初始状态：未播放",
                f"播放状态: {widget.is_playing}"
            )
            
            # 测试开始播放
            widget.on_play_pause_clicked()
            self.assert_test(
                widget.is_playing,
                "点击后：开始播放",
                f"播放状态: {widget.is_playing}"
            )
            
            button_text = widget.play_pause_button.text()
            self.assert_test(
                "⏸ 暂停" in button_text,
                "按钮文本变为暂停",
                f"按钮文本: {button_text}"
            )
            
            # 测试暂停播放
            widget.on_play_pause_clicked()
            self.assert_test(
                not widget.is_playing,
                "再次点击：暂停播放",
                f"播放状态: {widget.is_playing}"
            )
            
            button_text = widget.play_pause_button.text()
            self.assert_test(
                "▶ 播放" in button_text,
                "按钮文本变为播放",
                f"按钮文本: {button_text}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "播放/暂停功能测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_navigation_buttons(self):
        """测试导航按钮"""
        print("\n=== 测试导航按钮 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 添加测试项到列表
            test_items = ["item1", "item2", "item3"]
            for item in test_items:
                widget.list_widget.addItem(item)
            
            # 设置当前项为中间项
            widget.list_widget.setCurrentRow(1)
            self.assert_test(
                widget.list_widget.currentRow() == 1,
                "当前行设置正确",
                f"当前行: {widget.list_widget.currentRow()}"
            )
            
            # 测试上一张按钮
            widget.on_prev_button_clicked()
            self.assert_test(
                widget.list_widget.currentRow() == 0,
                "上一张按钮功能正常",
                f"当前行: {widget.list_widget.currentRow()}"
            )
            
            # 测试下一张按钮
            widget.on_next_button_clicked()
            self.assert_test(
                widget.list_widget.currentRow() == 1,
                "下一张按钮功能正常",
                f"当前行: {widget.list_widget.currentRow()}"
            )
            
            # 测试边界情况：在第一项时点击上一张
            widget.list_widget.setCurrentRow(0)
            widget.on_prev_button_clicked()
            self.assert_test(
                widget.list_widget.currentRow() == 0,
                "第一项时上一张按钮不越界",
                f"当前行: {widget.list_widget.currentRow()}"
            )
            
            # 测试边界情况：在最后一项时点击下一张
            widget.list_widget.setCurrentRow(len(test_items) - 1)
            widget.on_next_button_clicked()
            self.assert_test(
                widget.list_widget.currentRow() == len(test_items) - 1,
                "最后一项时下一张按钮不越界",
                f"当前行: {widget.list_widget.currentRow()}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "导航按钮测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_signal_connection(self):
        """测试信号连接"""
        print("\n=== 测试信号连接 ===")
        
        try:
            config = FlameAnalyzerConfig()
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config
            )
            
            # 测试window_closed信号存在
            self.assert_test(
                hasattr(widget, 'window_closed'),
                "window_closed信号存在",
                "信号不存在"
            )
            
            # 测试信号类型
            from PySide6.QtCore import Signal
            self.assert_test(
                isinstance(widget.window_closed, Signal),
                "window_closed是Signal类型",
                f"类型: {type(widget.window_closed)}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "信号连接测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_config_injection(self):
        """测试配置注入"""
        print("\n=== 测试配置注入 ===")
        
        try:
            # 创建自定义配置
            custom_config = FlameAnalyzerConfig()
            custom_config.update_config('image_processing.flame_threshold', 200)
            custom_config.update_config('ui.window_title', '自定义标题')
            
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=custom_config
            )
            
            # 测试配置是否正确注入
            self.assert_test(
                widget.config.flame_threshold == 200,
                "自定义阈值配置正确",
                f"阈值: {widget.config.flame_threshold}"
            )
            
            self.assert_test(
                widget.windowTitle() == '自定义标题',
                "自定义窗口标题正确",
                f"标题: {widget.windowTitle()}"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "配置注入测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_processor_injection(self):
        """测试处理器注入"""
        print("\n=== 测试处理器注入 ===")
        
        try:
            config = FlameAnalyzerConfig()
            
            # 创建模拟处理器
            mock_processor = Mock(spec=FlameImageProcessor)
            mock_processor.get_image_files = Mock(return_value=["test1.jpg", "test2.jpg"])
            
            widget = FlameAnalyzerWidget(
                input_folder=self.test_image_folder,
                config=config,
                processor=mock_processor
            )
            
            # 测试处理器是否正确注入
            self.assert_test(
                widget.processor == mock_processor,
                "处理器正确注入",
                "处理器对象不匹配"
            )
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "处理器注入测试", str(e))
            import traceback
            traceback.print_exc()
    
    def test_invalid_input_folder(self):
        """测试无效输入文件夹"""
        print("\n=== 测试无效输入文件夹 ===")
        
        try:
            config = FlameAnalyzerConfig()
            invalid_folder = os.path.join(self.temp_dir, "non_existent_folder")
            
            # 注意：由于_auto_start_analysis会延迟执行，我们需要等待或mock
            widget = FlameAnalyzerWidget(
                input_folder=invalid_folder,
                config=config
            )
            
            # 窗口应该被创建，但会在自动分析时关闭
            self.assert_test(
                widget is not None,
                "窗口对象创建成功（即使文件夹无效）",
                "窗口对象为None"
            )
            
            # 等待自动分析执行
            QTimer.singleShot(200, lambda: widget.close() if widget else None)
            
            widget.close()
            
        except Exception as e:
            self.assert_test(False, "无效输入文件夹测试", str(e))
            import traceback
            traceback.print_exc()
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("火焰分析器窗口组件测试")
        print("=" * 60)
        
        self.setup()
        
        try:
            # 运行所有测试
            self.test_widget_initialization()
            self.test_ui_components()
            self.test_window_title()
            self.test_play_control_initialization()
            self.test_speed_change()
            self.test_play_pause_functionality()
            self.test_navigation_buttons()
            self.test_signal_connection()
            self.test_config_injection()
            self.test_processor_injection()
            self.test_invalid_input_folder()
            
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


if __name__ == "__main__":
    tester = TestFlameAnalyzerWidget()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)







