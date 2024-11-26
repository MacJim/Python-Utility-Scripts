"""
Given an int, print the set bits.
Example: 9 -> 0, 3
"""

import argparse


def main(number: str):
    number = int(number, 0)
    if number < 0:
        raise ValueError("Non-negative numbers only")

    print(f"{number} ({bin(number)})")

    set_bits = [i for i in range(number.bit_length()) if number & (1 << i)]
    print(f"Set bits: {set_bits}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("number", type=str)
    args = parser.parse_args()
    main(args.number)
