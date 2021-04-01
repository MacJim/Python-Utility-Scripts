"""
https://docs.python.org/3/library/os.html#os.walk
"""

import os
import argparse


def list_files(start_path: str):
    for root_path, dir_names, filenames in os.walk(start_path):
        level = root_path.replace(start_path, "").count(os.sep)
        indent = ' ' * 2 * (level)
        print(f"{indent}{os.path.basename(root_path)}/")

        # Sort the dir names here to modify sub-directory walking order.
        # This feature is documented.
        dir_names.sort()

        filenames.sort()
        sub_indent = " " * 2 * (level + 1)
        for f in filenames:
            print(f"{sub_indent}{f}")


# MARK: Main
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("dir_name", nargs="?", default=os.getcwd())
    args = parser.parse_args()

    # print(f"Working directory: {args.dir_name}")    # No need to print it since the dir name is always printed by `list_files` in the first place.
    list_files(args.dir_name)
