import argparse
import os
import typing

from PIL import Image


OLD_EXTENSION: typing.Final = ".old"


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


def convert_image_to_webp(src_filename: str, dest_filename: str):
    if not dest_filename.endswith(".webp"):
        raise NotImplementedError("Extension must be webp.")

    src_image: Image.Image = Image.open(src_filename)
    src_image.save(dest_filename, lossless=True, quality=100, method=6)


def main(
    src_dir: str,
    dest_dir: str,
    input_extensions: typing.List[str],
    output_extension: str,
    assume_yes: bool,
    rename_src: bool,
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
    for src_filename, dest_filename in source_and_target_filenames:
        if os.path.exists(dest_filename):
            print(f"Destination file `{dest_filename}` exists. Skipping.")
            continue

        print(f"Converting `{src_filename}` to `{dest_filename}`...")
        convert_image_to_webp(src_filename, dest_filename)

        if rename_src:
            os.rename(src_filename, src_filename + OLD_EXTENSION)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src_dir", "-s", type=str, default=os.getcwd())
    parser.add_argument("--dest_dir", "-d", type=str, default=None)
    parser.add_argument("--input_extensions", nargs="+", default=["png"])
    parser.add_argument("--output_extension", type=str, default="webp")
    parser.add_argument("--assume_yes", "-y", action="store_true")
    parser.add_argument("--rename_src", "-r", action="store_true")
    args = parser.parse_args()

    main(
        args.src_dir,
        args.dest_dir,
        args.input_extensions,
        args.output_extension,
        args.assume_yes,
        args.rename_src,
    )
