"""Leading-digit analysis helpers for financial statement amounts."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


def leading_digit_frequency(values: Iterable[object]) -> dict[int, int]:
    """Count the first non-zero decimal digit for each usable value.

    >>> leading_digit_frequency([-120, 0.0042, 3, None])
    {1: 1, 2: 0, 3: 1, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
    """
    frequencies = {digit: 0 for digit in range(1, 10)}
    for value in values:
        if pd.isna(value):
            continue
        digits = re.sub(r"\D", "", str(value))
        first_nonzero = next((char for char in digits if char != "0"), None)
        if first_nonzero is not None:
            frequencies[int(first_nonzero)] += 1
    return frequencies


def benford_distribution() -> dict[int, float]:
    """Return Benford's expected leading-digit percentages for digits 1-9.

    >>> round(sum(benford_distribution().values()), 4)
    100.0
    """
    digits = np.arange(1, 10)
    percentages = np.log10(1 + 1 / digits) * 100
    return {int(digit): round(float(percent), 4) for digit, percent in zip(digits, percentages)}


def frequency_to_percent(frequencies: Mapping[int, int]) -> dict[int, float]:
    """Convert digit counts to percentages, returning zeroes for empty input.

    >>> frequency_to_percent({1: 1, 2: 3})
    {1: 25.0, 2: 75.0}
    >>> frequency_to_percent({1: 0})
    {1: 0.0}
    """
    total = sum(frequencies.values())
    return {
        digit: round(count / total * 100, 4) if total else 0.0
        for digit, count in frequencies.items()
    }


def mad_statistic(actual: Mapping[int, float], expected: Mapping[int, float]) -> float:
    """Compute mean absolute deviation between percentage distributions.

    >>> mad_statistic({digit: 10 for digit in range(1, 10)}, benford_distribution()) >= 0
    True
    """
    differences = [abs(actual[digit] - expected[digit]) for digit in range(1, 10)]
    return round(float(np.mean(differences)), 6)


def ks_statistic(actual: Mapping[int, float], expected: Mapping[int, float]) -> float:
    """Compute the maximum absolute cumulative percentage difference.

    >>> ks_statistic(benford_distribution(), benford_distribution())
    0.0
    """
    actual_cumulative = np.cumsum([actual[digit] for digit in range(1, 10)])
    expected_cumulative = np.cumsum([expected[digit] for digit in range(1, 10)])
    return round(float(np.max(np.abs(actual_cumulative - expected_cumulative))), 6)


def analyze_benford(values: Iterable[object]) -> tuple[pd.DataFrame, float, float]:
    """Return a digit comparison table, MAD, and KS statistic.

    >>> table, mad, ks = analyze_benford([1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> (len(table), round(float(table["actual_percent"].sum()), 1), mad >= 0, ks >= 0)
    (9, 100.0, True, True)
    """
    actual = frequency_to_percent(leading_digit_frequency(values))
    expected = benford_distribution()
    comparison = pd.DataFrame({
        "digit": range(1, 10),
        "actual_percent": [actual[digit] for digit in range(1, 10)],
        "benford_percent": [expected[digit] for digit in range(1, 10)],
    })
    return comparison, mad_statistic(actual, expected), ks_statistic(actual, expected)