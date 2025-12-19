#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
切线法检测器可视化测试脚本
测试 _plot_tangent_analysis 方法的绘制效果
"""

import sys
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
import pyqtgraph as pg
from utils.tangent_method_detector import TangentMethodDetector


class TangentMethodVisualizationWindow(QMainWindow):
    """切线法可视化测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("切线法检测器可视化测试")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置深色主题
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12pt;
                padding: 10px;
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title = QLabel("切线法着火点检测可视化")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a9eff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', '温度', units='°C')
        self.plot_widget.setLabel('bottom', '时间', units='秒')
        self.plot_widget.setTitle("温度-时间曲线及切线法分析", color='#e0e0e0', size='14pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        layout.addWidget(self.plot_widget)
        
        # 结果标签
        self.result_label = QLabel()
        self.result_label.setStyleSheet("font-size: 11pt; background-color: #3a3a3a; border-radius: 5px;")
        layout.addWidget(self.result_label)
        
        # 执行测试
        self.run_test()
    
    def run_test(self):
        """运行测试"""
        print("=" * 60)
        print("切线法检测器可视化测试")
        print("=" * 60)
        
        # 1. 生成模拟温度数据
        print("\n1. 生成模拟温度数据...")
        time_array, temp_array = self.generate_test_data()
        print(f"   数据点数: {len(time_array)}")
        print(f"   时间范围: {time_array[0]:.1f}s - {time_array[-1]:.1f}s")
        print(f"   温度范围: {temp_array.min():.1f}°C - {temp_array.max():.1f}°C")
        
        # 2. 创建检测器并检测
        print("\n2. 执行切线法检测...")
        detector = TangentMethodDetector({
            'smooth_window': 11,
            'smooth_order': 2,
            'baseline_points': 20,
            'peak_points': 10,
            'min_temp_rise': 20.0,
            'min_rate_increase': 2.0,
            'min_data_points': 50
        })
        
        result = detector.detect_ignition(time_array, temp_array)
        
        if result is None:
            print("   ✗ 检测失败！")
            self.result_label.setText("检测失败：未找到明显的放热峰")
            return
        
        print(f"   ✓ 检测成功！")
        print(f"   着火点温度: {result['ignition_temp']:.1f}°C")
        print(f"   着火点时刻: {result['ignition_time']:.1f}秒")
        print(f"   置信度: {result['confidence']:.2f}")
        print(f"   基线拟合: y = {result['baseline_fit'][0]:.3f}x + {result['baseline_fit'][1]:.3f}")
        print(f"   峰顶拟合: y = {result['peak_fit'][0]:.3f}x + {result['peak_fit'][1]:.3f}")
        print(f"   基线相关系数: {result['baseline_r']:.3f}")
        print(f"   峰顶相关系数: {result['peak_r']:.3f}")
        
        # 3. 绘制结果
        print("\n3. 绘制可视化结果...")
        self.plot_results(time_array, temp_array, result)
        
        # 4. 更新结果标签
        result_text = (
            f"<b>检测结果:</b><br>"
            f"着火点温度: <span style='color: #ff9800; font-size: 14pt;'>{result['ignition_temp']:.1f}°C</span><br>"
            f"着火点时刻: <span style='color: #4a9eff;'>{result['ignition_time']:.1f}秒</span><br>"
            f"置信度: <span style='color: #4caf50;'>{result['confidence']:.2f}</span><br>"
            f"基线拟合: y = {result['baseline_fit'][0]:.3f}x + {result['baseline_fit'][1]:.3f} (R={result['baseline_r']:.3f})<br>"
            f"峰顶拟合: y = {result['peak_fit'][0]:.3f}x + {result['peak_fit'][1]:.3f} (R={result['peak_r']:.3f})"
        )
        self.result_label.setText(result_text)
        
        print("   ✓ 绘制完成！")
        print("\n" + "=" * 60)
    
    def generate_test_data(self):
        """
        生成测试数据（模拟煤粉着火过程）
        
        返回:
            time_array: 时间数组
            temp_array: 温度数组
        """
        # 时间：0-120秒，每0.5秒一个点
        time = np.linspace(0, 120, 240)
        
        # 第一段：室温到200°C的预热阶段（0-30秒）
        # 线性升温：约 2°C/秒
        segment1_mask = time <= 30
        segment1_temp = 25 + 2.0 * time[segment1_mask]
        
        # 第二段：200-350°C的缓慢升温阶段（30-60秒）
        # 线性升温：约 2.5°C/秒
        segment2_mask = (time > 30) & (time <= 60)
        segment2_temp = 85 + 2.5 * (time[segment2_mask] - 30)
        
        # 第三段：350-400°C的着火过渡阶段（60-65秒）
        # 开始加速升温：3-8°C/秒（指数增长）
        segment3_mask = (time > 60) & (time <= 65)
        t3 = time[segment3_mask] - 60
        segment3_temp = 160 + 3 * t3 + 0.5 * t3**2
        
        # 第四段：400-550°C的快速放热阶段（65-75秒）
        # 快速升温：约 15°C/秒
        segment4_mask = (time > 65) & (time <= 75)
        segment4_temp = 172.5 + 15 * (time[segment4_mask] - 65)
        
        # 第五段：550-600°C的燃烧后期（75-90秒）
        # 减速升温：约 5°C/秒
        segment5_mask = (time > 75) & (time <= 90)
        segment5_temp = 322.5 + 5 * (time[segment5_mask] - 75)
        
        # 第六段：600-650°C的稳定燃烧阶段（90-120秒）
        # 缓慢升温：约 1.7°C/秒
        segment6_mask = time > 90
        segment6_temp = 397.5 + 1.7 * (time[segment6_mask] - 90)
        
        # 合并所有段
        temp = np.concatenate([
            segment1_temp,
            segment2_temp,
            segment3_temp,
            segment4_temp,
            segment5_temp,
            segment6_temp
        ])
        
        # 添加随机噪声（模拟测量误差）
        noise = np.random.normal(0, 1.5, len(temp))
        temp += noise
        
        return time, temp
    
    def plot_results(self, time_array, temp_array, result):
        """
        绘制检测结果
        
        参数:
            time_array: 时间数组
            temp_array: 温度数组
            result: 检测结果字典
        """
        # 清空之前的图表
        self.plot_widget.clear()
        self.plot_widget.addLegend()
        
        # 1. 绘制原始温度曲线（青色实线）
        self.plot_widget.plot(
            time_array, temp_array,
            pen=pg.mkPen(color='#00d9ff', width=2),
            name='温度曲线'
        )
        
        # 2. 绘制基线拟合（红色虚线）
        k1, b1 = result['baseline_fit']
        baseline_range = result['baseline_range']
        baseline_time = time_array[baseline_range[0]:baseline_range[1]]
        baseline_temp = k1 * baseline_time + b1
        
        # 延伸基线到交点附近
        extended_time = np.linspace(baseline_time[0], result['ignition_time'] + 5, 50)
        extended_baseline = k1 * extended_time + b1
        
        self.plot_widget.plot(
            extended_time, extended_baseline,
            pen=pg.mkPen(color='#ff4444', width=2, style=Qt.DashLine),
            name='基线拟合'
        )
        
        # 3. 绘制峰顶拟合（蓝色虚线）
        k2, b2 = result['peak_fit']
        peak_range = result['peak_range']
        peak_time = time_array[peak_range[0]:peak_range[1]]
        peak_temp = k2 * peak_time + b2
        
        # 延伸峰顶线到交点附近
        extended_peak_time = np.linspace(result['ignition_time'] - 5, peak_time[-1], 50)
        extended_peak = k2 * extended_peak_time + b2
        
        self.plot_widget.plot(
            extended_peak_time, extended_peak,
            pen=pg.mkPen(color='#4444ff', width=2, style=Qt.DashLine),
            name='峰顶拟合'
        )
        
        # 4. 标注拐点和峰顶
        inflection_idx = result['inflection_idx']
        peak_idx = result['peak_idx']
        
        # 拐点标记（黄色）
        self.plot_widget.plot(
            [time_array[inflection_idx]], [temp_array[inflection_idx]],
            symbol='o', symbolSize=10,
            symbolBrush=pg.mkBrush(color='yellow'),
            symbolPen=pg.mkPen(color='orange', width=2),
            name='拐点'
        )
        
        # 峰顶标记（绿色）
        self.plot_widget.plot(
            [time_array[peak_idx]], [temp_array[peak_idx]],
            symbol='o', symbolSize=10,
            symbolBrush=pg.mkBrush(color='lime'),
            symbolPen=pg.mkPen(color='green', width=2),
            name='峰顶'
        )
        
        # 5. 标注着火点（橙色大圆圈）
        t_ig = result['ignition_time']
        T_ig = result['ignition_temp']
        
        self.plot_widget.plot(
            [t_ig], [T_ig],
            symbol='o', symbolSize=15,
            symbolBrush=pg.mkBrush(color='orange'),
            symbolPen=pg.mkPen(color='red', width=3),
            name='着火点'
        )
        
        # 6. 添加着火点文本标注
        text = pg.TextItem(
            f"着火点\n{T_ig:.1f}°C\n{t_ig:.1f}s",
            color='orange',
            anchor=(0.5, 1.5),
            border=pg.mkPen(color='red', width=2),
            fill=pg.mkBrush(0, 0, 0, 150)
        )
        text.setPos(t_ig, T_ig)
        self.plot_widget.addItem(text)
        
        # 7. 添加垂直辅助线（从着火点到x轴）
        inf_line = pg.InfiniteLine(
            pos=t_ig,
            angle=90,
            pen=pg.mkPen(color='orange', width=1, style=Qt.DotLine)
        )
        self.plot_widget.addItem(inf_line)
        
        # 8. 添加水平辅助线（从着火点到y轴）
        inf_line_h = pg.InfiniteLine(
            pos=T_ig,
            angle=0,
            pen=pg.mkPen(color='orange', width=1, style=Qt.DotLine)
        )
        self.plot_widget.addItem(inf_line_h)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示窗口
    window = TangentMethodVisualizationWindow()
    window.show()
    
    print("\n窗口已打开，请查看可视化结果...")
    print("关闭窗口退出程序。")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

