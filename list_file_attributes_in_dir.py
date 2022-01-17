import argparse
import csv
import enum
import multiprocessing
import os
import typing
from collections import defaultdict

import sha_hash

# def _calculate_file_sizes_recursively(start_path: str) -> int:
#     # 1. Separate dir names from filenames.
#     dir_names = []
#     filenames = []
#     for name in os.listdir(start_path):
#         abs_name = os.path.join(start_path, name)
#         if (os.path.isdir(abs_name)):
#             dir_names.append(abs_name)
#         elif (os.path.isfile(abs_name)):
#             filenames.append(abs_name)
#
#     # 2. Sort.
#     dir_names.sort()
#     filenames.sort()
#
#     # 3. Recurse on sub dirs.
#     return_value = 0
#
#     for sub_dir_name in dir_names:
#         return_value += _calculate_file_sizes_recursively(sub_dir_name)
#
#     # 4. Calculate file sizes.
#
#     return return_value


# MARK: - Get filenames and dir names
class PathFormat (enum.Enum):
    UNMODIFIED = "unmodified"

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


def get_all_file_and_dir_names(start_path: str, path_format=PathFormat.UNMODIFIED) -> typing.List[str]:
    """
    Get all filenames and dir names.

    Dir names end with `os.sep` to make them distinguishable.

    :param start_path:
    :param path_format:
    :return:
    """
    if path_format == PathFormat.ABSOLUTE:
        start_path = os.path.abspath(start_path)
    elif path_format == PathFormat.RELATIVE:
        os.chdir(os.path.dirname(os.path.abspath(start_path)))
        start_path = os.path.basename(start_path)

    return_value = []

    for root_path, dir_names, filenames in os.walk(start_path):
        if not root_path.endswith(os.sep):
            root_path += os.sep

        return_value.append(root_path)

        dir_names.sort()
        filenames.sort()

        abs_filenames = [os.path.join(root_path, f) for f in filenames]
        return_value += abs_filenames

    return return_value


# MARK: - Attributes
class AttributeKeys:
    FILENAME = "filename"

    SIZE = "size"
    SHA_256_HASH = "sha256"


HASH_FILE_SIZE_THRESHOLD = 65536


def _calculate_file_attributes_worker(filename: str, attribute_keys: typing.List[str]) -> typing.Dict[str, typing.Any]:
    """
    Calculate file attributes.

    Directory names are included in the returned dictionary, but their other attributes are not.

    :param filename:
    :param attribute_keys: A list of `AttributeKeys` constants specifying the attributes to calculate.
    :return:
    """
    return_value = {AttributeKeys.FILENAME: filename}

    if (not os.path.isfile(filename)):
        # This is a folder.
        # Return an empty dict because we can only calculate its info after calculating its files.
        # raise ValueError(f"`{filename}` is not a file!")
        return return_value

    # Calculate size.
    # This is also the prerequisite for has functions.
    if ((AttributeKeys.SIZE in attribute_keys) or (AttributeKeys.SHA_256_HASH in attribute_keys)):
        file_size = os.path.getsize(filename)

    # Size.
    if AttributeKeys.SIZE in attribute_keys:
        return_value[AttributeKeys.SIZE] = file_size

    # Hash.
    if AttributeKeys.SHA_256_HASH in attribute_keys:
        if file_size > HASH_FILE_SIZE_THRESHOLD:
            return_value[AttributeKeys.SHA_256_HASH] = sha_hash.get_sha_hash_of_big_file(filename, sha_hash.HashAlgorithm.SHA256)
        else:
            return_value[AttributeKeys.SHA_256_HASH] = sha_hash.get_sha_hash_of_file(filename, sha_hash.HashAlgorithm.SHA256)

    return return_value


def _calculate_dir_attributes(attribute_dicts: typing.List[typing.Dict[str, typing.Any]], attribute_keys: typing.List[str]):
    """
    Select directories from `attribute_dicts` and update their attributes according to the files they contain.

    Currently this function simply adds up the size of files in directories.

    :param attribute_dicts:
    :param attribute_keys:
    :return: None
    """
    if AttributeKeys.SIZE in attribute_keys:
        size_cache = defaultdict(int)

        # Iterate in reversed order because sub-directories/files always appear after parents.
        for d in reversed(attribute_dicts):
            filename: str = d[AttributeKeys.FILENAME]
            if (filename.endswith(os.sep)):
                # This is a dir.
                if filename[:-1] in size_cache:
                    # `size_cache` entries don't have the ending `os.sep`.
                    d[AttributeKeys.SIZE] = size_cache[filename[:-1]]
                    del size_cache[filename[:-1]]
                elif filename in size_cache:
                    # Just in case. Should never get executed.
                    d[AttributeKeys.SIZE] = size_cache[filename]
                    del size_cache[filename]
                else:
                    # Empty dir.
                    d[AttributeKeys.SIZE] = 0

                parent_dir = os.path.dirname(filename[:-1])    # We must remove the final `os.sep`. Otherwise, `parent_dir` will be the dir as `filename`.

            else:
                # This is a file.
                parent_dir = os.path.dirname(filename)

            # Add current size to parent's size in `size_cache`.
            size_cache[parent_dir] += d[AttributeKeys.SIZE]


# MARK: - CSV
def write_attribute_dicts_to_csv(attribute_dicts: typing.List[typing.Dict[str, typing.Any]], attribute_keys: typing.List[str], csv_filename: str):
    with open(csv_filename, "w") as f:    # Default encoding is UTF-8 (even if there are only ASCII characters)
        fieldnames = [AttributeKeys.FILENAME] + attribute_keys
        writer = csv.DictWriter(f, fieldnames)

        writer.writeheader()
        writer.writerows(attribute_dicts)


# MARK: - Main
def main(start_path: str, attribute_keys: typing.List[str], csv_filename: str, processes: int, path_format: PathFormat):
    # 1. Verify parameters.
    if not attribute_keys:
        print(f"No designated attribute keys. Nothing to do.")
        return

    for key in attribute_keys:
        if ((key != AttributeKeys.SIZE) and (key != AttributeKeys.SHA_256_HASH)):
            raise ValueError(f"Invalid attribute key `{key}`.")

    if AttributeKeys.FILENAME in attribute_keys:
        # Filename is a special key and always appear first in the attribute dicts.
        # It should not be specified in the command line arguments.
        attribute_keys.remove(AttributeKeys.FILENAME)

    csv_filename = os.path.abspath(csv_filename)    # The `get_all_file_and_dir_names` may change the working directory if `path_format` is `RELATIVE`.
    if (os.path.exists(csv_filename)):
        raise ValueError(f"CSV file `{csv_filename}` exists!")

    # 2. Get file and dir names.
    file_and_dir_names = get_all_file_and_dir_names(start_path, path_format=path_format)
    # for f in file_and_dir_names:
    #     print(f)

    # 3. Calculate file attributes.
    if (processes > 1):
        with multiprocessing.Pool(processes=processes) as pool:
            attribute_dicts = pool.starmap(_calculate_file_attributes_worker, [(filename, attribute_keys) for filename in file_and_dir_names])
    else:
        attribute_dicts = [_calculate_file_attributes_worker(filename, attribute_keys) for filename in file_and_dir_names]

    # for d in attribute_dicts:
    #     print(d)

    # 4. Calculate dir attributes.
    _calculate_dir_attributes(attribute_dicts, attribute_keys)

    # for d in attribute_dicts:
    #     print(d)

    # 5. Save to csv.
    write_attribute_dicts_to_csv(attribute_dicts, attribute_keys, csv_filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List file attributes recursively in the specified directory.")
    parser.add_argument("dir_name", nargs="?", default=os.getcwd(), help="The root directory name. Defaults to the current working dir (%(default)s).")
    parser.add_argument("--attributes", "-a", nargs="*", default=[AttributeKeys.SIZE, AttributeKeys.SHA_256_HASH], help="Attributes to include in the output file. (default: %(default)s)")
    parser.add_argument("--csv_filename", "-o", type=str, default="file_attributes.csv", help="The output filename. (default: %(default)s)")
    parser.add_argument("--processes", "-p", type=int, default=1, help="`multiprocessing` process count. By default this script does not use multiple processes, which is sufficient for most cases.")
    parser.add_argument("--path_format", "-f", type=str, default=PathFormat.UNMODIFIED.value, help=f"File/dir name format in the output file. Possible values: {PathFormat.UNMODIFIED.value}, {PathFormat.ABSOLUTE.value}, {PathFormat.RELATIVE.value}. (default: %(default)s)")
    args = parser.parse_args()

    main(args.dir_name, args.attributes, args.csv_filename, args.processes, PathFormat(args.path_format))
