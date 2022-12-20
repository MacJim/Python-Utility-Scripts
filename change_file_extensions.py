"""
Changes all matching file extensions to another extension.
"""

import argparse
import os


# MARK: - Main
def main(work_dir: str, old_ext: str, new_ext: str):
    print(f"Working directory: {work_dir}")
    print(f"Old extension: {old_ext}")
    print(f"New extension: {new_ext}")

    filenames = os.listdir(work_dir)

    filenames_with_old_ext = [f for f in filenames if f.endswith(old_ext)]
    filenames_with_old_ext.sort()

    filenames_with_new_ext = [f[:-len(old_ext)] + new_ext for f in filenames_with_old_ext]

    for old_filename, new_filename in zip(filenames_with_old_ext, filenames_with_new_ext):
        print(f"{old_filename} -> {new_filename}")

    consent = input("Press ENTER to proceed. Type 'q' and press ENTER to abort.")
    if (consent):
        print("Abort.")
        exit(0)

    print(f"Renaming {len(filenames_with_old_ext)} files.")
    for old_filename, new_filename in zip(filenames_with_old_ext, filenames_with_new_ext):
        old_filename = os.path.join(work_dir, old_filename)
        new_filename = os.path.join(work_dir, new_filename)

        os.rename(old_filename, new_filename)


if (__name__ == "__main__"):
    parser = argparse.ArgumentParser()
    parser.add_argument("--work_dir", "-d", type=str, default=os.getcwd(), help="Working directory. Default is your shell's working directory. (default: %(default)s)")
    parser.add_argument("--old_ext", "-o", type=str, default=None, help="Old file extension.")
    parser.add_argument("--new_ext", "-n", type=str, default=None, help="New file extension.")
    args = parser.parse_args()

    if (not args.old_ext):
        print(f"Please specify the old extension.")
        exit(1)

    if (not args.new_ext):
        print(f"Please specify the new extension.")
        exit(1)

    if (args.work_dir):
        main(args.work_dir, args.old_ext, args.new_ext)
    else:
        main(os.getcwd(), args.old_ext, args.new_ext)

