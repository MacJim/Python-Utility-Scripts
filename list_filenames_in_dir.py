import argparse
import os


# TODO: Also list files in sub-directories.


def main(working_dir: str, extensions_filter: list[str] | None, drop_extension: bool):
    if not os.path.isdir(working_dir):
        raise NotADirectoryError(f"`{working_dir}` isn't a dir.")

    filenames = os.listdir(working_dir)

    filenames = [f for f in filenames if os.path.isfile(os.path.join(working_dir, f))]
    if extensions_filter:
        old_filenames = filenames
        filenames = []
        for f in old_filenames:
            for ext in extensions_filter:
                if ext[0] != ".":
                    ext = f".{ext}"
                if os.path.splitext(f)[-1] == ext:
                    filenames.append(f)
                    break

    filenames.sort()

    for f in filenames:
        if drop_extension:
            print(os.path.splitext(f)[0])
        else:
            print(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List filenames.")
    parser.add_argument("dir_name", nargs="?", default=os.getcwd(), help="The root directory name. Defaults to the current working dir (%(default)s).")
    parser.add_argument("--extensions_filter", "-e", nargs="*", default=None, help="Filter files by extensions. Default: Allow all extensions.")
    parser.add_argument("--drop_extension", "-d", action="store_true", help="If specified, drop file extensions from the output.")
    args = parser.parse_args()

    main(args.dir_name, args.extensions_filter, args.drop_extension)
