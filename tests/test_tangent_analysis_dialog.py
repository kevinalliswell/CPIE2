#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：测试切线法分析对话框
从数据库中查询指定会话ID的温度数据，并显示切线法分析对话框
"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from PySide6.QtWidgets import QApplication, QMessageBox
import yaml

from models.ignition_database import IgnitionDatabase
from views.dialogs.tangent_analysis_dialog import TangentAnalysisDialog
from utils.path_manager import PathManager


def load_config():
    """加载实验配置文件"""
    config_path = project_root / 'configs' / 'experiment_config.yaml'
    
    if not config_path.exists():
        print(f"✗ 配置文件不存在: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 提取着火点实验配置
        ignition_config = config.get('ignition_experiment', {})
        
        if not ignition_config:
            print("⚠ 配置文件中没有找到 ignition_experiment 配置，使用默认配置")
            ignition_config = {
                'ignition_detection': {
                    'tangent_method': {
                        'smooth_window': 11,
                        'smooth_order': 2,
                        'baseline_points': 20,
                        'peak_points': 10,
                        'min_temp_rise': 20.0,
                        'min_rate_increase': 2.0,
                        'min_data_points': 50
                    }
                }
            }
        
        return ignition_config
    except Exception as e:
        print(f"✗ 加载配置文件失败: {e}")
        return None


def list_available_sessions(db):
    """列出所有可用的会话"""
    try:
        sessions = db.get_all_experiment_sessions()
        if not sessions:
            return []
        
        # 检查每个会话是否有数据
        available_sessions = []
        for session in sessions:
            session_id = session['id']
            session_data = db.get_session_temperature_data(session_id)
            if session_data and len(session_data) >= 50:
                # 检查是否有有效温度数据
                has_valid_data = False
                for record in session_data:
                    for i in range(6):
                        temp = record.get(f'sample{i+1}_temperature', 0)
                        if temp > 30:
                            has_valid_data = True
                            break
                    if has_valid_data:
                        break
                
                if has_valid_data:
                    available_sessions.append({
                        'id': session_id,
                        'name': session.get('experiment_name', f'会话{session_id}'),
                        'start_time': session.get('start_time', ''),
                        'status': session.get('status', ''),
                        'data_count': len(session_data)
                    })
        
        return available_sessions
    except Exception as e:
        print(f"    ⚠ 列出可用会话时出错: {e}")
        return []


def verify_session_data(db, session_id):
    """验证会话数据是否存在"""
    try:
        session_data = db.get_session_temperature_data(session_id)
        
        if not session_data:
            return False, f"会话 {session_id} 没有温度数据"
        
        # 检查数据有效性
        if len(session_data) < 50:
            return False, f"会话 {session_id} 数据点不足（{len(session_data)}个，至少需要50个）"
        
        # 检查是否有有效的温度数据
        has_valid_data = False
        for record in session_data:
            for i in range(6):
                temp = record.get(f'sample{i+1}_temperature', 0)
                if temp > 30:  # 有效温度阈值
                    has_valid_data = True
                    break
            if has_valid_data:
                break
        
        if not has_valid_data:
            return False, f"会话 {session_id} 没有有效的温度数据（所有温度都低于30°C）"
        
        return True, f"会话 {session_id} 有 {len(session_data)} 条有效数据记录"
        
    except Exception as e:
        return False, f"验证会话数据时出错: {e}"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='测试切线法分析对话框',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test_tangent_analysis_dialog.py              # 使用默认会话ID 15
  python test_tangent_analysis_dialog.py --session 14 # 使用会话ID 14
        """
    )
    parser.add_argument(
        '--session',
        type=int,
        default=15,
        help='会话ID（默认: 15）'
    )
    
    args = parser.parse_args()
    session_id = args.session
    
    print("=" * 80)
    print(f"切线法分析对话框测试 - 会话 {session_id}")
    print("=" * 80)
    
    # 1. 加载配置
    print("\n[1] 加载配置文件...")
    config = load_config()
    if config is None:
        print("    ✗ 配置加载失败，退出")
        return 1
    print("    ✓ 配置加载成功")
    
    # 2. 连接数据库
    print("\n[2] 连接数据库...")
    try:
        db_path = PathManager.get_data_path("ignition_experiment - 副本.db")
        print(f"    数据库路径: {db_path}")
        
        db = IgnitionDatabase(db_path)
        print("    ✓ 数据库连接成功")
    except Exception as e:
        print(f"    ✗ 数据库连接失败: {e}")
        return 1
    
    # 3. 验证会话数据
    print(f"\n[3] 验证会话 {session_id} 的数据...")
    is_valid, message = verify_session_data(db, session_id)
    if not is_valid:
        print(f"    ✗ {message}")
        
        # 列出可用的会话
        print("\n[提示] 正在查找可用的会话...")
        available_sessions = list_available_sessions(db)
        
        if available_sessions:
            print(f"\n    找到 {len(available_sessions)} 个有数据的会话:")
            print("    " + "-" * 70)
            for sess in available_sessions[:10]:  # 最多显示10个
                print(f"    会话ID: {sess['id']:3d} | "
                      f"名称: {sess['name']:20s} | "
                      f"数据点: {sess['data_count']:5d} | "
                      f"状态: {sess['status']}")
            if len(available_sessions) > 10:
                print(f"    ... 还有 {len(available_sessions) - 10} 个会话")
            print("    " + "-" * 70)
            script_name = Path(__file__).name
            print(f"\n    使用示例: python {script_name} --session <会话ID>")
        else:
            print("    ⚠ 数据库中没有找到有数据的会话")
        
        return 1
    print(f"    ✓ {message}")
    
    # 4. 创建Qt应用
    print("\n[4] 初始化Qt应用...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    print("    ✓ Qt应用初始化成功")
    
    # 5. 创建并显示对话框
    print("\n[5] 创建切线法分析对话框...")
    try:
        dialog = TangentAnalysisDialog(
            session_id=session_id,
            db=db,
            config=config,
            parent=None
        )
        print("    ✓ 对话框创建成功")
        print("\n" + "=" * 80)
        print("对话框已打开，请查看分析结果")
        print("关闭对话框后程序将退出")
        print("=" * 80 + "\n")
        
        # 显示对话框（模态）
        dialog.exec()
        
        print("\n对话框已关闭")
        
    except Exception as e:
        print(f"    ✗ 创建或显示对话框失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试显示错误对话框
        try:
            QMessageBox.critical(
                None,
                "错误",
                f"创建切线法分析对话框失败:\n{e}\n\n详细信息请查看控制台输出"
            )
        except Exception:
            pass
        
        return 1
    
    # 6. 清理资源
    try:
        db.close()
        print("✓ 数据库连接已关闭")
    except Exception:
        pass
    
    print("\n测试完成！")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断程序")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
