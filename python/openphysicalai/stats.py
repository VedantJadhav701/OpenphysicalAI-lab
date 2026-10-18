"""Statistics helpers: Wilson score interval, McNemar paired test, paired bootstrap."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple
import numpy as np


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_test(y_a: List[bool], y_b: List[bool]) -> Dict:
    """Paired McNemar test for two binary classifiers or policies evaluated on identical seeds.
    y_a: baseline outcomes (True for success, False for failure)
    y_b: treatment outcomes (True for success, False for failure)
    """
    if len(y_a) != len(y_b):
        raise ValueError(f"Lengths must match: len(y_a)={len(y_a)} vs len(y_b)={len(y_b)}")
    n = len(y_a)
    if n == 0:
        return {"n": 0, "b": 0, "c": 0, "p_value": 1.0, "statistic": 0.0, "significant_05": False}

    b = sum(1 for a, b_val in zip(y_a, y_b) if not a and b_val)
    c = sum(1 for a, b_val in zip(y_a, y_b) if a and not b_val)
    disc = b + c

    if disc == 0:
        return {"n": n, "b": 0, "c": 0, "discordant_pairs": 0, "p_value": 1.0, "statistic": 0.0, "significant_05": False, "method": "exact"}

    if disc < 25:
        k = min(b, c)
        p_val = 2.0 * sum(math.comb(disc, i) * (0.5 ** disc) for i in range(k + 1))
        p_val = min(1.0, p_val)
        return {
            "n": n,
            "b": b,
            "c": c,
            "discordant_pairs": disc,
            "statistic": float(k),
            "p_value": round(p_val, 5),
            "significant_05": p_val < 0.05,
            "method": "exact_binomial",
        }
    else:
        stat = ((abs(b - c) - 1.0) ** 2) / disc
        p_val = math.erfc(math.sqrt(stat / 2.0))
        return {
            "n": n,
            "b": b,
            "c": c,
            "discordant_pairs": disc,
            "statistic": round(stat, 4),
            "p_value": round(p_val, 5),
            "significant_05": p_val < 0.05,
            "method": "continuity_corrected_chi2",
        }


def paired_bootstrap_difference(
    y_a: List[bool],
    y_b: List[bool],
    n_resamples: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict:
    """Bootstrap confidence interval for paired difference in success rate: mean(y_b) - mean(y_a)."""
    if len(y_a) != len(y_b):
        raise ValueError("Lengths must match for paired bootstrap")
    n = len(y_a)
    if n == 0:
        return {"diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "significant": False}

    arr_a = np.array(y_a, dtype=float)
    arr_b = np.array(y_b, dtype=float)
    diff = float(np.mean(arr_b) - np.mean(arr_a))

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    sample_diffs = np.mean(arr_b[indices] - arr_a[indices], axis=1)

    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)
    ci_low = float(np.percentile(sample_diffs, low_pct))
    ci_high = float(np.percentile(sample_diffs, high_pct))

    significant = (ci_low > 0) or (ci_high < 0)
    return {
        "diff": round(diff, 4),
        "ci_lower": round(ci_low, 4),
        "ci_upper": round(ci_high, 4),
        "alpha": alpha,
        "n_resamples": n_resamples,
        "significant": significant,
    }
