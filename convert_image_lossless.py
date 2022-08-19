import argparse
import os
import typing
import multiprocessing

from PIL import Image


OLD_EXTENSION: typing.Final = ".old"


# MARK: Filename/path helpers
def get_image_filenames_in_dir(
    src_dir: str, image_extensions: typing.List[str]
) -> typing.List[str]:
    return_value = []

    for current_dir, dir_names, filenames in os.walk(src_dir):
        for filename in filenames:
            match = any((filename.endswith(ext) for ext in image_extensions))
            if match:
                abs_filename = os.path.join(current_dir, filename)
                return_value.append(abs_filename)

    return return_value


def _get_dest_filename(filename: str, dest_extension: str, dest_dir: str):
    filename = os.path.splitext(filename)[0] + dest_extension
    filename = os.path.basename(filename)
    filename = os.path.join(dest_dir, filename)
    return filename


# MARK: Image conversion helpers
def convert_image_worker(src_filename: str, dest_filename: str, rename_src: bool):
    if os.path.exists(dest_filename):
        print(f"Destination file `{dest_filename}` exists. Skipping.")
        return

    print(f"Converting `{src_filename}` to `{dest_filename}`...")
    # TODO: Support more output formats.
    convert_image_to_webp(src_filename, dest_filename)

    if rename_src:
        os.rename(src_filename, src_filename + OLD_EXTENSION)


def convert_image_to_webp(src_filename: str, dest_filename: str):
    if not dest_filename.endswith(".webp"):
        raise NotImplementedError("Extension must be webp.")

    src_image: Image.Image = Image.open(src_filename)
    src_image.save(dest_filename, lossless=True, quality=100, method=6)  # TODO: ICC Profile


def main(
    src_dir: str,
    dest_dir: str,
    input_extensions: typing.List[str],
    output_extension: str,
    assume_yes: bool,
    rename_src: bool,
    processes: int | None,
):
    # Check directories.
    print(f"Using source dir `{src_dir}`.")
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(f"`{src_dir}` isn't a dir!")

    if dest_dir:
        print(f"Using destination dir `{dest_dir}`.")
        if os.path.isfile(dest_dir):
            raise NotADirectoryError(f"`{dest_dir}` isn't a dir!")
        elif not os.path.exists(dest_dir):
            os.mkdir(dest_dir)
            print(f"Created destination dir `{dest_dir}`.")
    else:
        print(f"Saving output to source dir.")

    # Add . before extensions.
    input_extensions = [
        "." + ext for ext in input_extensions if not ext.startswith(".")
    ]
    if not output_extension.startswith("."):
        output_extension = "." + output_extension

    # Get source and target files.
    image_filenames = get_image_filenames_in_dir(src_dir, input_extensions)
    if not image_filenames:
        print("No file to convert.")
        exit(0)

    if dest_dir:
        source_and_target_filenames = tuple(
            (filename, _get_dest_filename(filename, output_extension, dest_dir))
            for filename in image_filenames
        )
    else:
        source_and_target_filenames = tuple(
            (filename, os.path.splitext(filename)[0] + output_extension)
            for filename in image_filenames
        )

    # List source and target files.
    if not assume_yes:
        print(f"{len(source_and_target_filenames)} files to convert:")
        for src_filename, dest_filename in source_and_target_filenames:
            print(f"`{src_filename}` -> `{dest_filename}`")

        consent = input("Convert? (y/n) ")
        if consent.lower() != "y":
            print("Conversion aborted.")
            exit(2)

    # Convert.
    if processes == 0:
        for src_filename, dest_filename in source_and_target_filenames:
            convert_image_worker(src_filename, dest_filename, rename_src)

    else:
        with multiprocessing.Pool(processes) as pool:
            pool.starmap(
                convert_image_worker,
                (
                    (src_filename, dest_filename, rename_src)
                    for src_filename, dest_filename in source_and_target_filenames
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src_dir",
        "-s",
        type=str,
        default=os.getcwd(),
        help=f"Source images dir. Default: %(default)s",
    )
    parser.add_argument(
        "--dest_dir",
        "-d",
        type=str,
        default=None,
        help="Destination dir. If `None`, will use `src_dir`. Default: %(default)s",
    )
    parser.add_argument(
        "--input_extensions", nargs="+", default=["png"], help=f"Default: %(default)s"
    )
    parser.add_argument(
        "--output_extension", type=str, default="webp", help=f"Default: %(default)s"
    )
    parser.add_argument(
        "--assume_yes",
        "-y",
        action="store_true",
        help="If set, don't ask for user confirmation.",
    )
    parser.add_argument(
        "--rename_src",
        "-r",
        action="store_true",
        help=f"If set, add `{OLD_EXTENSION}` to all converted source files.",
    )
    parser.add_argument(
        "--processes",
        "-p",
        type=int,
        default=None,
        help=f"Amount of `multiprocessing` processes to use. "
             f"Uses `os.cpu_count()` ({os.cpu_count()}) if `None`; "
             f"Doesn't use `multiprocessing` if 0. "
             f"Default: %(default)s",
    )
    args = parser.parse_args()

    main(
        args.src_dir,
        args.dest_dir,
        args.input_extensions,
        args.output_extension,
        args.assume_yes,
        args.rename_src,
        args.processes,
    )
