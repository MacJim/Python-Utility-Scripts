"""
Square brackets <==> Curly brackets.
"""


import argparse
import typing

import clipboard


def convert_brackets(s: str) -> str:
    # MARK: Verify that `s` is valid
    left_square_brackets_count = 0
    right_square_brackets_count = 0
    right_curly_brackets_count = 0
    left_curly_brackets_count = 0

    for i, c in enumerate(s):
        if c == '[':
            left_square_brackets_count += 1
        elif c == ']':
            right_square_brackets_count += 1
            if right_square_brackets_count > left_square_brackets_count:
                # Error case 1: More right brackets than left brackets.
                raise ValueError(f"More right square brackets than left brackets at index {i}.")

        elif c == '{':
            left_curly_brackets_count += 1
        elif c == '}':
            right_curly_brackets_count += 1
            if right_curly_brackets_count > left_curly_brackets_count:
                # Error case 1: More right brackets than left brackets.
                raise ValueError(f"More right curly brackets than left brackets at index {i}.")

    # Error case 2: Both square and curly brackets.
    square_brackets_found = (left_square_brackets_count > 0) or (right_square_brackets_count > 0)
    curly_brackets_found = (left_curly_brackets_count > 0) or (right_curly_brackets_count > 0)
    if square_brackets_found and curly_brackets_found:
        raise ValueError(f"\nBoth square and curly brackets found: ({left_square_brackets_count}, {right_square_brackets_count}, {left_curly_brackets_count}, {right_curly_brackets_count})")

    # Error case 3: Unbalanced brackets count.
    if square_brackets_found:
        if left_square_brackets_count != right_square_brackets_count:
            raise ValueError(f"\nUnbalanced square brackets: ({left_square_brackets_count}, {right_square_brackets_count})")

    if curly_brackets_found:
        if left_curly_brackets_count != right_curly_brackets_count:
            raise ValueError(f"\nUnbalanced curly brackets: ({left_curly_brackets_count}, {right_curly_brackets_count})")

    # MARK: Change brackets
    solution = s

    if square_brackets_found:
        solution = s.replace('[', '{')
        solution = solution.replace(']', '}')

    if curly_brackets_found:
        solution = s.replace('{', '[')
        solution = solution.replace('}', ']')

    return solution


def main(input_filename: typing.Optional[str], copy_to_clipboard: bool):
    print("Square brackets <==> Curly brackets")

    if input_filename:
        # Load from file.
        print(f"Loading input from file `{input_filename}`...")
        with open(input_filename, "r") as f:
            s = f.read()

        if not s:
            print("Failed.")
            exit(1)

        try:
            solution = convert_brackets(s)

            print(solution)
            if copy_to_clipboard:
                clipboard.write(solution)

        except ValueError as e:
            print(e)

    else:
        # Interactive mode.
        print("Empty input or control-C to exit.")

        while True:
            print()
            s = input("Input: ")

            if not s:
                # Empty input to exit.
                exit(0)

            try:
                solution = convert_brackets(s)

                print(solution)
                if copy_to_clipboard:
                    clipboard.write(solution)

            except ValueError as e:
                print(e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_filename", "-f", type=str, default=None)
    parser.add_argument("--copy_to_clipboard", "-c", action="store_true")
    args = parser.parse_args()

    main(args.input_filename, args.copy_to_clipboard)
