"""
Square brackets <==> Curly brackets.
"""


import argparse

import clipboard


def main(copy_to_clipboard: bool):
    print("Square brackets <==> Curly brackets")
    print("Empty input or control-C to exit.")

    while True:
        print()
        s = input("Input: ")

        if not s:
            # Empty input to exit.
            exit(0)

        left_square_brackets_count = 0
        right_square_brackets_count = 0
        right_curly_brackets_count = 0
        left_curly_brackets_count = 0

        for c in s:
            if c == '[':
                left_square_brackets_count += 1
            elif c == ']':
                right_square_brackets_count += 1
            elif c == '{':
                left_curly_brackets_count += 1
            elif c == '}':
                right_curly_brackets_count += 1

        # Error case 1: Both square and curly brackets.
        square_brackets_found = (left_square_brackets_count > 0) or (right_square_brackets_count > 0)
        curly_brackets_found = (left_curly_brackets_count > 0) or (right_curly_brackets_count > 0)
        if square_brackets_found and curly_brackets_found:
            print(f"\nBoth square and curly brackets found: ({left_square_brackets_count}, {right_square_brackets_count}, {left_curly_brackets_count}, {right_curly_brackets_count})")
            continue

        # Error case 2: Unbalanced brackets count.
        if square_brackets_found:
            if left_square_brackets_count != right_square_brackets_count:
                print(f"\nUnbalanced square brackets: ({left_square_brackets_count}, {right_square_brackets_count})")
                continue

        if curly_brackets_found:
            if left_curly_brackets_count != right_curly_brackets_count:
                print(f"\nUnbalanced curly brackets: ({left_curly_brackets_count}, {right_curly_brackets_count})")
                continue

        # Solution
        solution = s

        if square_brackets_found:
            solution = s.replace('[', '{')
            solution = solution.replace(']', '}')

        if curly_brackets_found:
            solution = s.replace('{', '[')
            solution = solution.replace('}', ']')

        print(solution)
        if copy_to_clipboard:
            clipboard.write(solution)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--copy_to_clipboard", "-c", action="store_true")
    args = parser.parse_args()

    main(args.copy_to_clipboard)
