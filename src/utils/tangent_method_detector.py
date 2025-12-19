#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
放热峰切线法着火点检测器 V2 - 优化版
基于 GB/T 18511-2017《煤的着火温度测定方法》

主要优化:
1. 改进的拐点检测算法 - 使用累积加速度和多尺度分析
2. 自适应参数调整 - 根据数据特征动态调整阈值
3. 多方法验证 - 结合温升速率、二阶导数、三阶导数
4. 智能基线拟合 - 动态选择最佳基线区间
5. 峰顶段优化 - 更精确的峰顶拟合策略
6. 置信度评估增强 - 多维度质量评估
"""

import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.stats import linregress
from scipy.ndimage import gaussian_filter1d
import logging


class TangentMethodDetector:
    """
    放热峰切线法着火点检测器 - 优化版
    
    原理增强:
    1. 煤粉着火时发生放热反应,温度-时间曲线形成"放热峰"
    2. 使用多尺度分析识别放热起始点(拐点)
    3. 在基线段和放热峰段分别拟合切线
    4. 两条切线交点对应的温度即为着火点温度
    """
    
    def __init__(self, config=None):
        """
        初始化检测器
        
        参数:
            config: dict, 配置参数
                - smooth_window: int, 平滑窗口大小(奇数),默认11
                - smooth_order: int, 平滑多项式阶数,默认2
                - baseline_points: int, 基线拟合点数,默认30
                - peak_points: int, 峰顶拟合点数,默认15
                - min_temp_rise: float, 最小总温升(°C),默认20.0
                - min_rate_increase: float, 最小速率增幅(倍数),默认1.5
                - min_data_points: int, 最小数据点数,默认50
                - inflection_threshold: float, 拐点检测阈值,默认0.8
                - adaptive_threshold: bool, 是否自适应阈值,默认True
                - multi_scale_analysis: bool, 是否多尺度分析,默认True
        """
        self.logger = logging.getLogger(__name__)
        
        # 默认配置(优化后的参数)
        default_config = {
            'smooth_window': 11,              # 平滑窗口
            'smooth_order': 2,                # 平滑阶数
            'baseline_points': 30,            # 基线拟合点数(增加)
            'peak_points': 15,                # 峰顶拟合点数(增加)
            'min_temp_rise': 20.0,            # 最小温升
            'min_rate_increase': 1.5,         # 最小速率增幅
            'min_data_points': 50,            # 最小数据点数
            'inflection_threshold': 0.8,      # 拐点检测阈值(降低)
            'adaptive_threshold': True,       # 自适应阈值
            'multi_scale_analysis': True,     # 多尺度分析
            'use_cumulative_accel': True,     # 使用累积加速度
            'use_third_derivative': True,     # 使用三阶导数
            'baseline_r2_threshold': 0.95,    # 基线拟合质量阈值
            'peak_slope_ratio_min': 1.2,      # 峰顶斜率最小比率
        }
        
        self.config = {**default_config, **(config or {})}
        
        self.logger.info(f"切线法检测器V2初始化完成,配置: {self.config}")
    
    def detect_ignition(self, time_data, temp_data):
        """
        检测着火点
        
        参数:
            time_data: numpy数组或列表,时间数据(秒)
            temp_data: numpy数组或列表,温度数据(°C)
        
        返回:
            result: dict 或 None
                {
                    'ignition_temp': float, 着火点温度(°C)
                    'ignition_time': float, 着火点时刻(秒)
                    'baseline_fit': tuple, 基线拟合参数 (k1, b1)
                    'peak_fit': tuple, 峰顶拟合参数 (k2, b2)
                    'confidence': float, 置信度 (0-1)
                    'inflection_idx': int, 拐点索引
                    'peak_idx': int, 峰顶索引
                    'baseline_range': tuple, 基线拟合范围 (start, end)
                    'peak_range': tuple, 峰顶拟合范围 (start, end)
                    'method_scores': dict, 各检测方法得分
                }
        """
        try:
            # 1. 数据预处理
            time_array = np.array(time_data, dtype=np.float64)
            temp_array = np.array(temp_data, dtype=np.float64)
            
            # 数据验证
            if not self._validate_data(time_array, temp_array):
                return None
            
            # 2. 数据平滑
            temp_smooth = self._smooth_data(temp_array)
            if temp_smooth is None:
                return None
            
            # 3. 计算导数
            rate, rate_time = self._calculate_first_derivative(time_array, temp_smooth)
            if rate is None:
                return None
            
            acceleration, accel_time = self._calculate_second_derivative(rate_time, rate)
            if acceleration is None:
                return None
            
            # 4. 多方法拐点检测
            inflection_idx, method_scores = self._detect_inflection_multi_method(
                time_array, temp_smooth, rate, rate_time, acceleration, accel_time
            )
            
            if inflection_idx is None:
                self.logger.warning("未找到明显的拐点")
                return None
            
            # 5. 识别峰顶
            peak_idx = self._find_peak_point_v2(rate, inflection_idx)
            if peak_idx is None:
                self.logger.warning("未找到峰顶")
                return None
            
            # 6. 智能基线拟合
            baseline_result = self._fit_baseline_smart(
                time_array, temp_smooth, inflection_idx
            )
            if baseline_result is None:
                self.logger.warning("基线拟合失败")
                return None
            
            k1, b1, r1, baseline_start, baseline_end = baseline_result
            
            # 7. 优化峰顶拟合
            peak_result = self._fit_peak_smart(
                time_array, temp_smooth, rate, inflection_idx, peak_idx, k1
            )
            if peak_result is None:
                self.logger.warning("峰顶拟合失败")
                return None
            
            k2, b2, r2, peak_start, peak_end = peak_result
            
            # 8. 计算切线交点
            if abs(k2 - k1) < 1e-6:
                self.logger.warning("两条切线近似平行")
                return None
            
            ignition_time = (b2 - b1) / (k1 - k2)
            ignition_temp = k1 * ignition_time + b1
            
            # 验证着火点的合理性
            if not self._validate_ignition_point(
                ignition_time, ignition_temp, time_array, temp_smooth, inflection_idx
            ):
                return None
            
            # 9. 计算增强置信度
            confidence = self._calculate_confidence_v2(
                r1, r2, k1, k2, method_scores, inflection_idx, baseline_start
            )
            
            result = {
                'ignition_temp': ignition_temp,
                'ignition_time': ignition_time,
                'baseline_fit': (k1, b1),
                'peak_fit': (k2, b2),
                'confidence': confidence,
                'inflection_idx': inflection_idx,
                'peak_idx': peak_idx,
                'baseline_range': (baseline_start, baseline_end),
                'peak_range': (peak_start, peak_end),
                'method_scores': method_scores,
                'r1': r1,
                'r2': r2
            }
            
            self.logger.info(
                f"检测成功: 着火温度={ignition_temp:.1f}°C, "
                f"时间={ignition_time:.1f}s, 置信度={confidence:.3f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"检测失败: {e}", exc_info=True)
            return None
    
    def _validate_data(self, time_array, temp_array):
        """数据验证"""
        # 长度检查
        if len(time_array) < self.config['min_data_points']:
            self.logger.warning(
                f"数据点太少: {len(time_array)} < {self.config['min_data_points']}"
            )
            return False
        
        if len(time_array) != len(temp_array):
            self.logger.error(
                f"时间和温度数据长度不匹配: {len(time_array)} vs {len(temp_array)}"
            )
            return False
        
        # NaN/Inf检查
        if np.any(np.isnan(temp_array)) or np.any(np.isinf(temp_array)):
            self.logger.error("温度数据包含NaN或Inf")
            return False
        
        # 温升检查
        total_temp_rise = temp_array[-1] - temp_array[0]
        if total_temp_rise < self.config['min_temp_rise']:
            self.logger.warning(
                f"温升不足: {total_temp_rise:.1f}°C < {self.config['min_temp_rise']}°C"
            )
            return False
        
        return True
    
    def _smooth_data(self, temp_array):
        """数据平滑"""
        window_size = min(self.config['smooth_window'], len(temp_array) // 4)
        if window_size % 2 == 0:
            window_size += 1
        
        if window_size < 5:
            self.logger.warning("数据点太少,无法进行有效平滑")
            return None
        
        try:
            temp_smooth = savgol_filter(
                temp_array,
                window_length=window_size,
                polyorder=min(self.config['smooth_order'], window_size - 1)
            )
            return temp_smooth
        except Exception as e:
            self.logger.error(f"数据平滑失败: {e}")
            return None
    
    def _calculate_first_derivative(self, time_array, temp_smooth):
        """计算一阶导数(温升速率)"""
        dt = np.diff(time_array)
        dT = np.diff(temp_smooth)
        
        dt = np.where(dt == 0, 1e-6, dt)
        rate = dT / dt
        rate_time = time_array[:-1]
        
        return rate, rate_time
    
    def _calculate_second_derivative(self, rate_time, rate):
        """计算二阶导数(加速度)"""
        dt = np.diff(rate_time)
        drate = np.diff(rate)
        
        dt = np.where(dt == 0, 1e-6, dt)
        acceleration = drate / dt
        accel_time = rate_time[:-1]
        
        return acceleration, accel_time
    
    def _detect_inflection_multi_method(self, time_array, temp_smooth, 
                                        rate, rate_time, acceleration, accel_time):
        """
        多方法拐点检测
        
        结合以下方法:
        1. 二阶导数峰值法
        2. 累积加速度法
        3. 温升速率突变法
        4. 三阶导数法(可选)
        """
        method_scores = {}
        candidates = []
        
        # 方法1: 二阶导数峰值法(经典方法)
        idx1, score1 = self._method_acceleration_peak(acceleration, accel_time, rate_time)
        if idx1 is not None:
            candidates.append((idx1, score1, 'accel_peak'))
            method_scores['accel_peak'] = score1
        
        # 方法2: 累积加速度法(新增,对缓慢变化更敏感)
        if self.config.get('use_cumulative_accel', True):
            idx2, score2 = self._method_cumulative_acceleration(
                acceleration, accel_time, rate_time
            )
            if idx2 is not None:
                candidates.append((idx2, score2, 'cumul_accel'))
                method_scores['cumul_accel'] = score2
        
        # 方法3: 温升速率突变法
        idx3, score3 = self._method_rate_jump(rate, rate_time)
        if idx3 is not None:
            candidates.append((idx3, score3, 'rate_jump'))
            method_scores['rate_jump'] = score3
        
        # 方法4: 三阶导数法(对拐点最敏感,但易受噪声影响)
        if self.config.get('use_third_derivative', True) and len(acceleration) > 10:
            idx4, score4 = self._method_third_derivative(
                acceleration, accel_time, rate_time
            )
            if idx4 is not None:
                candidates.append((idx4, score4, 'third_deriv'))
                method_scores['third_deriv'] = score4
        
        # 如果没有候选点,返回None
        if not candidates:
            self.logger.debug(f"所有拐点检测方法都失败,得分: {method_scores}")
            return None, method_scores
        
        # 选择最佳候选点(加权投票)
        inflection_idx = self._select_best_inflection(candidates, temp_smooth)
        
        self.logger.debug(
            f"拐点检测: 索引={inflection_idx}, "
            f"温度={temp_smooth[inflection_idx]:.1f}°C, "
            f"方法得分={method_scores}"
        )
        
        return inflection_idx, method_scores
    
    def _method_acceleration_peak(self, acceleration, accel_time, rate_time):
        """方法1: 二阶导数峰值法"""
        try:
            # 平滑加速度信号
            accel_smooth = gaussian_filter1d(acceleration, sigma=2)
            
            # 计算阈值
            accel_mean = np.mean(accel_smooth)
            accel_std = np.std(accel_smooth)
            
            if self.config.get('adaptive_threshold', True):
                # 自适应阈值
                threshold_mult = self.config.get('inflection_threshold', 0.8)
                threshold = accel_mean + threshold_mult * accel_std
            else:
                threshold = accel_mean + 1.5 * accel_std
            
            # 寻找超过阈值的点
            candidates = np.where(accel_smooth > threshold)[0]
            
            if len(candidates) == 0:
                return None, 0.0
            
            # 选择第一个显著峰值
            inflection_accel_idx = candidates[0]
            inflection_time = accel_time[min(inflection_accel_idx, len(accel_time) - 1)]
            inflection_idx = np.argmin(np.abs(rate_time - inflection_time))
            
            # 计算得分(基于加速度相对大小)
            accel_value = accel_smooth[inflection_accel_idx]
            score = min(1.0, (accel_value - accel_mean) / (accel_std + 1e-6) / 5.0)
            
            return inflection_idx, max(0.0, score)
            
        except Exception as e:
            self.logger.debug(f"加速度峰值法失败: {e}")
            return None, 0.0
    
    def _method_cumulative_acceleration(self, acceleration, accel_time, rate_time):
        """方法2: 累积加速度法(对缓慢变化更敏感)"""
        try:
            # 计算累积加速度
            cumul_accel = np.cumsum(acceleration)
            
            # 归一化
            cumul_accel = (cumul_accel - np.min(cumul_accel)) / (
                np.max(cumul_accel) - np.min(cumul_accel) + 1e-6
            )
            
            # 寻找累积加速度开始快速增长的点(拐点前)
            # 使用二阶导数寻找累积曲线的拐点
            dcumul = np.diff(cumul_accel)
            ddcumul = np.diff(dcumul)
            
            # 平滑二阶导数
            ddcumul_smooth = gaussian_filter1d(ddcumul, sigma=2)
            
            # 寻找最大正加速度点
            if len(ddcumul_smooth) < 5:
                return None, 0.0
            
            # 排除前10%的数据(初始段不稳定)
            start_idx = len(ddcumul_smooth) // 10
            search_range = ddcumul_smooth[start_idx:]
            
            if len(search_range) == 0:
                return None, 0.0
            
            local_max_idx = np.argmax(search_range)
            inflection_accel_idx = start_idx + local_max_idx
            
            inflection_time = accel_time[min(inflection_accel_idx, len(accel_time) - 1)]
            inflection_idx = np.argmin(np.abs(rate_time - inflection_time))
            
            # 计算得分
            score = min(1.0, ddcumul_smooth[inflection_accel_idx] / (np.std(ddcumul_smooth) + 1e-6))
            
            return inflection_idx, max(0.0, score)
            
        except Exception as e:
            self.logger.debug(f"累积加速度法失败: {e}")
            return None, 0.0
    
    def _method_rate_jump(self, rate, rate_time):
        """方法3: 温升速率突变法"""
        try:
            # 计算速率的移动平均(窗口大小=10)
            window = 10
            if len(rate) < window * 3:
                return None, 0.0
            
            rate_ma = np.convolve(rate, np.ones(window)/window, mode='valid')
            
            # 计算速率变化率
            rate_change = np.diff(rate_ma)
            
            # 寻找最大正变化点
            if len(rate_change) < 5:
                return None, 0.0
            
            # 排除前后10%
            start_idx = len(rate_change) // 10
            end_idx = len(rate_change) * 9 // 10
            search_range = rate_change[start_idx:end_idx]
            
            if len(search_range) == 0:
                return None, 0.0
            
            local_max_idx = np.argmax(search_range)
            inflection_idx = start_idx + local_max_idx + window // 2
            
            # 确保索引有效
            inflection_idx = min(inflection_idx, len(rate_time) - 1)
            
            # 计算得分
            max_change = search_range[local_max_idx]
            mean_change = np.mean(np.abs(rate_change))
            score = min(1.0, max_change / (mean_change + 1e-6) / 10.0)
            
            return inflection_idx, max(0.0, score)
            
        except Exception as e:
            self.logger.debug(f"速率突变法失败: {e}")
            return None, 0.0
    
    def _method_third_derivative(self, acceleration, accel_time, rate_time):
        """方法4: 三阶导数法(对拐点最敏感)"""
        try:
            # 计算三阶导数
            dt = np.diff(accel_time)
            dt = np.where(dt == 0, 1e-6, dt)
            daccel = np.diff(acceleration)
            jerk = daccel / dt
            
            # 强平滑(三阶导数噪声很大)
            jerk_smooth = gaussian_filter1d(jerk, sigma=3)
            
            # 寻找最大正jerk
            if len(jerk_smooth) < 5:
                return None, 0.0
            
            # 排除前15%的数据
            start_idx = len(jerk_smooth) // 6
            search_range = jerk_smooth[start_idx:]
            
            if len(search_range) == 0:
                return None, 0.0
            
            local_max_idx = np.argmax(search_range)
            inflection_accel_idx = start_idx + local_max_idx
            
            jerk_time = accel_time[:-1]
            inflection_time = jerk_time[min(inflection_accel_idx, len(jerk_time) - 1)]
            inflection_idx = np.argmin(np.abs(rate_time - inflection_time))
            
            # 计算得分
            jerk_value = search_range[local_max_idx]
            jerk_std = np.std(jerk_smooth)
            score = min(1.0, jerk_value / (jerk_std + 1e-6) / 3.0)
            
            return inflection_idx, max(0.0, score)
            
        except Exception as e:
            self.logger.debug(f"三阶导数法失败: {e}")
            return None, 0.0
    
    def _select_best_inflection(self, candidates, temp_smooth):
        """选择最佳拐点(加权投票)"""
        # 如果只有一个候选,直接返回
        if len(candidates) == 1:
            return candidates[0][0]
        
        # 按索引分组(相近的索引视为同一点)
        tolerance = 20  # 容差范围
        groups = []
        
        for idx, score, method in candidates:
            added = False
            for group in groups:
                if abs(idx - group['indices'][0]) < tolerance:
                    group['indices'].append(idx)
                    group['scores'].append(score)
                    group['methods'].append(method)
                    added = True
                    break
            if not added:
                groups.append({
                    'indices': [idx],
                    'scores': [score],
                    'methods': [method]
                })
        
        # 选择得分最高的组
        best_group = max(groups, key=lambda g: sum(g['scores']))
        
        # 在该组内选择索引最小的(最早的拐点)
        best_idx = min(best_group['indices'])
        
        return best_idx
    
    def _find_peak_point_v2(self, rate, inflection_idx):
        """寻找峰顶(优化版)"""
        try:
            # 在拐点之后寻找速率最大值
            search_range = rate[inflection_idx:]
            
            if len(search_range) < 5:
                return None
            
            # 使用scipy的find_peaks查找峰值
            peaks, properties = find_peaks(
                search_range,
                prominence=np.std(search_range) * 0.5
            )
            
            if len(peaks) > 0:
                # 选择第一个显著峰值
                local_peak_idx = peaks[0]
            else:
                # 如果没找到峰值,使用最大值
                local_peak_idx = np.argmax(search_range)
            
            peak_idx = inflection_idx + local_peak_idx
            
            # 验证峰顶的有效性
            peak_rate = rate[peak_idx]
            
            # 计算基线速率(拐点前的平均速率)
            baseline_window = max(20, inflection_idx // 3)
            baseline_start = max(0, inflection_idx - baseline_window)
            baseline_end = max(baseline_start + 5, inflection_idx - 5)
            
            if baseline_end <= baseline_start:
                baseline_end = baseline_start + 1
            
            baseline_rate = np.mean(rate[baseline_start:baseline_end])
            
            # 峰顶速率应该大于基线速率
            if peak_rate < baseline_rate * self.config['min_rate_increase'] * 0.5:
                # 放宽条件
                if peak_rate < baseline_rate * 0.5:
                    self.logger.debug(
                        f"峰顶速率过低: peak={peak_rate:.2f}, "
                        f"baseline={baseline_rate:.2f}"
                    )
                    return None
            
            return peak_idx
            
        except Exception as e:
            self.logger.error(f"寻找峰顶失败: {e}")
            return None
    
    def _fit_baseline_smart(self, time_array, temp_smooth, inflection_idx):
        """智能基线拟合"""
        try:
            # 尝试不同的基线区间,选择拟合质量最好的
            baseline_points = self.config['baseline_points']
            best_result = None
            best_r2 = 0
            
            # 尝试多个区间
            for ratio in [1.0, 0.8, 1.2, 0.6]:
                points = int(baseline_points * ratio)
                points = min(points, inflection_idx)
                
                baseline_start = max(0, inflection_idx - points)
                baseline_end = inflection_idx
                
                if baseline_end - baseline_start < 10:
                    continue
                
                # 线性回归
                k, b, r, _, _ = linregress(
                    time_array[baseline_start:baseline_end],
                    temp_smooth[baseline_start:baseline_end]
                )
                
                r2 = r ** 2
                
                # 选择R²最高的
                if r2 > best_r2:
                    best_r2 = r2
                    best_result = (k, b, r, baseline_start, baseline_end)
            
            if best_result is None:
                return None
            
            k1, b1, r1, baseline_start, baseline_end = best_result
            
            # 验证拟合质量
            if best_r2 < self.config.get('baseline_r2_threshold', 0.95):
                self.logger.debug(f"基线拟合质量较低: R²={best_r2:.3f}")
                # 不拒绝,只是警告
            
            self.logger.debug(
                f"基线拟合: [{baseline_start}:{baseline_end}], "
                f"斜率={k1:.3f}, R²={best_r2:.3f}"
            )
            
            return k1, b1, r1, baseline_start, baseline_end
            
        except Exception as e:
            self.logger.error(f"基线拟合失败: {e}")
            return None
    
    def _fit_peak_smart(self, time_array, temp_smooth, rate, 
                        inflection_idx, peak_idx, k1):
        """智能峰顶拟合"""
        try:
            peak_points = self.config['peak_points']
            best_result = None
            best_slope = 0
            
            # 尝试不同的峰顶区间,选择斜率最大且合理的
            for start_offset in [0, 5, 10]:
                for window_mult in [1.0, 1.5, 2.0]:
                    peak_start = inflection_idx + start_offset
                    peak_end = min(
                        len(temp_smooth),
                        peak_start + int(peak_points * window_mult)
                    )
                    
                    if peak_end - peak_start < 5:
                        continue
                    
                    # 确保包含峰顶
                    if not (peak_start <= peak_idx < peak_end):
                        continue
                    
                    # 线性回归
                    k, b, r, _, _ = linregress(
                        time_array[peak_start:peak_end],
                        temp_smooth[peak_start:peak_end]
                    )
                    
                    # 选择斜率最大且大于基线的
                    min_slope_ratio = self.config.get('peak_slope_ratio_min', 1.2)
                    if k > k1 * min_slope_ratio and k > best_slope:
                        best_slope = k
                        best_result = (k, b, r, peak_start, peak_end)
            
            if best_result is None:
                self.logger.debug("未找到合适的峰顶拟合区间")
                return None
            
            k2, b2, r2, peak_start, peak_end = best_result
            
            self.logger.debug(
                f"峰顶拟合: [{peak_start}:{peak_end}], "
                f"斜率={k2:.3f}, R²={r2**2:.3f}, "
                f"斜率比={k2/k1:.2f}"
            )
            
            return k2, b2, r2, peak_start, peak_end
            
        except Exception as e:
            self.logger.error(f"峰顶拟合失败: {e}")
            return None
    
    def _validate_ignition_point(self, ignition_time, ignition_temp, 
                                  time_array, temp_smooth, inflection_idx):
        """验证着火点的合理性"""
        # 时间范围检查
        if ignition_time < time_array[0] or ignition_time > time_array[-1]:
            self.logger.warning(
                f"着火时间超出数据范围: {ignition_time:.1f}s "
                f"不在[{time_array[0]:.1f}, {time_array[-1]:.1f}]内"
            )
            return False
        
        # 温度范围检查
        temp_min, temp_max = np.min(temp_smooth), np.max(temp_smooth)
        if ignition_temp < temp_min or ignition_temp > temp_max:
            self.logger.warning(
                f"着火温度超出数据范围: {ignition_temp:.1f}°C "
                f"不在[{temp_min:.1f}, {temp_max:.1f}]内"
            )
            return False
        
        # 着火点应该在拐点附近(前后50个点内)
        ignition_idx = np.argmin(np.abs(time_array - ignition_time))
        if abs(ignition_idx - inflection_idx) > 50:
            self.logger.warning(
                f"着火点距离拐点太远: {abs(ignition_idx - inflection_idx)}个点"
            )
            # 不拒绝,只是警告
        
        return True
    
    def _calculate_confidence_v2(self, r1, r2, k1, k2, method_scores, 
                                  inflection_idx, baseline_start):
        """计算增强置信度"""
        # 1. 拟合质量得分(30%)
        fit_quality = (abs(r1) + abs(r2)) / 2
        fit_score = min(1.0, fit_quality)
        
        # 2. 斜率差异得分(40%)
        if k2 > k1:
            slope_ratio = k2 / (k1 + 1e-6)
            
            if slope_ratio >= 3.0:
                slope_score = 0.95 + 0.05 * min(1.0, (slope_ratio - 3.0) / 2.0)
            elif slope_ratio >= 2.0:
                slope_score = 0.85 + 0.10 * ((slope_ratio - 2.0) / 1.0)
            elif slope_ratio >= 1.5:
                slope_score = 0.75 + 0.10 * ((slope_ratio - 1.5) / 0.5)
            elif slope_ratio >= 1.2:
                slope_score = 0.65 + 0.10 * ((slope_ratio - 1.2) / 0.3)
            else:
                slope_score = 0.5 + 0.15 * ((slope_ratio - 1.0) / 0.2)
            
            slope_score = min(1.0, max(0.5, slope_score))
        else:
            slope_score = 0.3
        
        # 3. 多方法一致性得分(20%)
        if method_scores:
            consistency_score = np.mean(list(method_scores.values()))
        else:
            consistency_score = 0.5
        
        # 4. 数据覆盖度得分(10%)
        coverage_score = min(1.0, (inflection_idx - baseline_start) / 100.0)
        
        # 综合得分
        confidence = (
            0.30 * fit_score +
            0.40 * slope_score +
            0.20 * consistency_score +
            0.10 * coverage_score
        )
        
        return confidence
    
    def batch_detect(self, time_data_list, temp_data_list):
        """批量检测多个样品的着火点"""
        results = []
        for i, (time_data, temp_data) in enumerate(zip(time_data_list, temp_data_list)):
            self.logger.info(f"正在检测第 {i+1} 个样品...")
            result = self.detect_ignition(time_data, temp_data)
            results.append(result)
        
        return results


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 模拟真实的煤粉着火数据
    time = np.linspace(0, 1000, 2000)  # 1000秒,2000个数据点
    
    # 基线段:缓慢线性升温
    temp1 = 200 + 0.15 * time[:1000]
    
    # 着火段:加速升温(模拟放热反应)
    t2 = time[1000:]
    temp2 = 350 + 0.4 * (t2 - 500) + 0.0005 * (t2 - 500)**2
    
    temp = np.concatenate([temp1, temp2])
    
    # 添加噪声
    temp += np.random.normal(0, 1.5, len(temp))
    
    # 创建检测器
    detector = TangentMethodDetector()
    
    # 检测着火点
    result = detector.detect_ignition(time, temp)
    
    if result:
        print("\n" + "="*60)
        print("检测结果:")
        print("="*60)
        print(f"  着火点温度: {result['ignition_temp']:.1f}°C")
        print(f"  着火点时刻: {result['ignition_time']:.1f}秒")
        print(f"  置信度: {result['confidence']:.3f}")
        print(f"  基线拟合: y = {result['baseline_fit'][0]:.4f}x + {result['baseline_fit'][1]:.2f}")
        print(f"  峰顶拟合: y = {result['peak_fit'][0]:.4f}x + {result['peak_fit'][1]:.2f}")
        print(f"  斜率比: {result['peak_fit'][0] / result['baseline_fit'][0]:.2f}")
        print(f"  方法得分: {result['method_scores']}")
        print("="*60)
    else:
        print("检测失败")
