import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openphysicalai import Budget, evaluate_budget, wilson_interval  # noqa: E402


def test_missing_measurement_fails():
    r = evaluate_budget(Budget(), {"vram_process_peak_gb": 1.0})
    assert not r.passed
    assert any(c.note == "not measured" for c in r.checks)


def test_pass_and_fail():
    ok = {"vram_process_peak_gb": 2, "vram_device_peak_gb": 3, "ram_process_peak_gb": 4, "ram_system_peak_gb": 10, "planning_ms_p95": 2000}
    assert evaluate_budget(Budget(), ok).passed
    bad = dict(ok, vram_process_peak_gb=3.5)
    assert not evaluate_budget(Budget(), bad).passed


def test_wilson():
    lo, hi = wilson_interval(50, 100)
    assert 0.39 < lo < 0.41 and 0.59 < hi < 0.61
    assert wilson_interval(0, 0) == (0.0, 0.0)
