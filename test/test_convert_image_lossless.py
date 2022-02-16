import os
import unittest
import tempfile
import typing

from PIL import Image, ImageChops  # Channel Operations

import convert_image_lossless


class ConvertImageLosslessTestCase (unittest.TestCase):
    @staticmethod
    def _generate_src_and_dest_images(dest_ext: str) -> typing.Iterator[typing.Tuple[str, str]]:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        test_filenames = [  # Must not contain duplicate filenames.
            "test_images/1.png",
            "test_images/2.png",
        ]
        test_filenames = [os.path.join(script_dir, f) for f in test_filenames]

        dest_filenames = [os.path.basename(f) for f in test_filenames]
        dest_filenames = [os.path.splitext(f)[0] + dest_ext for f in dest_filenames]

        return zip(test_filenames, dest_filenames)

    def _assert_image_equal(self, src_filename: str, dest_filename: str):
        src_image: Image.Image = Image.open(src_filename)
        dest_image: Image.Image = Image.open(dest_filename)

        diff = ImageChops.difference(src_image, dest_image)
        if diff.getbbox():
            self.fail(f"Images don't equal: {diff.getbbox()}")

    def test_convert_image_to_webp(self):
        test_filenames = self._generate_src_and_dest_images(".webp")

        with tempfile.TemporaryDirectory() as dir_name:
            for src_filename, dest_filename in test_filenames:
                dest_filename = os.path.join(dir_name, dest_filename)

                with self.subTest(src_filename=src_filename, dest_filename=dest_filename):
                    convert_image_lossless.convert_image_to_webp(src_filename, dest_filename)
                    self._assert_image_equal(src_filename, dest_filename)


if __name__ == '__main__':
    unittest.main()
