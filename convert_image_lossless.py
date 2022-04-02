import argparse
import os
import typing

from PIL import Image


OLD_EXTENSION: typing.Final = ".old"


def get_image_filenames(root_dir: str, image_extensions: typing.List[str]) -> typing.List[str]:
    return_value = []

    for current_dir, dir_names, filenames in os.walk(root_dir):
        for filename in filenames:
            match = any((filename.endswith(ext) for ext in image_extensions))
            if match:
                abs_filename = os.path.join(current_dir, filename)
                return_value.append(abs_filename)

    return return_value


def _get_dest_filename(src_filename: str, dest_extension: str) -> str:
    src_filename_without_extension = os.path.splitext(src_filename)[0]
    return src_filename_without_extension + dest_extension


def convert_image_to_webp(src_filename: str, dest_filename: str):
    if not dest_filename.endswith(".webp"):
        raise NotImplementedError("Extension must be webp.")

    src_image: Image.Image = Image.open(src_filename)
    src_image.save(dest_filename, lossless=True, quality=100, method=6)


def main(root_dir: str, assume_yes: bool, input_extensions: typing.List[str], output_extension: str):
    # Check input directory.
    print(f"Using root dir `{root_dir}`.")
    if not os.path.isdir(root_dir):
        raise NotADirectoryError(f"`{root_dir}` isn't a dir!")

    # Add . before extensions.
    input_extensions = ["." + ext for ext in input_extensions]
    output_extension = "." + output_extension

    # List files to convert.
    image_filenames = get_image_filenames(root_dir, input_extensions)
    if not image_filenames:
        print("No file to convert.")
        exit(0)

    if not assume_yes:
        print(f"{len(image_filenames)} files to convert:")
        for filename in image_filenames:
            print(filename)

        consent = input("Convert? (y/n) ")
        if consent.lower() != "y":
            print("Conversion aborted.")
            exit(2)

    # Get target files.
    source_and_target_filenames = ((filename, _get_dest_filename(filename, output_extension)) for filename in image_filenames)
    for src_filename, dest_filename in source_and_target_filenames:
        if os.path.exists(dest_filename):
            print(f"Destination file `{dest_filename}` exists. Aborted.")
            continue

        print(f"Converting `{src_filename}` to `{dest_filename}`...")
        convert_image_to_webp(src_filename, dest_filename)
        os.rename(src_filename, src_filename + OLD_EXTENSION)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_dir", type=str, default=os.getcwd())
    parser.add_argument("--assume_yes", "-y", action="store_true")
    parser.add_argument("--input_extensions", nargs="+", default=["png"])
    parser.add_argument("--output_extension", type=str, default="webp")
    args = parser.parse_args()

    main(args.root_dir, args.assume_yes, args.input_extensions, args.output_extension)
