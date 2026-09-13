"""
新建实验对话框测试

- 前三个 test_* 函数是 pytest 用例：在离屏 QApplication 中构造对话框并校验 get_config_data() 的输出
- main() 是手工交互脚本（需要显示器和键盘输入），只在直接运行本文件时执行
"""

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.views.dialogs.explosion_experiment_dialog import ExplosionExperimentDialog  # noqa: E402
from src.views.dialogs.ignition_experiment_dialog import IgnitionExperimentDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


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


def test_explosion_dialog(qapp):
    """爆炸性实验对话框：填入的信息应原样出现在配置数据中"""
    dialog = ExplosionExperimentDialog("EXP-20241201-001")
    try:
        dialog.exp_name_input.setText("煤粉爆炸性测试")
        dialog.sample_name_input.setText("煤粉样品A")
        dialog.client_input.setText("北京科技大学")
        dialog.operator_input.setText("张三")
        dialog.note_input.setPlainText("这是测试备注信息")

        config = dialog.get_config_data()
        print_config("爆炸性实验配置信息", config)

        assert config["experiment_id"] == "EXP-20241201-001"
        assert config["experiment_name"] == "煤粉爆炸性测试"
        assert config["sample_name"] == "煤粉样品A"
        assert config["client"] == "北京科技大学"
        assert config["operator"] == "张三"
        # description 是由实验编号/委托单位/操作员/备注拼接的摘要
        assert "这是测试备注信息" in config["description"]
    finally:
        dialog.deleteLater()


def test_ignition_dialog(qapp):
    """着火点实验对话框：6 个样品名称应按顺序进入 sample_names 列表"""
    dialog = IgnitionExperimentDialog("IGN-20241201-001")
    try:
        dialog.exp_name_input.setText("煤粉着火点测试")
        for i in range(6):
            dialog.sample_name_inputs[i].setText(f"样品{i + 1}")
        dialog.client_input.setText("北京科技大学")
        dialog.operator_input.setText("李四")
        dialog.note_input.setPlainText("这是着火点测试备注")

        config = dialog.get_config_data()
        print_config("着火点实验配置信息", config)

        expected_names = [f"样品{i + 1}" for i in range(6)]
        assert config["experiment_id"] == "IGN-20241201-001"
        assert config["experiment_name"] == "煤粉着火点测试"
        # sample_names 以 JSON 字符串形式存入数据库，sample_names_list 为原始列表
        assert json.loads(config["sample_names"]) == expected_names
        assert config["sample_names_list"] == expected_names
        assert config["client"] == "北京科技大学"
        assert config["operator"] == "李四"
        assert "这是着火点测试备注" in config["description"]
    finally:
        dialog.deleteLater()


def test_with_signal(qapp):
    """confirmed 信号应携带与 get_config_data() 一致的配置字典"""
    received = []

    explosion_dialog = ExplosionExperimentDialog("EXP-20241201-002")
    try:
        explosion_dialog.exp_name_input.setText("爆炸性测试-信号方式")
        explosion_dialog.sample_name_input.setText("测试样品")
        explosion_dialog.confirmed.connect(received.append)
        explosion_dialog.confirmed.emit(explosion_dialog.get_config_data())

        assert len(received) == 1
        assert received[0]["experiment_name"] == "爆炸性测试-信号方式"
        assert received[0]["sample_name"] == "测试样品"
    finally:
        explosion_dialog.deleteLater()


def main():
    """手工交互脚本：显示对话框并打印确认后的配置"""
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    print("=" * 60)
    print("对话框测试程序")
    print("=" * 60)
    print("\n请选择要测试的对话框：")
    print("1. 爆炸性实验对话框")
    print("2. 着火点实验对话框")
    print("3. 退出")

    choice = input("\n请输入选项 (1-3): ").strip()

    if choice == "1":
        dialog = ExplosionExperimentDialog("EXP-20241201-001")
        dialog.confirmed.connect(lambda config: (print_config("爆炸性实验配置信息", config), app.quit()))
        dialog.show()
        sys.exit(app.exec())
    elif choice == "2":
        dialog = IgnitionExperimentDialog("IGN-20241201-001")
        dialog.confirmed.connect(lambda config: (print_config("着火点实验配置信息", config), app.quit()))
        dialog.show()
        sys.exit(app.exec())
    else:
        print("\n退出程序")


if __name__ == "__main__":
    main()
