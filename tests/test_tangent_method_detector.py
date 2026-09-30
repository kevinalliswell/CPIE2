"""Numerical regression cases, not reference samples or standards certification."""
import json

import numpy as np
import pytest

from src.utils.tangent_method_detector import TangentMethodDetector


def exotherm(width=40.0, step=0.5, noise=0.0):
    time = np.arange(0.0, 1200.0, step)
    onset, amplitude, baseline_rate = 400.0, 150.0, 5.0 / 60.0
    rise = np.maximum(time - onset, 0.0)
    temperature = 200.0 + baseline_rate * time
    temperature += amplitude * (1.0 - np.exp(-rise ** 2 / (2.0 * width ** 2)))
    temperature += np.random.default_rng(2).normal(0.0, noise, len(time))
    # For this analytic curve the rate peaks at onset + width. The tangent at
    # that point intersects the exact baseline at the following time.
    intersection = onset + width * (2.0 - np.exp(0.5))
    return time, temperature, intersection


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_noisy_linear_heating_is_not_an_exotherm(seed):
    time = np.arange(0.0, 1200.0, 0.5)
    temperature = 200.0 + time / 12.0
    temperature += np.random.default_rng(seed).normal(0.0, 0.3, len(time))
    assert TangentMethodDetector().detect_ignition(time, temperature) is None


@pytest.mark.parametrize("width", [10.0, 40.0, 100.0])
@pytest.mark.parametrize("noise", [0.0, 0.3])
def test_exotherm_tangents_track_analytic_intersection(width, noise):
    time, temperature, expected = exotherm(width=width, noise=noise)
    result = TangentMethodDetector().detect_ignition(time, temperature)
    assert result is not None
    assert result["ignition_time"] == pytest.approx(expected, abs=4.0)
    assert result["ignition_temp"] == pytest.approx(200.0 + expected / 12.0, abs=0.6)
    assert time[result["peak_idx"]] == pytest.approx(400.0 + width, abs=6.0)
    assert result["peak_range"][0] <= result["peak_idx"] < result["peak_range"][1]


def test_result_has_only_json_serializable_finite_values():
    time, temperature, _ = exotherm(width=10.0)
    result = TangentMethodDetector().detect_ignition(time, temperature)
    assert result is not None
    restored = json.loads(json.dumps(result, allow_nan=False))
    assert isinstance(restored["peak_idx"], int)
    assert 0.0 <= restored["confidence"] <= 1.0


@pytest.mark.parametrize("bad_time", ["nan", "inf", "duplicate", "reverse", "constant", "matrix"])
def test_invalid_time_axis_is_rejected(bad_time):
    time, temperature, _ = exotherm(width=10.0)
    if bad_time == "nan":
        time[100] = np.nan
    elif bad_time == "inf":
        time[-1] = np.inf
    elif bad_time == "duplicate":
        time[100] = time[99]
    elif bad_time == "reverse":
        time[100] = time[99] - 1.0
    elif bad_time == "constant":
        time[:] = 0.0
    else:
        time = time.reshape(-1, 1)
    assert TangentMethodDetector().detect_ignition(time, temperature) is None


@pytest.mark.parametrize("count", [0, 1, 2, 10, 49])
def test_insufficient_samples_are_rejected(count):
    assert TangentMethodDetector().detect_ignition(np.arange(count), np.arange(count) + 200) is None


@pytest.mark.parametrize("bad_temperature", [None, "invalid", np.nan, np.inf, -np.inf])
def test_invalid_temperature_is_rejected(bad_temperature):
    time, temperature, _ = exotherm(width=10.0)
    temperature = list(temperature)
    temperature[100] = bad_temperature
    assert TangentMethodDetector().detect_ignition(time, temperature) is None


def test_mismatched_shapes_are_rejected():
    time, temperature, _ = exotherm(width=10.0)
    assert TangentMethodDetector().detect_ignition(time[:-1], temperature) is None
    assert TangentMethodDetector().detect_ignition(time, temperature.reshape(-1, 1)) is None


def test_monotonic_irregular_sampling_remains_supported():
    uniform_time, uniform_temperature, expected = exotherm()
    indices = np.delete(np.arange(len(uniform_time)), np.arange(20, len(uniform_time), 9))
    result = TangentMethodDetector().detect_ignition(uniform_time[indices], uniform_temperature[indices])
    assert result is not None
    assert result["ignition_time"] == pytest.approx(expected, abs=4.0)
