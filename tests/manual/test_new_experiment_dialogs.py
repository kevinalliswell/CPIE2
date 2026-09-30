"""
测试对话框脚本 - 打印填入的信息
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtWidgets import QApplication
from src.views.dialogs.explosion_experiment_dialog import ExplosionExperimentDialog
from src.views.dialogs.ignition_experiment_dialog import IgnitionExperimentDialog
import json


def print_config(title: str, config: dict):
    """打印配置信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    for key, value in config.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, ensure_ascii=False, indent=2)}")
        else:
            print(f"{key}: {value}")
    print(f"{'='*60}\n")


def test_explosion_dialog():
    """测试爆炸性实验对话框"""
    print("\n【测试爆炸性实验对话框】")
    
    # 创建对话框
    dialog = ExplosionExperimentDialog("EXP-20241201-001")
    
    # 填入测试数据
    dialog.exp_name_input.setText("煤粉爆炸性测试")
    dialog.sample_name_input.setText("煤粉样品A")
    dialog.client_input.setText("北京科技大学")
    dialog.operator_input.setText("张三")
    dialog.note_input.setPlainText("这是测试备注信息")
    
    # 获取配置数据并打印
    config = dialog.get_config_data()
    print_config("爆炸性实验配置信息", config)


def test_ignition_dialog():
    """测试着火点实验对话框"""
    print("\n【测试着火点实验对话框】")
    
    # 创建对话框
    dialog = IgnitionExperimentDialog("IGN-20241201-001")
    
    # 填入测试数据
    dialog.exp_name_input.setText("煤粉着火点测试")
    dialog.sample_name_inputs[0].setText("样品1")
    dialog.sample_name_inputs[1].setText("样品2")
    dialog.sample_name_inputs[2].setText("样品3")
    dialog.sample_name_inputs[3].setText("样品4")
    dialog.sample_name_inputs[4].setText("样品5")
    dialog.sample_name_inputs[5].setText("样品6")
    dialog.client_input.setText("北京科技大学")
    dialog.operator_input.setText("李四")
    dialog.note_input.setPlainText("这是着火点测试备注")
    
    # 获取配置数据并打印
    config = dialog.get_config_data()
    print_config("着火点实验配置信息", config)


def test_with_signal():
    """使用信号方式测试（模拟实际使用场景）"""
    print("\n【使用信号方式测试】")
    
    def on_explosion_confirmed(config):
        print_config("爆炸性实验信号接收到的配置", config)
    
    def on_ignition_confirmed(config):
        print_config("着火点实验信号接收到的配置", config)
    
    # 测试爆炸性实验对话框
    explosion_dialog = ExplosionExperimentDialog("EXP-20241201-002")
    explosion_dialog.exp_name_input.setText("爆炸性测试-信号方式")
    explosion_dialog.sample_name_input.setText("测试样品")
    explosion_dialog.confirmed.connect(on_explosion_confirmed)
    
    # 测试着火点实验对话框
    ignition_dialog = IgnitionExperimentDialog("IGN-20241201-002")
    ignition_dialog.exp_name_input.setText("着火点测试-信号方式")
    ignition_dialog.sample_name_inputs[0].setText("信号测试样品1")
    ignition_dialog.sample_name_inputs[1].setText("信号测试样品2")
    ignition_dialog.confirmed.connect(on_ignition_confirmed)
    
    print("注意：信号测试需要手动点击确认按钮才会触发打印")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    print("="*60)
    print("对话框测试程序")
    print("="*60)
    print("\n请选择要测试的对话框：")
    print("1. 爆炸性实验对话框")
    print("2. 着火点实验对话框")
    print("3. 两个都测试（先爆炸性，后着火点）")
    print("4. 退出")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        # 显示爆炸性实验对话框
        explosion_dialog = ExplosionExperimentDialog("EXP-20241201-001")
        explosion_dialog.exp_name_input.setText("煤粉爆炸性测试")
        explosion_dialog.sample_name_input.setText("煤粉样品A")
        explosion_dialog.client_input.setText("北京科技大学")
        explosion_dialog.operator_input.setText("张三")
        explosion_dialog.note_input.setPlainText("这是测试备注信息")
        
        def on_explosion_confirmed(config):
            print_config("爆炸性实验配置信息", config)
            app.quit()
        
        explosion_dialog.confirmed.connect(on_explosion_confirmed)
        explosion_dialog.show()
        sys.exit(app.exec())
    
    elif choice == "2":
        # 显示着火点实验对话框
        ignition_dialog = IgnitionExperimentDialog("IGN-20241201-001")
        ignition_dialog.exp_name_input.setText("煤粉着火点测试")
        ignition_dialog.sample_name_inputs[0].setText("样品1")
        ignition_dialog.sample_name_inputs[1].setText("样品2")
        ignition_dialog.sample_name_inputs[2].setText("样品3")
        ignition_dialog.sample_name_inputs[3].setText("样品4")
        ignition_dialog.sample_name_inputs[4].setText("样品5")
        ignition_dialog.sample_name_inputs[5].setText("样品6")
        ignition_dialog.client_input.setText("北京科技大学")
        ignition_dialog.operator_input.setText("李四")
        ignition_dialog.note_input.setPlainText("这是着火点测试备注")
        
        def on_ignition_confirmed(config):
            print_config("着火点实验配置信息", config)
            app.quit()
        
        ignition_dialog.confirmed.connect(on_ignition_confirmed)
        ignition_dialog.show()
        sys.exit(app.exec())
    
    elif choice == "3":
        # 先显示爆炸性，再显示着火点
        explosion_dialog = ExplosionExperimentDialog("EXP-20241201-001")
        explosion_dialog.exp_name_input.setText("煤粉爆炸性测试")
        explosion_dialog.sample_name_input.setText("煤粉样品A")
        explosion_dialog.client_input.setText("北京科技大学")
        explosion_dialog.operator_input.setText("张三")
        explosion_dialog.note_input.setPlainText("这是测试备注信息")
        
        ignition_dialog = IgnitionExperimentDialog("IGN-20241201-001")
        ignition_dialog.exp_name_input.setText("煤粉着火点测试")
        ignition_dialog.sample_name_inputs[0].setText("样品1")
        ignition_dialog.sample_name_inputs[1].setText("样品2")
        ignition_dialog.sample_name_inputs[2].setText("样品3")
        ignition_dialog.sample_name_inputs[3].setText("样品4")
        ignition_dialog.sample_name_inputs[4].setText("样品5")
        ignition_dialog.sample_name_inputs[5].setText("样品6")
        ignition_dialog.client_input.setText("北京科技大学")
        ignition_dialog.operator_input.setText("李四")
        ignition_dialog.note_input.setPlainText("这是着火点测试备注")
        
        def on_explosion_confirmed(config):
            print_config("爆炸性实验配置信息", config)
            explosion_dialog.close()
            # 显示着火点对话框
            ignition_dialog.show()
        
        def on_ignition_confirmed(config):
            print_config("着火点实验配置信息", config)
            app.quit()
        
        explosion_dialog.confirmed.connect(on_explosion_confirmed)
        ignition_dialog.confirmed.connect(on_ignition_confirmed)
        explosion_dialog.show()
        sys.exit(app.exec())
    
    elif choice == "4":
        print("\n退出程序")
        return
    
    else:
        print("\n无效选项，退出程序")
        return


if __name__ == "__main__":
    main()

