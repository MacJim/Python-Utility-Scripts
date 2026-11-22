#!/usr/bin/env python3

# Examples:
#   Print filenames from the current directory:
#       ./list_filenames_in_dir.py
#   Save only JPG/PNG filenames:
#       ./list_filenames_in_dir.py ./photos -e jpg png -o names.txt
#   Merge stripped names into an existing list:
#       ./list_filenames_in_dir.py ./photos -e jpg png -o names.txt --merge -d
#   Strip a compound extension:
#       ./list_filenames_in_dir.py ./archives -e tar.gz -d --out_filename archives.txt
# Existing outputs are backed up to <output>.old before replacement.

import argparse
import os
import re
import shutil
import tempfile


def _natural_sort_key(filename: str):
    return [int(part) if part.isdecimal() else part for part in re.split(r"(\d+)", filename)], filename


def _save_filenames_cow(output_filename: str, filenames: list[str]):
    output_dir = os.path.dirname(os.path.abspath(output_filename))
    tmp_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output_dir, delete=False)
    try:
        with tmp_file:
            tmp_file.writelines(f"{filename}\n" for filename in filenames)
        if os.path.exists(output_filename):
            shutil.copyfile(output_filename, f"{output_filename}.old")
        os.replace(tmp_file.name, output_filename)
    finally:
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)


def main(working_dir: str, extensions_filter: list[str] | None = None, drop_extension: bool = False, output_filename: str | None = None, merge: bool = False):
    if merge and output_filename is None:
        raise ValueError("--merge requires --out_filename (-o/--output).")
    if not os.path.isdir(working_dir):
        raise NotADirectoryError(f"`{working_dir}` isn't a dir.")

    extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions_filter or []]
    extensions.sort(key=len, reverse=True)
    filenames = set()
    for filename in os.listdir(working_dir):
        if not os.path.isfile(os.path.join(working_dir, filename)):
            continue
        extension = next((ext for ext in extensions if filename.lower().endswith(ext)), None)
        if extensions and extension is None:
            continue
        if drop_extension:
            filename = filename[:-len(extension)] if extension else os.path.splitext(filename)[0]
        filenames.add(filename)

    if merge and os.path.exists(output_filename):
        with open(output_filename, encoding="utf-8") as output:
            filenames.update(output.read().splitlines())

    sorted_filenames = sorted(filenames, key=_natural_sort_key)
    if output_filename is not None:
        _save_filenames_cow(output_filename, sorted_filenames)
    else:
        for filename in sorted_filenames:
            print(filename)


def cli():
    parser = argparse.ArgumentParser(description="List filenames in natural order, optionally saving them to a text file.")

    input_options = parser.add_argument_group("Input options")
    input_options.add_argument("in_dir", nargs="?", default=os.getcwd(), help="Source directory. Defaults to the current working dir (%(default)s).")
    input_options.add_argument("--extensions_filter", "-e", nargs="*", default=None, help="Accepted suffixes, ignoring case, with or without leading dots (e.g. jpg .png tar.gz). Default: all files.")

    output_options = parser.add_argument_group("Output options")
    output_options.add_argument("--out_filename", "--output", "-o", metavar="FILE", help="Save to this file. Existing contents are backed up to FILE.old. Default: print to standard output.")
    output_options.add_argument("--merge", action="store_true", help="Keep existing output entries and add new names without duplicates. Requires --out_filename.")
    output_options.add_argument("--drop_extension", "-d", action="store_true", help="Strip the matched extension(s) in the output.")

    args = parser.parse_args()
    if args.merge and args.out_filename is None:
        parser.error("--merge requires --out_filename (-o/--output).")
    try:
        main(args.in_dir, args.extensions_filter, args.drop_extension, args.out_filename, args.merge)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    cli()
