#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
着火点实验按钮状态测试
验证各状态下的按钮使能逻辑
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.experiment_states import IgnitionExperimentState


class MockButton:
    """模拟按钮对象"""
    def __init__(self, name):
        self.name = name
        self._enabled = False
        self._text = ""
        self._object_name = ""
    
    def setEnabled(self, enabled):
        self._enabled = enabled
    
    def setText(self, text):
        self._text = text
    
    def setObjectName(self, name):
        self._object_name = name
    
    def style(self):
        return MockStyle()
    
    def isEnabled(self):
        return self._enabled
    
    def text(self):
        return self._text
    
    def objectName(self):
        return self._object_name


class MockStyle:
    """模拟样式对象"""
    def unpolish(self, widget):
        pass
    
    def polish(self, widget):
        pass


class MockController:
    """模拟控制器"""
    def __init__(self, state):
        self.current_state = state


class TestButtonStates:
    """按钮状态测试类"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
    
    def assert_button_state(self, button, expected_enabled, expected_text, test_name):
        """断言按钮状态"""
        self.total_tests += 1
        
        enabled_match = button.isEnabled() == expected_enabled
        text_match = button.text() == expected_text
        
        if enabled_match and text_match:
            print(f"✓ {test_name}: 通过")
            self.passed_tests += 1
            return True
        else:
            error_msg = []
            if not enabled_match:
                error_msg.append(f"使能状态错误(期望: {expected_enabled}, 实际: {button.isEnabled()})")
            if not text_match:
                error_msg.append(f"文本错误(期望: '{expected_text}', 实际: '{button.text()}')")
            print(f"✗ {test_name}: 失败 - {', '.join(error_msg)}")
            self.failed_tests += 1
            return False
    
    def simulate_update_button_states(self, controller, btn_connect, btn_new_experiment, btn_start, btn_finalize):
        """
        模拟 _update_button_states 方法
        （从 ignition_page.py 复制的逻辑）
        """
        state = controller.current_state
        
        # 连接按钮
        btn_connect.setEnabled(state == IgnitionExperimentState.IDLE)
        
        # 新建实验按钮
        btn_new_experiment.setEnabled(state.can_create_experiment())
        
        # 启动/停止按钮（智能按钮）
        if state == IgnitionExperimentState.PREPARED:
            btn_start.setEnabled(True)
            btn_start.setText("启动实验")
            btn_start.setObjectName("successButton")
        elif state == IgnitionExperimentState.RUNNING:
            btn_start.setEnabled(True)
            btn_start.setText("停止实验")
            btn_start.setObjectName("dangerButton")
        else:
            # 其他状态禁用
            btn_start.setEnabled(False)
            btn_start.setText("启动实验")
            btn_start.setObjectName("successButton")
        
        # 完成实验按钮（独立按钮）
        btn_finalize.setEnabled(state.can_finalize())
        
        # 应用样式（模拟）
        btn_start.style().unpolish(btn_start)
        btn_start.style().polish(btn_start)
        btn_finalize.style().unpolish(btn_finalize)
        btn_finalize.style().polish(btn_finalize)
    
    def test_state(self, state):
        """测试指定状态下的按钮状态"""
        print(f"\n{'='*60}")
        print(f"【测试状态】{state.value.upper()} - {state.description()}")
        print(f"{'='*60}")
        
        # 创建模拟对象
        controller = MockController(state)
        btn_connect = MockButton("连接设备")
        btn_new_experiment = MockButton("新建实验")
        btn_start = MockButton("启动/停止实验")
        btn_finalize = MockButton("完成实验")
        
        # 模拟按钮状态更新
        self.simulate_update_button_states(
            controller, btn_connect, btn_new_experiment, btn_start, btn_finalize
        )
        
        # 定义期望状态（根据设计文档）
        expectations = {
            IgnitionExperimentState.IDLE: {
                'btn_connect': (True, "连接设备"),
                'btn_new_experiment': (False, None),
                'btn_start': (False, "启动实验"),
                'btn_finalize': (False, None)
            },
            IgnitionExperimentState.CONNECTED: {
                'btn_connect': (False, None),
                'btn_new_experiment': (True, "新建实验"),
                'btn_start': (False, "启动实验"),
                'btn_finalize': (False, None)
            },
            IgnitionExperimentState.PREPARED: {
                'btn_connect': (False, None),
                'btn_new_experiment': (True, "新建实验"),
                'btn_start': (True, "启动实验"),
                'btn_finalize': (False, None)
            },
            IgnitionExperimentState.RUNNING: {
                'btn_connect': (False, None),
                'btn_new_experiment': (False, None),
                'btn_start': (True, "停止实验"),
                'btn_finalize': (False, None)
            },
            IgnitionExperimentState.STOPPED: {
                'btn_connect': (False, None),
                'btn_new_experiment': (False, None),
                'btn_start': (False, "启动实验"),
                'btn_finalize': (True, "完成实验")
            },
            IgnitionExperimentState.COMPLETED: {
                'btn_connect': (False, None),
                'btn_new_experiment': (True, "新建实验"),
                'btn_start': (False, "启动实验"),
                'btn_finalize': (False, None)
            }
        }
        
        expected = expectations[state]
        
        # 验证每个按钮
        results = []
        
        # 连接设备按钮
        enabled, text = expected['btn_connect']
        if text:
            results.append(self.assert_button_state(
                btn_connect, enabled, text,
                f"  连接设备按钮: 使能={enabled}, 文本='{text}'"
            ))
        else:
            self.total_tests += 1
            if btn_connect.isEnabled() == enabled:
                print(f"✓   连接设备按钮: 使能={enabled} - 通过")
                self.passed_tests += 1
                results.append(True)
            else:
                print(f"✗   连接设备按钮: 使能错误(期望: {enabled}, 实际: {btn_connect.isEnabled()})")
                self.failed_tests += 1
                results.append(False)
        
        # 新建实验按钮
        enabled, text = expected['btn_new_experiment']
        if text:
            results.append(self.assert_button_state(
                btn_new_experiment, enabled, text,
                f"  新建实验按钮: 使能={enabled}, 文本='{text}'"
            ))
        else:
            self.total_tests += 1
            if btn_new_experiment.isEnabled() == enabled:
                print(f"✓   新建实验按钮: 使能={enabled} - 通过")
                self.passed_tests += 1
                results.append(True)
            else:
                print(f"✗   新建实验按钮: 使能错误(期望: {enabled}, 实际: {btn_new_experiment.isEnabled()})")
                self.failed_tests += 1
                results.append(False)
        
        # 启动/停止按钮
        enabled, text = expected['btn_start']
        results.append(self.assert_button_state(
            btn_start, enabled, text,
            f"  启动/停止按钮: 使能={enabled}, 文本='{text}'"
        ))
        
        # 验证按钮样式
        if state == IgnitionExperimentState.PREPARED:
            style_ok = btn_start.objectName() == "successButton"
        elif state == IgnitionExperimentState.RUNNING:
            style_ok = btn_start.objectName() == "dangerButton"
        else:
            style_ok = btn_start.objectName() == "successButton"
        
        self.total_tests += 1
        if style_ok:
            print(f"✓   启动/停止按钮样式: {btn_start.objectName()} - 通过")
            self.passed_tests += 1
            results.append(True)
        else:
            print(f"✗   启动/停止按钮样式错误: {btn_start.objectName()}")
            self.failed_tests += 1
            results.append(False)
        
        # 完成实验按钮
        enabled, text = expected['btn_finalize']
        if text:
            results.append(self.assert_button_state(
                btn_finalize, enabled, text,
                f"  完成实验按钮: 使能={enabled}, 文本='{text}'"
            ))
        else:
            self.total_tests += 1
            if btn_finalize.isEnabled() == enabled:
                print(f"✓   完成实验按钮: 使能={enabled} - 通过")
                self.passed_tests += 1
                results.append(True)
            else:
                print(f"✗   完成实验按钮: 使能错误(期望: {enabled}, 实际: {btn_finalize.isEnabled()})")
                self.failed_tests += 1
                results.append(False)
        
        return all(results)
    
    def run_all_tests(self):
        """运行所有状态的按钮测试"""
        print("=" * 60)
        print("着火点实验按钮状态测试")
        print("=" * 60)
        print("\n测试目标: 验证各状态下按钮的使能状态和文本")
        print("=" * 60)
        
        # 测试所有状态
        states_to_test = [
            IgnitionExperimentState.IDLE,
            IgnitionExperimentState.CONNECTED,
            IgnitionExperimentState.PREPARED,
            IgnitionExperimentState.RUNNING,
            IgnitionExperimentState.STOPPED,
            IgnitionExperimentState.COMPLETED
        ]
        
        for state in states_to_test:
            self.test_state(state)
        
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
        
        if self.failed_tests == 0:
            print("✅ 所有按钮状态测试通过！")
        else:
            print("⚠️  部分测试失败，请检查上述错误信息")
        
        # 打印按钮状态表
        self.print_button_state_table()
        
        return self.failed_tests == 0
    
    def print_button_state_table(self):
        """打印按钮状态表"""
        print("\n" + "=" * 60)
        print("按钮状态对照表")
        print("=" * 60)
        print(f"{'状态':<15} {'连接设备':<10} {'新建实验':<10} {'启动/停止':<15} {'按钮文本':<12} {'按钮样式':<12} {'完成实验':<10}")
        print("-" * 60)
        
        test_data = [
            ("IDLE", "✅", "❌", "❌", "启动实验", "success", "❌"),
            ("CONNECTED", "❌", "✅", "❌", "启动实验", "success", "❌"),
            ("PREPARED", "❌", "✅", "✅", "启动实验", "success", "❌"),
            ("RUNNING", "❌", "❌", "✅", "停止实验", "danger", "❌"),
            ("STOPPED", "❌", "❌", "❌", "启动实验", "success", "✅"),
            ("COMPLETED", "❌", "✅", "❌", "启动实验", "success", "❌"),
        ]
        
        for row in test_data:
            print(f"{row[0]:<15} {row[1]:<10} {row[2]:<10} {row[3]:<15} {row[4]:<12} {row[5]:<12} {row[6]:<10}")
        
        print("-" * 60)
        print("\n说明:")
        print("  ✅ = 按钮可用")
        print("  ❌ = 按钮禁用")
        print("  success = 绿色成功样式")
        print("  danger = 红色危险样式")
        print("=" * 60)


if __name__ == "__main__":
    tester = TestButtonStates()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

