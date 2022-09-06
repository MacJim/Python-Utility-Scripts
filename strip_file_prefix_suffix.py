import argparse
import os


def maybe_get_new_filename(
    filename: str, prefix: str, suffix: str, strip_whitespaces: bool
) -> tuple[bool, str | None]:
    root, ext = os.path.splitext(filename)
    will_rename = False

    if prefix and root.startswith(prefix):
        root = root[len(prefix) :]
        will_rename = True

    if suffix and root.endswith(suffix):
        root = root[: len(suffix)]
        will_rename = True

    if strip_whitespaces and ((root[0] == " ") or (root[-1] == " ")):
        root = root.strip()
        will_rename = True

    if will_rename:
        return True, f"{root}{ext}"
    else:
        return False, None


def main(
    dir_name: str, prefix: str, suffix: str, strip_whitespaces: bool, assume_yes: bool
):
    # Verify arguments.
    if not os.path.isdir(dir_name):
        raise NotADirectoryError(f"`{dir_name}` isn't a dir.")

    if (not prefix) and (not suffix) and (not strip_whitespaces):
        raise ValueError(f"No prefix or suffix given.")

    # Get filenames.
    old_filenames = os.listdir(dir_name)
    old_filenames.sort()

    # Get new filenames.
    old_and_new_filenames = []
    for filename in old_filenames:
        will_rename, new_filename = maybe_get_new_filename(
            filename, prefix, suffix, strip_whitespaces
        )
        if will_rename:
            old_and_new_filenames.append((filename, new_filename))

    # Show preview.
    if not assume_yes:
        for old_filename, new_filename in old_and_new_filenames:
            print(f"{old_filename} -> {new_filename}")

        consent = input("Convert? (y/n) ")
        if consent.lower() != "y":
            print("Conversion aborted.")
            exit(2)

    # Rename.
    for old_filename, new_filename in old_and_new_filenames:
        old_filename = os.path.join(dir_name, old_filename)
        new_filename = os.path.join(dir_name, new_filename)
        os.rename(old_filename, new_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch remove prefixes and/or suffixes from filenames in a dir."
    )
    parser.add_argument("--dir_name", "-d", default=os.getcwd())
    # TODO: Multiple prefixes and suffixes are currently unsupported.
    # parser.add_argument("--prefixes", nargs="*")
    # parser.add_argument("--suffixes", nargs="*")
    parser.add_argument("--prefix", "-p", type=str, default=None)
    parser.add_argument("--suffix", "-s", type=str, default=None)
    parser.add_argument("--strip_whitespaces", "-w", action="store_true")
    parser.add_argument("--assume_yes", "-y", action="store_true")
    args = parser.parse_args()

    main(
        args.dir_name, args.prefix, args.suffix, args.strip_whitespaces, args.assume_yes
    )
