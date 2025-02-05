import argparse
import os


def main(work_dir: str, old_ext: str | None, new_ext: str | None):
    if (not old_ext) and (not new_ext):
        raise ValueError("Old and new extensions can't both be empty")

    if old_ext and old_ext[0] != ".":
        old_ext = f".{old_ext}"
    if new_ext and new_ext[0] != ".":
        new_ext = f".{new_ext}"

    if old_ext == new_ext:
        raise ValueError("Old and new extensions must differ")

    print(f"Working directory: {work_dir}")
    print(f"Old extension: {old_ext if old_ext else '(empty, add extension to files without an extension)'}")
    print(f"New extension: {new_ext if new_ext else '(empty, remove extension)'}")

    filenames_old = os.listdir(work_dir)
    filenames_old = [f for f in filenames_old if os.path.isfile(os.path.join(work_dir, f))]  # NOTE: Ignore dirs.

    # FIXME: Handle filenames that that start with `.`
    if old_ext:
        filenames_old = [f for f in filenames_old if f.endswith(old_ext)]
    else:
        filenames_old = [f for f in filenames_old if "." not in f]

    if not filenames_old:
        print("No file matches the old extension. Nothing to do.")
        exit(0)

    filenames_old.sort()

    if old_ext:
        filenames_new = [f[:-len(old_ext)] + (new_ext if new_ext else "") for f in filenames_old]
    else:
        filenames_new = [f + (new_ext if new_ext else "") for f in filenames_old]

    filenames = [
        (os.path.join(work_dir, old), os.path.join(work_dir, new))
        for old, new in zip(filenames_old, filenames_new)
    ]
    ignored_filenames = [(old, new) for old, new in filenames if os.path.exists(new)]
    filenames = [(old, new) for old, new in filenames if not os.path.exists(new)]

    print(f"{len(filenames)} files to rename:")
    for old, new in filenames:
        print(f"{old} -> {new}")

    if ignored_filenames:
        print(f"{len(ignored_filenames)} files ignored due to existing target:")
        for old, new in ignored_filenames:
            print(f"{old} -> {new}")

    consent = input("Proceed? (y/n) ")
    if consent.lower() != "y":
        print("Aborted.")
        exit(2)

    for old, new in filenames:
        os.rename(old, new)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work_dir", "-d", type=str, default=os.getcwd(), help="Working directory. Default: Current working directory: %(default)s")
    parser.add_argument("--old_ext", "-o", type=str, default=None, help="Old file extension. Empty: Add extension to files without an extension")
    parser.add_argument("--new_ext", "-n", type=str, default=None, help="New file extension. Empty: Remove extension")
    args = parser.parse_args()

    main(args.work_dir, args.old_ext, args.new_ext)
