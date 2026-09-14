"""
放热峰切线法检测器回归测试

用合成曲线（线性升温 + 指数型放热峰）验证：
- 快/慢放热峰的着火温度都接近解析切线交点
- 纯升温曲线不得"检出"着火点
- configs/experiment_config.yaml 中的参数档能正常工作
"""

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from utils.tangent_method_detector import TangentMethodDetector

RAMP = 5.0 / 60.0  # 5 °C/min 线性升温
DT = 0.5


def make_curve(time_to_peak, amplitude=150.0, t0=300.0, t_end=700.0, noise=0.3, seed=0):
    """返回 (t, clean, noisy)：基线 200°C + RAMP·t，t0 起叠加 amplitude·(1-exp(-x²)) 型放热"""
    t = np.arange(0.0, t_end, DT)
    base = 200.0 + RAMP * t
    tau = np.sqrt(2.0) * time_to_peak  # 1-exp(-x²) 的最大斜率出现在 x=1/√2
    x = np.clip((t - t0) / tau, 0, None)
    clean = base + amplitude * (1.0 - np.exp(-x ** 2))
    noisy = clean + np.random.default_rng(seed).normal(0, noise, len(t))
    return t, clean, noisy


def analytic_tangent(t, clean):
    """解析参考：基线直线与干净曲线最大斜率点切线的交点温度"""
    rate = np.gradient(clean, t)
    p = int(np.argmax(rate))
    k2 = rate[p]
    b2 = clean[p] - k2 * t[p]
    k1, b1 = RAMP, 200.0
    t_ig = (b2 - b1) / (k1 - k2)
    return k1 * t_ig + b1, t_ig


def pure_ramp(seed=1, noise=0.3):
    t = np.arange(0.0, 700.0, DT)
    return t, 200.0 + RAMP * t + np.random.default_rng(seed).normal(0, noise, len(t))


@pytest.fixture(scope="module")
def yaml_config():
    config_path = Path(__file__).resolve().parents[1] / "configs" / "experiment_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["ignition_experiment"]["ignition_detection"]["tangent_method"]


RESULT_KEYS = {
    "ignition_temp", "ignition_time", "baseline_fit", "peak_fit", "confidence",
    "inflection_idx", "onset_idx", "peak_idx", "baseline_range", "peak_range",
    "method_scores", "r1", "r2",
}


@pytest.mark.parametrize("time_to_peak", [10, 30, 60, 120, 180])
def test_ignition_temperature_matches_analytic_tangent(time_to_peak):
    detector = TangentMethodDetector()
    for seed in range(3):
        t, clean, noisy = make_curve(time_to_peak, seed=seed)
        temp_ref, time_ref = analytic_tangent(t, clean)

        result = detector.detect_ignition(t, noisy)

        assert result is not None, f"ttp={time_to_peak}s seed={seed} 未检出"
        assert abs(result["ignition_temp"] - temp_ref) < 1.5, (
            f"ttp={time_to_peak}s seed={seed}: {result['ignition_temp']:.1f} vs {temp_ref:.1f}"
        )
        assert abs(result["ignition_time"] - time_ref) < 10.0


def test_result_structure_and_ordering():
    t, _, noisy = make_curve(40)
    result = TangentMethodDetector().detect_ignition(t, noisy)

    assert result is not None
    assert RESULT_KEYS <= set(result)
    # 结果需可直接序列化写入数据库
    json.dumps(result)

    baseline_start, baseline_end = result["baseline_range"]
    peak_start, peak_end = result["peak_range"]
    assert 0 <= baseline_start < baseline_end <= result["onset_idx"]
    assert result["onset_idx"] <= result["inflection_idx"] <= result["peak_idx"]
    assert peak_start <= result["peak_idx"] < peak_end
    # 峰顶切线斜率显著大于基线斜率
    assert result["peak_fit"][0] > result["baseline_fit"][0] * 1.2
    # 交点位于基线段起点与峰顶之间
    assert t[baseline_start] <= result["ignition_time"] <= t[result["peak_idx"]]
    assert 0.0 <= result["confidence"] <= 1.0


def test_yaml_profile_detects_slow_exotherm(yaml_config):
    detector = TangentMethodDetector(yaml_config)
    t, clean, noisy = make_curve(120, seed=2)
    temp_ref, _ = analytic_tangent(t, clean)

    result = detector.detect_ignition(t, noisy)

    assert result is not None
    assert abs(result["ignition_temp"] - temp_ref) < 1.5


@pytest.mark.parametrize("config_name", ["default", "yaml"])
def test_pure_ramp_is_not_detected(config_name, yaml_config):
    detector = TangentMethodDetector(None if config_name == "default" else yaml_config)
    for seed in range(3):
        t, temp = pure_ramp(seed=seed)
        assert detector.detect_ignition(t, temp) is None


def test_weak_slow_exotherm_still_detected():
    """幅值仅 30°C、峰宽 2 分钟：速率峰不高于噪声尖峰太多，需要多尺度峰顶搜索"""
    detector = TangentMethodDetector()
    t, clean, noisy = make_curve(120, amplitude=30.0, seed=0)
    temp_ref, _ = analytic_tangent(t, clean)

    result = detector.detect_ignition(t, noisy)

    assert result is not None
    assert abs(result["ignition_temp"] - temp_ref) < 2.0


def test_invalid_inputs_return_none():
    detector = TangentMethodDetector()
    t, _, noisy = make_curve(30)

    assert detector.detect_ignition(t[:20], noisy[:20]) is None  # 数据点太少
    assert detector.detect_ignition(t, noisy[:-1]) is None  # 长度不一致
    bad = noisy.copy()
    bad[10] = np.nan
    assert detector.detect_ignition(t, bad) is None
    assert detector.detect_ignition(t, np.full_like(t, 200.0)) is None  # 温升不足


def test_batch_detect_returns_one_result_per_sample():
    detector = TangentMethodDetector()
    t, _, exo = make_curve(30)
    t_ramp, ramp = pure_ramp()

    results = detector.batch_detect([t, t_ramp], [exo, ramp])

    assert len(results) == 2
    assert results[0] is not None
    assert results[1] is None
