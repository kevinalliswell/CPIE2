#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
放热峰切线法着火点检测器 V3
对温度曲线拟合基线与最大温升速率处的切线，估计交点。
数值回归验证不代表标准认证；实验结果仍需结合原始记录复核。

算法流程:
1. 温度曲线平滑（Savitzky-Golay）
2. 计算温升速率 dT/dt 及其加速度 d²T/dt²
3. 峰顶 = 温升速率最大值点（放热反应最剧烈处）
4. 起始点 = 从峰顶向前回溯，温升速率回落到基线水平的位置；拐点 = 起始点与峰顶之间加速度最大处
5. 基线段：起始点之前的线性升温段做线性拟合 L1
6. 峰顶段：以峰顶为中心的数据段做线性拟合 L2
7. 交点 (L1 ∩ L2) 对应的温度即为着火点温度；交点必须位于基线区间与峰顶之间

相对 V2 的主要修正:
- V2 以"拐点之后第一个局部峰"作为峰顶、并把峰顶拟合窗口锚定在拐点之后，
  放热峰稍慢时会把峰顶切线拟合在放热初期的缓坡上，着火温度整体偏高数十度；
- V2 的多方法投票没有整体显著性校验，纯升温曲线也会"检出"着火点。
"""

import logging

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter
from scipy.stats import linregress


class TangentMethodDetector:
    """放热峰切线法着火点检测器"""

    def __init__(self, config=None):
        """
        初始化检测器

        参数:
            config: dict, 配置参数
                - smooth_window: int, 温度平滑窗口(奇数), 默认11
                - smooth_order: int, 平滑多项式阶数, 默认2
                - baseline_points: int, 基线拟合点数(下限), 默认30
                - baseline_width_fraction: float, 基线拟合点数相对放热宽度(起始点→峰顶)的比例, 默认0.5
                - peak_points: int, 峰顶拟合点数, 默认15
                - min_temp_rise: float, 最小总温升(°C), 默认20.0
                - min_rate_increase: float, 峰顶温升速率相对基线的最小倍数, 默认1.5
                - min_data_points: int, 最小数据点数, 默认50
                - inflection_threshold: float, 拐点加速度显著性阈值(基线加速度标准差倍数), 默认0.8
                - onset_rise_fraction: float, 起始点粗判: 速率回落到基线以上该比例以内, 默认0.1
                - onset_residual_sigma: float, 起始点精判: 温度偏离基线超过残差标准差的倍数, 默认3.0
                - onset_guard_fraction: float, 基线拟合窗口相对起始点再前移的放热宽度比例, 默认0.15
                - peak_window_fraction: float, 峰顶拟合半窗口相对放热宽度(起始点→峰顶)的比例, 默认0.1
                - min_exotherm_rise: float, 峰顶处温度高于基线外推的最小值(°C), 默认3.0
                - rate_smooth_sigma: float, 温升速率高斯平滑 sigma(采样点), 默认2.0
                - baseline_r2_threshold: float, 基线拟合质量提示阈值, 默认0.95
                - peak_slope_ratio_min: float, 峰顶切线斜率相对基线的最小倍数, 默认1.2
        """
        self.logger = logging.getLogger(__name__)

        default_config = {
            'smooth_window': 11,
            'smooth_order': 2,
            'baseline_points': 30,
            'baseline_width_fraction': 0.5,
            'peak_points': 15,
            'min_temp_rise': 20.0,
            'min_rate_increase': 1.5,
            'min_data_points': 50,
            'inflection_threshold': 0.8,
            'onset_rise_fraction': 0.1,
            'onset_residual_sigma': 3.0,
            'onset_guard_fraction': 0.15,
            'peak_window_fraction': 0.1,
            'min_exotherm_rise': 3.0,
            'rate_smooth_sigma': 2.0,
            'baseline_r2_threshold': 0.95,
            'peak_slope_ratio_min': 1.2,
        }

        self.config = {**default_config, **(config or {})}
        self.logger.info(f"切线法检测器V3初始化完成,配置: {self.config}")

    # ------------------------------------------------------------------ 主流程
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
                    'inflection_idx': int, 拐点索引(起始点与峰顶之间加速度最大处)
                    'onset_idx': int, 放热起始点索引
                    'peak_idx': int, 峰顶索引
                    'baseline_range': tuple, 基线拟合范围 (start, end)
                    'peak_range': tuple, 峰顶拟合范围 (start, end)
                    'method_scores': dict, 各项质量评分
                    'r1', 'r2': float, 两段拟合的相关系数
                }
        """
        try:
            time_array = np.asarray(time_data, dtype=np.float64)
            temp_array = np.asarray(temp_data, dtype=np.float64)

            if not self._validate_data(time_array, temp_array):
                return None

            temp_smooth = self._smooth_data(temp_array)
            if temp_smooth is None or not np.all(np.isfinite(temp_smooth)):
                return None

            rate, rate_smooth, accel = self._derivatives(time_array, temp_smooth)
            if rate is None:
                return None

            # 1. 峰顶：温升速率最大值（多尺度平滑，取峰值相对噪声最显著的尺度，
            #    避免放热弱而缓时被基线段的噪声尖峰抢占 argmax）
            peak_search = self._find_peak_multiscale(time_array, rate, rate_smooth)
            if peak_search is None:
                self.logger.warning("未找到峰顶")
                return None
            peak_idx, rate_smooth, accel = peak_search

            # 2. 基线速率与峰顶显著性
            baseline_rate = float(np.median(rate_smooth[:peak_idx]))
            peak_rate = float(rate_smooth[peak_idx])
            if not self._peak_is_significant(peak_rate, baseline_rate):
                self.logger.warning(
                    f"放热峰不显著: 峰顶速率={peak_rate:.3f}, 基线速率={baseline_rate:.3f}"
                )
                return None

            # 3. 起始点（粗判：速率回落到基线水平）
            onset_idx = self._find_onset(rate_smooth, peak_idx, baseline_rate, peak_rate)
            if onset_idx is None:
                self.logger.warning("未找到放热起始点")
                return None

            # 放热较慢时速率峰平坦、受噪声影响大：按放热宽度加大平滑后重新定位峰顶
            peak_idx = self._refine_peak(rate, rate_smooth, onset_idx, peak_idx)

            # 起始点精判：温度偏离基线外推超过噪声水平处（比速率判据更早、更稳定）
            onset_idx = self._refine_onset(time_array, temp_smooth, onset_idx, peak_idx)
            if onset_idx is None:
                self.logger.warning("放热起始点精判失败")
                return None

            inflection_idx = onset_idx + int(np.argmax(accel[onset_idx:peak_idx + 1]))
            if not self._inflection_is_significant(accel, onset_idx, inflection_idx):
                self.logger.warning("拐点加速度不显著")
                return None

            # 4. 基线拟合（起始点之前，再按放热宽度前移一段以避开放热初期缓坡）
            baseline_result = self._fit_baseline(
                time_array, temp_smooth, self._baseline_end_index(onset_idx, peak_idx),
                width=peak_idx - onset_idx,
            )
            if baseline_result is None:
                self.logger.warning("基线拟合失败")
                return None
            k1, b1, r1, baseline_start, baseline_end = baseline_result

            # 峰顶处温度必须明显高于基线外推，否则只是噪声造成的速率起伏
            exotherm_rise = float(temp_smooth[peak_idx] - (k1 * time_array[peak_idx] + b1))
            if exotherm_rise < float(self.config['min_exotherm_rise']):
                self.logger.warning(
                    f"放热量不足: 峰顶温度高于基线外推 {exotherm_rise:.2f}°C "
                    f"< {self.config['min_exotherm_rise']}°C"
                )
                return None

            # 5. 峰顶拟合（以峰顶为中心）
            peak_result = self._fit_peak(time_array, temp_smooth, onset_idx, peak_idx, k1)
            if peak_result is None:
                self.logger.warning("峰顶拟合失败")
                return None
            k2, b2, r2, peak_start, peak_end = peak_result

            # 6. 切线交点
            if abs(k2 - k1) < 1e-6:
                self.logger.warning("两条切线近似平行")
                return None
            ignition_time = (b2 - b1) / (k1 - k2)
            ignition_temp = k1 * ignition_time + b1

            if not self._validate_ignition_point(
                ignition_time, ignition_temp, time_array, temp_smooth, baseline_start, peak_idx
            ):
                return None

            # 7. 置信度
            method_scores = {
                'rate_ratio': self._clamp01(
                    (peak_rate / (baseline_rate + 1e-9)) / (2.0 * float(self.config['min_rate_increase']))
                    if baseline_rate > 0 else 1.0
                ),
                'onset_sharpness': self._clamp01((peak_idx - onset_idx) and
                                                 1.0 - (inflection_idx - onset_idx) / max(1, peak_idx - onset_idx)),
            }
            confidence = self._calculate_confidence(r1, r2, k1, k2, method_scores, baseline_end - baseline_start)

            if not np.all(np.isfinite([k1, b1, k2, b2, r1, r2, confidence,
                                       *method_scores.values()])):
                self.logger.warning("拟合结果包含非有限数值")
                return None

            result = {
                'ignition_temp': float(ignition_temp),
                'ignition_time': float(ignition_time),
                'baseline_fit': (float(k1), float(b1)),
                'peak_fit': (float(k2), float(b2)),
                'confidence': float(confidence),
                'inflection_idx': int(inflection_idx),
                'onset_idx': int(onset_idx),
                'peak_idx': int(peak_idx),
                'baseline_range': (int(baseline_start), int(baseline_end)),
                'peak_range': (int(peak_start), int(peak_end)),
                'method_scores': method_scores,
                'r1': float(r1),
                'r2': float(r2),
            }

            self.logger.info(
                f"检测成功: 着火温度={ignition_temp:.1f}°C, 时间={ignition_time:.1f}s, "
                f"置信度={confidence:.3f}, 斜率比={k2 / k1 if k1 else float('inf'):.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"检测失败: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------ 预处理
    def _validate_data(self, time_array, temp_array):
        """数据验证"""
        if time_array.ndim != 1 or temp_array.ndim != 1:
            self.logger.error("时间和温度数据必须是一维数组")
            return False
        if len(time_array) < self.config['min_data_points']:
            self.logger.warning(f"数据点太少: {len(time_array)} < {self.config['min_data_points']}")
            return False
        if len(time_array) != len(temp_array):
            self.logger.error(f"时间和温度数据长度不匹配: {len(time_array)} vs {len(temp_array)}")
            return False
        if not np.all(np.isfinite(time_array)) or not np.all(np.isfinite(temp_array)):
            self.logger.error("时间或温度数据包含NaN或Inf")
            return False
        with np.errstate(over='ignore', invalid='ignore'):
            intervals = np.diff(time_array)
        if not np.all(np.isfinite(intervals)) or np.any(intervals <= 0):
            self.logger.error("时间数据必须严格递增")
            return False
        total_temp_rise = float(np.max(temp_array) - temp_array[0])
        if total_temp_rise < self.config['min_temp_rise']:
            self.logger.warning(f"温升不足: {total_temp_rise:.1f}°C < {self.config['min_temp_rise']}°C")
            return False
        return True

    def _smooth_data(self, temp_array):
        """温度数据平滑"""
        window_size = min(int(self.config['smooth_window']), len(temp_array) // 4)
        if window_size % 2 == 0:
            window_size += 1
        if window_size < 5:
            self.logger.warning("数据点太少,无法进行有效平滑")
            return None
        try:
            return savgol_filter(
                temp_array,
                window_length=window_size,
                polyorder=min(int(self.config['smooth_order']), window_size - 1),
            )
        except Exception as e:
            self.logger.error(f"数据平滑失败: {e}")
            return None

    def _derivatives(self, time_array, temp_smooth):
        """温升速率(原始/平滑)与加速度"""
        try:
            rate = np.gradient(temp_smooth, time_array)
            sigma = float(self.config.get('rate_smooth_sigma', 2.0))
            rate_smooth = gaussian_filter1d(rate, sigma=sigma) if sigma > 0 else rate.copy()
            accel = np.gradient(rate_smooth, time_array)
            if not all(np.all(np.isfinite(values)) for values in (rate, rate_smooth, accel)):
                self.logger.warning("数据跨度或采样间隔导致导数不可表示")
                return None, None, None
            return rate, rate_smooth, accel
        except Exception as e:
            self.logger.error(f"计算导数失败: {e}")
            return None, None, None

    # ------------------------------------------------------------------ 特征点
    def _find_peak(self, rate_smooth, sigma=0.0):
        """峰顶 = 温升速率最大值点（排除两端受平滑影响的边缘点）"""
        n = len(rate_smooth)
        edge = max(3, int(self.config['smooth_window']) // 2, int(3 * sigma))
        if n <= 2 * edge + 5:
            return None
        local = int(np.argmax(rate_smooth[edge:n - edge]))
        peak_idx = edge + local
        # 峰顶之前必须有足够的基线数据
        if peak_idx < max(10, int(self.config['min_data_points']) // 4):
            self.logger.debug(f"峰顶过早: idx={peak_idx}")
            return None
        return peak_idx

    def _find_peak_multiscale(self, time_array, rate, rate_smooth):
        """
        多尺度峰顶搜索：在 rate_smooth_sigma 的 1/2/4/8/16 倍尺度上分别平滑速率，
        取"峰值高出中位数的倍数(以 MAD 估计噪声)"最大的尺度。返回 (peak_idx, rate_smooth, accel)。
        """
        base_sigma = max(0.0, float(self.config.get('rate_smooth_sigma', 2.0)))
        n = len(rate)
        best = None
        best_z = -np.inf
        for mult in (1, 2, 4, 8, 16):
            sigma = base_sigma * mult
            if mult > 1 and (base_sigma <= 0 or sigma > n / 20.0):
                break
            if mult == 1:
                candidate = rate_smooth
            else:
                try:
                    candidate = gaussian_filter1d(rate, sigma=sigma)
                except Exception as e:
                    self.logger.debug(f"速率平滑失败(sigma={sigma}): {e}")
                    break
            peak_idx = self._find_peak(candidate, sigma)
            if peak_idx is None:
                continue
            pre = candidate[:peak_idx]
            median = float(np.median(pre))
            noise = 1.4826 * float(np.median(np.abs(pre - median)))
            z = (float(candidate[peak_idx]) - median) / max(noise, 1e-9)
            if z > best_z:
                best_z = z
                best = (peak_idx, candidate)
        if best is None:
            return None
        peak_idx, chosen = best
        accel = np.gradient(chosen, time_array)
        return peak_idx, chosen, accel

    def _peak_is_significant(self, peak_rate, baseline_rate):
        """峰顶速率必须显著高于基线速率"""
        if peak_rate <= 0:
            return False
        if baseline_rate > 1e-9:
            return peak_rate >= baseline_rate * float(self.config['min_rate_increase'])
        # 基线几乎不升温：只要求峰顶速率为正
        return True

    def _find_onset(self, rate_smooth, peak_idx, baseline_rate, peak_rate):
        """从峰顶向前回溯，温升速率回落到基线以上 onset_rise_fraction 比例以内处为放热起始点"""
        fraction = float(self.config.get('onset_rise_fraction', 0.1))
        fraction = min(max(fraction, 0.02), 0.5)
        level = baseline_rate + fraction * (peak_rate - baseline_rate)
        i = peak_idx
        while i > 0 and rate_smooth[i] > level:
            i -= 1
        if i <= 0 or i >= peak_idx:
            return None
        return i

    def _refine_peak(self, rate, rate_smooth, onset_idx, peak_idx):
        """按放热宽度加大速率平滑后重新定位峰顶（放热慢时速率峰平坦，argmax 受噪声左右）"""
        width = peak_idx - onset_idx
        base_sigma = max(0.0, float(self.config.get('rate_smooth_sigma', 2.0)))
        sigma = width / 8.0
        if sigma <= max(base_sigma * 1.5, 1.0):
            return peak_idx
        try:
            heavy = gaussian_filter1d(rate, sigma=sigma)
        except Exception as e:
            self.logger.debug(f"峰顶重定位平滑失败: {e}")
            return peak_idx
        n = len(rate_smooth)
        edge = max(3, int(self.config['smooth_window']) // 2)
        lo = onset_idx
        hi = min(n - edge, peak_idx + width + 1)
        if hi - lo < 3:
            return peak_idx
        return lo + int(np.argmax(heavy[lo:hi]))

    def _refine_onset(self, time_array, temp_smooth, onset_idx, peak_idx):
        """
        起始点精判：以起始点之前的数据拟合基线，取温度持续高于基线外推 onset_residual_sigma 倍
        残差标准差的第一个点作为新的起始点，迭代收敛。速率判据在放热较慢时会停在噪声造成的
        第一个速率回落处（明显偏晚），温度偏离基线的累积效应对此更敏感。
        """
        sigma_mult = float(self.config.get('onset_residual_sigma', 3.0))
        if sigma_mult <= 0:
            return onset_idx
        run_length = max(3, int(self.config['smooth_window']))
        for _ in range(3):
            baseline_end = self._baseline_end_index(onset_idx, peak_idx)
            fit = self._fit_baseline(
                time_array, temp_smooth, baseline_end, width=peak_idx - onset_idx, quiet=True
            )
            if fit is None:
                return onset_idx
            k1, b1, _, baseline_start, baseline_end = fit
            residual = temp_smooth - (k1 * time_array + b1)
            base_resid = residual[baseline_start:baseline_end]
            noise = 1.4826 * float(np.median(np.abs(base_resid - np.median(base_resid))))
            noise = max(noise, float(np.std(base_resid)) * 0.5, 1e-3)
            threshold = sigma_mult * noise

            above = residual[baseline_end:peak_idx + 1] > threshold
            new_onset = None
            count = 0
            for offset, flag in enumerate(above):
                count = count + 1 if flag else 0
                if count >= run_length:
                    new_onset = baseline_end + offset - run_length + 1
                    break
            if new_onset is None or new_onset >= onset_idx:
                break
            onset_idx = new_onset
        return onset_idx

    def _baseline_end_index(self, onset_idx, peak_idx):
        """基线拟合窗口终点：起始点减去平滑余量，再按放热宽度前移一段"""
        margin = max(1, int(self.config['smooth_window']) // 2)
        guard_fraction = max(0.0, float(self.config.get('onset_guard_fraction', 0.15)))
        guard = int(guard_fraction * max(0, peak_idx - onset_idx))
        baseline_end = onset_idx - margin - guard
        # 至少保留 10 个点用于基线拟合；不够时逐步放弃前移量
        return max(min(onset_idx - margin, 10), baseline_end)

    def _inflection_is_significant(self, accel, onset_idx, inflection_idx):
        """拐点处加速度须显著高于基线段加速度的波动"""
        baseline_accel = accel[:onset_idx]
        if len(baseline_accel) < 10:
            return True  # 基线太短无法统计，交给后续拟合质量把关
        threshold = float(np.mean(baseline_accel)) + float(self.config['inflection_threshold']) * float(np.std(baseline_accel))
        return accel[inflection_idx] > threshold

    # ------------------------------------------------------------------ 拟合
    def _fit_baseline(self, time_array, temp_smooth, baseline_end, width=0, quiet=False):
        """
        基线拟合：在起始点之前尝试多个区间长度，取斜率标准误最小者。
        - 区间基准长度取 baseline_points 与放热宽度×baseline_width_fraction 的较大者：
          放热越慢，交点距基线段越远，需要更长的基线抑制斜率噪声；
        - 不用 R² 选区间：升温缓慢时短区间的 R² 会被噪声"碰巧"抬高，选出斜率错误的窗口。
        """
        try:
            baseline_points = int(self.config['baseline_points'])
            width_fraction = max(0.0, float(self.config.get('baseline_width_fraction', 0.5)))
            base_points = max(baseline_points, int(width_fraction * max(0, width)))
            best_result, best_err, best_r2 = None, float('inf'), -1.0
            for ratio in (1.5, 1.2, 1.0, 0.8, 0.6):
                points = min(int(base_points * ratio), baseline_end)
                baseline_start = max(0, baseline_end - points)
                if baseline_end - baseline_start < 10:
                    continue
                k, b, r, _, stderr = linregress(
                    time_array[baseline_start:baseline_end],
                    temp_smooth[baseline_start:baseline_end],
                )
                if stderr < best_err:
                    best_err = stderr
                    best_r2 = r ** 2
                    best_result = (k, b, r, baseline_start, baseline_end)
            if best_result is None:
                return None
            if not quiet and best_r2 < float(self.config.get('baseline_r2_threshold', 0.95)):
                self.logger.debug(f"基线拟合质量较低: R²={best_r2:.3f}")
            return best_result
        except Exception as e:
            self.logger.error(f"基线拟合失败: {e}")
            return None

    def _fit_peak(self, time_array, temp_smooth, onset_idx, peak_idx, k1):
        """
        峰顶拟合：以峰顶为中心尝试多个窗口宽度，取 R² 最高且斜率显著大于基线者。
        窗口下限随放热宽度(起始点→峰顶)放大，放热慢时避免在几个点上拟合出噪声斜率。
        """
        try:
            n = len(temp_smooth)
            peak_points = max(4, int(self.config['peak_points']))
            min_slope_ratio = float(self.config.get('peak_slope_ratio_min', 1.2))
            width_fraction = max(0.0, float(self.config.get('peak_window_fraction', 0.1)))
            min_half = int(width_fraction * max(0, peak_idx - onset_idx))
            best_result, best_r2 = None, -1.0
            for mult in (1.0, 0.7, 1.5, 2.0):
                half = max(2, int(round(peak_points * mult / 2)), min_half)
                peak_start = max(onset_idx, peak_idx - half)
                peak_end = min(n, peak_idx + half + 1)
                if peak_end - peak_start < 5:
                    continue
                k, b, r, _, _ = linregress(
                    time_array[peak_start:peak_end],
                    temp_smooth[peak_start:peak_end],
                )
                if k <= k1 * min_slope_ratio:
                    continue
                if r ** 2 > best_r2:
                    best_r2 = r ** 2
                    best_result = (k, b, r, peak_start, peak_end)
            if best_result is None:
                self.logger.debug("未找到斜率显著大于基线的峰顶拟合区间")
            return best_result
        except Exception as e:
            self.logger.error(f"峰顶拟合失败: {e}")
            return None

    # ------------------------------------------------------------------ 校验/评分
    def _validate_ignition_point(self, ignition_time, ignition_temp, time_array, temp_smooth,
                                 baseline_start, peak_idx):
        """交点必须位于基线区间起点与峰顶之间，温度在数据范围内"""
        if not np.isfinite(ignition_time) or not np.isfinite(ignition_temp):
            self.logger.warning("切线交点不是有限数值")
            return False
        if ignition_time < time_array[baseline_start] or ignition_time > time_array[peak_idx]:
            self.logger.warning(
                f"切线交点不在基线区间与峰顶之间: {ignition_time:.1f}s "
                f"不在[{time_array[baseline_start]:.1f}, {time_array[peak_idx]:.1f}]内"
            )
            return False
        temp_min, temp_max = float(np.min(temp_smooth)), float(np.max(temp_smooth))
        if ignition_temp < temp_min or ignition_temp > temp_max:
            self.logger.warning(
                f"着火温度超出数据范围: {ignition_temp:.1f}°C 不在[{temp_min:.1f}, {temp_max:.1f}]内"
            )
            return False
        return True

    @staticmethod
    def _clamp01(value):
        try:
            return float(min(1.0, max(0.0, value)))
        except (TypeError, ValueError):
            return 0.0

    def _calculate_confidence(self, r1, r2, k1, k2, method_scores, baseline_length):
        """综合置信度：拟合质量(30%) + 斜率差异(40%) + 峰形质量(20%) + 基线覆盖(10%)"""
        fit_score = min(1.0, (abs(r1) + abs(r2)) / 2)

        if k2 > k1 and k1 > 0:
            slope_ratio = k2 / k1
            if slope_ratio >= 3.0:
                slope_score = 0.95 + 0.05 * min(1.0, (slope_ratio - 3.0) / 2.0)
            elif slope_ratio >= 2.0:
                slope_score = 0.85 + 0.10 * (slope_ratio - 2.0)
            elif slope_ratio >= 1.5:
                slope_score = 0.75 + 0.10 * ((slope_ratio - 1.5) / 0.5)
            elif slope_ratio >= 1.2:
                slope_score = 0.65 + 0.10 * ((slope_ratio - 1.2) / 0.3)
            else:
                slope_score = 0.5 + 0.15 * ((slope_ratio - 1.0) / 0.2)
            slope_score = min(1.0, max(0.5, slope_score))
        elif k2 > k1:
            slope_score = 0.8
        else:
            slope_score = 0.3

        shape_score = float(np.mean(list(method_scores.values()))) if method_scores else 0.5
        coverage_score = min(1.0, baseline_length / 100.0)

        return 0.30 * fit_score + 0.40 * slope_score + 0.20 * shape_score + 0.10 * coverage_score

    def batch_detect(self, time_data_list, temp_data_list):
        """批量检测多个样品的着火点"""
        results = []
        for i, (time_data, temp_data) in enumerate(zip(time_data_list, temp_data_list)):
            self.logger.info(f"正在检测第 {i + 1} 个样品...")
            results.append(self.detect_ignition(time_data, temp_data))
        return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 模拟煤粉着火数据: 5°C/min 线性升温 + 300s 处开始的放热峰
    t = np.arange(0, 700, 0.5)
    base = 200 + (5.0 / 60.0) * t
    x = np.clip((t - 300.0) / (np.sqrt(2) * 40.0), 0, None)
    temp = base + 150.0 * (1 - np.exp(-x ** 2)) + np.random.normal(0, 0.3, len(t))

    detector = TangentMethodDetector()
    result = detector.detect_ignition(t, temp)
    if result:
        print("\n" + "=" * 60)
        print(f"  着火点温度: {result['ignition_temp']:.1f}°C")
        print(f"  着火点时刻: {result['ignition_time']:.1f}秒")
        print(f"  置信度: {result['confidence']:.3f}")
        print(f"  基线拟合: y = {result['baseline_fit'][0]:.4f}x + {result['baseline_fit'][1]:.2f}")
        print(f"  峰顶拟合: y = {result['peak_fit'][0]:.4f}x + {result['peak_fit'][1]:.2f}")
        print(f"  斜率比: {result['peak_fit'][0] / result['baseline_fit'][0]:.2f}")
        print("=" * 60)
    else:
        print("检测失败")
