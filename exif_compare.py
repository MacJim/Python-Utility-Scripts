"""
- Get EXIF info from `exiftool`
- Extract the related fields, and compare them among files
"""

import argparse
import os
import subprocess
import json
from collections import defaultdict


EXIFTOOL_FILENAME_KEY = "SourceFile"  # Get keys from `exiftool -j filename`

METADATA_ABSENT_KEY = "(Absent)"


def run_exiftool(filename: str) -> dict:
    cmd = ["exiftool", "-j", filename]
    # FIXME: 1 call per file might be slow; Can I call `exiftool` once on all files?
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"exiftool failed on `{filename}` with code {result.returncode}")
    ret = json.loads(result.stdout)
    assert isinstance(ret[0], dict)  # Just crash if output isn't what we expect.
    return ret[0]


def main(filenames: list[str] | None, metadata_fields: list[str]):
    if not filenames:
        print(f"Will scan all files in current dir `{os.getcwd()}`\n")
        filenames = [filename for filename in os.listdir(os.getcwd()) if os.path.isfile(filename)]
        if not filenames:
            raise ValueError("Empty dir")
    filenames.sort()

    metadata_arr = []
    for filename in filenames:
        metadata_arr.append(run_exiftool(filename))

    for field in metadata_fields:
        values = defaultdict(list)
        for file_metadata in metadata_arr:
            if field not in file_metadata:
                values[METADATA_ABSENT_KEY].append(file_metadata[EXIFTOOL_FILENAME_KEY])
            else:
                value = file_metadata[field]
                if isinstance(value, list):  # Some metadata fields are lists (unhashable).
                    value = str(value)
                values[value].append(file_metadata[EXIFTOOL_FILENAME_KEY])

        if len(values) != 1:
            print(f"`{field}` differs among files: {len(values)} values:")
            for value, f in values.items():
                print(f"- {value}: {f}")
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filenames", nargs="*", help="Files to compare; Empty (default): All files in working dir")
    parser.add_argument("-m", "--metadata-fields", nargs="+", required=True, help="Metadata fields to compare; List field names with `exiftool -j`")
    args = parser.parse_args()
    main(args.filenames, args.metadata_fields)
