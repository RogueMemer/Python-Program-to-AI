import random
import math

def generate_random_two_digit_list(n=1000):
    """
    Generate a list of random numbers with two digits.
    """
    """
    all errors were fixed with the help of AI
    """
    return [random.randint(10, 99) for _ in range(n)]
def calculate_leading_digit_frequency(numbers):
    """
    Calculates the frequency of the digits from 1 to 9 in this list
    """
    freq = {i: 0 for i in range(1, 10)}
    for num in numbers:
        leading_digit = int(str(num)[0])
        if leading_digit in freq:
            freq[leading_digit] += 1
    return freq
def convert_frequency_to_percentage(freq_dict):
    """
    Converts the frequency to the precentage of the number
    """
    total = sum(freq_dict.values())
    return {digit: round((count / total) * 100, 4) for digit, count in freq_dict.items()}
def benford_distribution():
    """
    runs the nefarious benford for digits 1 to 9
    """
    return {d: round(math.log10(1 + 1/d) * 100, 4) for d in range(1, 10)}
def print_side_by_side(benford, actual):
    """
    Prints the titles side by side
    """
    print("\nDigit | Benford % | Actual %")
    print("-----------------------------")
    for d in range(1, 10):
        print(f"{d}     | {benford[d]:>8} | {actual[d]:>8}")
        
numbers = generate_random_two_digit_list(1500)
print("Generated random list of two-digit numbers (first 20 shown):")
print(numbers[:20])

freq = calculate_leading_digit_frequency(numbers)
print("\nLeading digit frequency:")
print(freq)

actual_percent = convert_frequency_to_percentage(freq)
print("\nActual distribution percentages:")
print(actual_percent)

benford_percent = benford_distribution()
print("\nBenford distribution percentages:")
print(benford_percent)

print_side_by_side(benford_percent, actual_percent)





