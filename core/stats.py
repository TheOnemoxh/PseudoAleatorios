"""
Statistical Analysis and Independence Testing for PRNG Sequences
Implements:
- Basic statistics (Mean, Variance, Min, Max)
- Lag-1 Scatter Plot Pairs (R_i vs R_{i+1}) for visual independence
- Autocorrelation Coefficient (Lag-1)
"""

import math
from typing import List, Dict, Any


def calculate_stats(numbers: List[float]) -> Dict[str, Any]:
    n = len(numbers)
    if n == 0:
        return {
            "count": 0,
            "mean": 0.0,
            "expected_mean": 0.5,
            "variance": 0.0,
            "expected_variance": round(1 / 12, 6),
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "autocorrelation_lag1": 0.0,
            "lag1_pairs": []
        }

    mean = sum(numbers) / n
    expected_mean = 0.5
    expected_variance = 1.0 / 12.0

    if n > 1:
        variance = sum((x - mean) ** 2 for x in numbers) / (n - 1)
    else:
        variance = 0.0
    std_dev = math.sqrt(variance)

    min_val = min(numbers)
    max_val = max(numbers)

    # Lag-1 Pairs for Independence Scatter Plot
    lag1_pairs = []
    for i in range(n - 1):
        lag1_pairs.append({
            "x": round(numbers[i], 6),
            "y": round(numbers[i + 1], 6),
            "index": i + 1
        })

    # Autocorrelation Lag-1
    if n > 2 and variance > 1e-12:
        numerator = sum((numbers[i] - mean) * (numbers[i + 1] - mean) for i in range(n - 1))
        denominator = sum((numbers[i] - mean) ** 2 for i in range(n))
        autocorr_lag1 = numerator / denominator if denominator != 0 else 0.0
    else:
        autocorr_lag1 = 0.0

    return {
        "count": n,
        "mean": round(mean, 6),
        "expected_mean": expected_mean,
        "mean_diff": round(abs(mean - expected_mean), 6),
        "variance": round(variance, 6),
        "expected_variance": round(expected_variance, 6),
        "std_dev": round(std_dev, 6),
        "min": round(min_val, 6),
        "max": round(max_val, 6),
        "autocorrelation_lag1": round(autocorr_lag1, 4),
        "lag1_pairs": lag1_pairs
    }
