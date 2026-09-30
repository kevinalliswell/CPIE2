#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：直接从数据库读取实时数据并进行切线法分析（不考虑会话ID）
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / 'src'))

from models.ignition_database import IgnitionDatabase
from utils.tangent_method_detector import TangentMethodDetector
from utils.path_manager import PathManager


def test_tangent_analysis_direct(limit=None):
    """
    直接读取实时数据进行切线法分析
    
    Args:
        limit: 限制读取的数据条数（None表示全部）
    """
    print("=" * 80)
    print("切线法着火点分析测试 - 直接读取实时数据")
    print("=" * 80)
    
    # 1. 连接数据库
    print("\n[1] 连接数据库...")
    db_path = PathManager.get_data_path("ignition_experiment.db")
    print(f"    数据库路径: {db_path}")
    
    db = IgnitionDatabase(db_path)
    print("    ✓ 数据库连接成功")
    
    # 2. 读取实时数据
    print(f"\n[2] 读取实时数据...")
    if limit:
        print(f"    限制读取最新 {limit} 条数据")
        data = db.get_latest_data(limit=limit)
        # 按时间升序排列
        data = sorted(data, key=lambda x: x['timestamp'])
    else:
        print(f"    读取所有数据")
        data = db.get_all_data(order_by='timestamp', ascending=True)
    
    if not data:
        print(f"    ✗ 数据库中没有数据")
        db.close()
        return
    
    print(f"    ✓ 成功读取 {len(data)} 条数据记录")
    print(f"    时间范围: {data[0]['timestamp']} - {data[-1]['timestamp']}")
    
    # 3. 构建时间和温度数组
    print("\n[3] 构建时间和温度数组...")
    
    # 计算相对时间（秒）
    from datetime import datetime
    timestamps = []
    for record in data:
        try:
            ts = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            ts = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
        timestamps.append(ts)
    
    # 第一个时间戳作为起点
    start_time = timestamps[0]
    time_seconds = np.array([(ts - start_time).total_seconds() for ts in timestamps])
    time_minutes = time_seconds / 60.0
    
    print(f"    时间范围: 0 - {time_seconds[-1]:.1f}秒 ({time_minutes[-1]:.1f}分钟)")
    
    # 提取各通道温度
    temp_arrays = []
    for i in range(6):
        channel_name = f'ch{i+1}'
        temp_array = np.array([record[channel_name] for record in data])
        temp_arrays.append(temp_array)
        
        # 显示温度范围
        if np.max(temp_array) > 30:  # 有效数据
            print(f"    样品{i+1}: {temp_array.min():.1f}°C - {temp_array.max():.1f}°C (温升: {temp_array.max()-temp_array.min():.1f}°C)")
        else:
            print(f"    样品{i+1}: 无有效数据")
    
    # 4. 创建切线法检测器
    print("\n[4] 创建切线法检测器...")
    detector_config = {
        'smooth_window': 11,
        'smooth_order': 2,
        'baseline_points': 20,
        'peak_points': 10,
        'min_temp_rise': 20.0,
        'min_rate_increase': 2.0,
        'min_data_points': 50
    }
    detector = TangentMethodDetector(detector_config)
    print("    ✓ 检测器创建成功")
    print(f"    配置参数:")
    print(f"      - 平滑窗口: {detector_config['smooth_window']}")
    print(f"      - 最小温升: {detector_config['min_temp_rise']}°C")
    print(f"      - 最小数据点: {detector_config['min_data_points']}")
    
    # 5. 分析每个样品
    print("\n[5] 开始切线法分析...")
    print("-" * 80)
    
    results = []
    for i in range(6):
        print(f"\n样品 {i+1}:")
        
        temp_array = temp_arrays[i]
        
        # 检查数据有效性
        if len(temp_array) < detector_config['min_data_points']:
            print(f"  ✗ 数据点不足（{len(temp_array)}个，需要{detector_config['min_data_points']}个）")
            results.append(None)
            continue
        
        temp_rise = np.max(temp_array) - np.min(temp_array)
        if np.all(temp_array == 0) or np.max(temp_array) < 30:
            print(f"  ✗ 数据无效（全0或温度过低）")
            results.append(None)
            continue
        
        if temp_rise < detector_config['min_temp_rise']:
            print(f"  ✗ 温升不足（{temp_rise:.1f}°C < {detector_config['min_temp_rise']}°C）")
            results.append(None)
            continue
        
        # 执行切线法检测
        try:
            result = detector.detect_ignition(time_seconds, temp_array)
            
            if result is not None:
                results.append(result)
                
                print(f"  ✓ 检测成功")
                print(f"  着火点温度: {result['ignition_temp']:.1f}°C")
                print(f"  着火点时刻: {result['ignition_time']/60:.1f}分钟 ({result['ignition_time']:.0f}秒)")
                print(f"  置信度: {result['confidence']:.3f}")
                print(f"  基线拟合: y = {result['baseline_fit'][0]:.4f}x + {result['baseline_fit'][1]:.2f}")
                if 'baseline_r' in result:
                    print(f"    相关系数: R = {result['baseline_r']:.3f}")
                print(f"  峰顶拟合: y = {result['peak_fit'][0]:.4f}x + {result['peak_fit'][1]:.2f}")
                if 'peak_r' in result:
                    print(f"    相关系数: R = {result['peak_r']:.3f}")
            else:
                results.append(None)
                print(f"  ✗ 检测失败（未找到明显放热峰）")
        except Exception as e:
            results.append(None)
            print(f"  ✗ 检测异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 6. 绘制结果
    print("\n" + "-" * 80)
    print("\n[6] 绘制分析结果...")
    plot_results(time_minutes, temp_arrays, results)
    print("    ✓ 图表已生成")
    
    # 7. 汇总统计
    print("\n[7] 汇总统计:")
    print("-" * 80)
    
    success_count = sum(1 for r in results if r is not None)
    print(f"  成功检测: {success_count}/6 个样品")
    
    if success_count > 0:
        detected_temps = [r['ignition_temp'] for r in results if r is not None]
        detected_times = [r['ignition_time']/60 for r in results if r is not None]
        confidences = [r['confidence'] for r in results if r is not None]
        
        print(f"  温度范围: {min(detected_temps):.1f}°C - {max(detected_temps):.1f}°C")
        print(f"  平均温度: {np.mean(detected_temps):.1f}°C ± {np.std(detected_temps):.1f}°C")
        print(f"  时间范围: {min(detected_times):.1f}min - {max(detected_times):.1f}min")
        print(f"  平均时间: {np.mean(detected_times):.1f}min")
        print(f"  平均置信度: {np.mean(confidences):.3f}")
    else:
        print(f"  ⚠ 未检测到任何着火点")
    
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)
    
    # 关闭数据库
    db.close()
    
    return results


def plot_results(time_minutes, temp_arrays, results):
    """
    绘制分析结果
    
    Args:
        time_minutes: 时间数组（分钟）
        temp_arrays: 温度数组列表（6个样品）
        results: 分析结果列表（6个样品）
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建3x2子图（6个样品）
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('切线法着火点分析结果（直接读取实时数据）', fontsize=16, fontweight='bold')
    
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7dc6f', '#bb8fce', '#85c1e9']
    
    for i, ax in enumerate(axes.flat):
        temp_array = temp_arrays[i]
        result = results[i]
        
        # 绘制温度曲线
        ax.plot(time_minutes, temp_array, color=colors[i], linewidth=2, label='温度曲线', alpha=0.8)
        
        ax.set_xlabel('时间 (分钟)', fontsize=10)
        ax.set_ylabel('温度 (°C)', fontsize=10)
        ax.set_title(f'样品 {i+1}', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 如果有检测结果，绘制切线
        if result is not None:
            k1, b1 = result['baseline_fit']
            k2, b2 = result['peak_fit']
            baseline_range = result['baseline_range']
            peak_range = result['peak_range']
            t_ig_seconds = result['ignition_time']
            t_ig_minutes = t_ig_seconds / 60.0
            T_ig = result['ignition_temp']
            
            # 转换为秒用于计算
            time_seconds = time_minutes * 60
            
            # 绘制基线（延伸到交点）
            baseline_time_seconds = time_seconds[baseline_range[0]:baseline_range[1]]
            extended_baseline_time_seconds = np.linspace(
                baseline_time_seconds[0], 
                min(t_ig_seconds + 180, time_seconds[-1]),  # 延伸3分钟或到数据末尾
                50
            )
            extended_baseline_minutes = extended_baseline_time_seconds / 60.0
            extended_baseline_temp = k1 * extended_baseline_time_seconds + b1
            
            ax.plot(extended_baseline_minutes, extended_baseline_temp, 
                   'r--', linewidth=2, label='基线拟合', alpha=0.8)
            
            # 绘制峰顶线（延伸到交点）
            peak_time_seconds = time_seconds[peak_range[0]:peak_range[1]]
            extended_peak_time_seconds = np.linspace(
                max(baseline_time_seconds[0], t_ig_seconds - 180),
                peak_time_seconds[-1],
                50
            )
            extended_peak_minutes = extended_peak_time_seconds / 60.0
            extended_peak_temp = k2 * extended_peak_time_seconds + b2
            
            ax.plot(extended_peak_minutes, extended_peak_temp, 
                   'b:', linewidth=2, label='峰顶拟合', alpha=0.8)
            
            # 标注着火点
            ax.scatter([t_ig_minutes], [T_ig], s=200, c='orange', 
                      marker='*', edgecolors='red', linewidths=2, 
                      label='着火点', zorder=5)
            
            # 添加垂直辅助线
            ax.axvline(x=t_ig_minutes, color='orange', linestyle=':', 
                      linewidth=1, alpha=0.5)
            
            # 添加文本标注
            ax.text(t_ig_minutes, T_ig, 
                   f'\n{T_ig:.1f}°C\n{t_ig_minutes:.1f}min\n置信度:{result["confidence"]:.2f}',
                   ha='center', va='bottom', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
            
            ax.legend(loc='best', fontsize=8)
        else:
            # 无检测结果
            ax.text(0.5, 0.5, '未检测到着火点', 
                   ha='center', va='center', 
                   transform=ax.transAxes,
                   fontsize=12, color='red', fontweight='bold')
    
    plt.tight_layout()
    
    # 保存图片
    output_path = project_root / 'tests' / 'tangent_analysis_direct_result.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"    图表已保存: {output_path}")
    
    # 显示图表
    plt.show()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='切线法着火点分析测试（直接读取实时数据）')
    parser.add_argument('--limit', type=int, default=None, 
                       help='限制读取的数据条数（默认: 全部）')
    
    args = parser.parse_args()
    
    try:
        results = test_tangent_analysis_direct(limit=args.limit)
        
        if results:
            print("\n提示: 图表窗口已打开，关闭窗口退出程序。")
    
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


