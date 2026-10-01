import pandas as pd
import numpy as np
import math

# ---------------------------------------------------------
# 1. LOAD CSV
# ---------------------------------------------------------

df = pd.read_csv("ohio.csv")   # <-- replace with your file if needed
column_name = "population"     # <-- change to any numeric column
data = df[column_name].dropna()


# ---------------------------------------------------------
# 2. LEADING DIGIT FREQUENCY
# ---------------------------------------------------------

def leading_digit_frequency(series):
    """
    Extracts the leading digit (1–9) from a pandas Series of numbers
    and returns a dictionary of frequencies.
    """
    digits = series.astype(str).str.strip().str[0]
    digits = digits[digits.isin(list("123456789"))]
    freq = digits.value_counts().sort_index()
    return freq.to_dict()


# ---------------------------------------------------------
# 3. BENFORD DISTRIBUTION USING NUMPY
# ---------------------------------------------------------

def benford_numpy():
    """
    Generates Benford distribution using NumPy for digits 1–9.
    Returns a dictionary mapping digit → percentage.
    """
    digits = np.arange(1, 10)
    benford = np.log10(1 + 1/digits) * 100
    return {d: round(b, 4) for d, b in zip(digits, benford)}


# ---------------------------------------------------------
# 4. CONVERT FREQUENCY TO PERCENTAGES
# ---------------------------------------------------------

def frequency_to_percent(freq_dict):
    """
    Converts frequency dictionary to percentage distribution.
    """
    total = sum(freq_dict.values())
    return {d: round((freq_dict[d] / total) * 100, 4) for d in freq_dict}


# ---------------------------------------------------------
# 5. MAD STATISTIC (Amiram et al. 2015)
# ---------------------------------------------------------

def mad_statistic(actual, benford):
    """
    Computes the Mean Absolute Deviation (MAD) between actual and Benford distributions.
    """
    diffs = [abs(actual[d] - benford[d]) for d in range(1, 10)]
    return round(sum(diffs) / 9, 6)


# ---------------------------------------------------------
# 6. KS STATISTIC (Manual, No SciPy)
# ---------------------------------------------------------

def ks_statistic(actual, benford):
    """
    Computes the Kolmogorov–Smirnov (KS) statistic using cumulative distributions.
    """
    actual_cum = []
    benford_cum = []
    
    a_sum = 0
    b_sum = 0
    
    for d in range(1, 10):
        a_sum += actual[d]
        b_sum += benford[d]
        actual_cum.append(a_sum)
        benford_cum.append(b_sum)
    
    diffs = [abs(a - b) for a, b in zip(actual_cum, benford_cum)]
    return round(max(diffs), 6)


# ---------------------------------------------------------
# 7. RUN ANALYSIS
# ---------------------------------------------------------

freq = leading_digit_frequency(data)
actual_percent = frequency_to_percent(freq)
benford_percent = benford_numpy()

print("Digit | Actual % | Benford %")
print("--------------------------------")
for d in range(1, 10):
    print(f"{d}     | {actual_percent[d]:>8} | {benford_percent[d]:>8}")

# ---------------------------------------------------------
# 8. STATISTICS
# ---------------------------------------------------------

mad = mad_statistic(actual_percent, benford_percent)
ks = ks_statistic(actual_percent, benford_percent)

print("\nMAD Statistic:", mad)
print("KS Statistic:", ks)

