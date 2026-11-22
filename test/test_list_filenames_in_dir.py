import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import list_filenames_in_dir as listing


class ListFilenamesInDirTest(unittest.TestCase):
    def setUp(self):
        temporary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_dir.cleanup)
        self.directory = Path(temporary_dir.name)
        self.source = self.directory / "source"
        self.source.mkdir()
        self.output = self.directory / "names.txt"
        self.backup = self.directory / "names.txt.old"
        self.stdout = io.StringIO()
        self.enterContext(redirect_stdout(self.stdout))

    def add_files(self, *names):
        for name in names:
            (self.source / name).touch()

    def test_console_output_is_natural_and_nonrecursive(self):
        self.add_files("10.jpg", "2.jpg", "1.jpg", "file10.txt", "file2.txt")
        (self.source / "3.jpg").mkdir()
        (self.source / "3.jpg" / "nested.jpg").touch()
        listing.main(str(self.source))
        self.assertEqual(self.stdout.getvalue(), "1.jpg\n2.jpg\n10.jpg\nfile2.txt\nfile10.txt\n")
        self.assertFalse(self.output.exists())

    def test_default_filter_includes_hidden_and_extensionless_files(self):
        self.add_files("README", ".env", "photo.jpg")
        listing.main(str(self.source))
        self.assertEqual(set(self.stdout.getvalue().splitlines()), {"README", ".env", "photo.jpg"})

    def test_extension_filters_accept_dots_and_ignore_case(self):
        self.add_files("photo.jpg", "image.PNG", "ignored.jpeg", "README")
        for extensions in (["jpg", "png"], [".jpg", ".png"], ["JPG", ".PNG"]):
            with self.subTest(extensions=extensions), redirect_stdout(io.StringIO()) as output:
                listing.main(str(self.source), extensions)
                self.assertEqual(output.getvalue(), "image.PNG\nphoto.jpg\n")

    def test_compound_extensions_match_and_strip(self):
        self.add_files("archive.tar.gz", "other.TAR.GZ", "ignored.zip")
        for extensions in (["tar.gz"], [".tar.gz"], ["gz", ".tar.gz"]):
            for strip in (False, True):
                with self.subTest(extensions=extensions, strip=strip), redirect_stdout(io.StringIO()) as output:
                    listing.main(str(self.source), extensions, strip)
                    expected = "archive\nother\n" if strip else "archive.tar.gz\nother.TAR.GZ\n"
                    self.assertEqual(output.getvalue(), expected)

    def test_stripped_names_are_deduplicated_and_naturally_sorted(self):
        self.add_files("10.jpg", "2.jpg", "2.png", "photo.jpg", "photo.png")
        listing.main(str(self.source), drop_extension=True)
        self.assertEqual(self.stdout.getvalue(), "2\n10\nphoto\n")

    def test_stripping_without_filter_removes_only_the_final_suffix(self):
        self.add_files("archive.tar.gz", ".env", "README")
        listing.main(str(self.source), drop_extension=True)
        self.assertEqual(set(self.stdout.getvalue().splitlines()), {"archive.tar", ".env", "README"})

    def test_equal_numeric_names_have_a_consistent_order(self):
        self.add_files("file1.jpg", "file01.jpg", "file001.jpg")
        listing.main(str(self.source))
        self.assertEqual(self.stdout.getvalue(), "file001.jpg\nfile01.jpg\nfile1.jpg\n")

    def test_save_creates_utf8_file_without_console_output_or_backup(self):
        self.add_files("2.jpg", "1.jpg", "café.jpg")
        listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), "1.jpg\n2.jpg\ncafé.jpg\n".encode())
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.stdout.getvalue(), "")

    def test_replacement_keeps_exact_previous_bytes_and_replaces_backup(self):
        self.add_files("2.jpg", "1.jpg")
        original = b"deleted.jpg\r\n2.jpg"
        self.output.write_bytes(original)
        self.backup.write_bytes(b"older backup")
        listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"1.jpg\n2.jpg\n")
        self.assertEqual(self.backup.read_bytes(), original)
        previous = self.output.read_bytes()
        self.add_files("10.jpg")
        listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"1.jpg\n2.jpg\n10.jpg\n")
        self.assertEqual(self.backup.read_bytes(), previous)

    def test_merge_preserves_existing_entries_without_filtering_or_stripping(self):
        self.add_files("photo.png", "photo.jpg", "2.png", "10.png", "ignored.txt")
        original = b"gone.jpg\r\nphoto.jpg\r\n2\r\n2\r\n"
        self.output.write_bytes(original)
        listing.main(str(self.source), ["png"], True, str(self.output), merge=True)
        self.assertEqual(self.output.read_bytes(), b"2\n10\ngone.jpg\nphoto\nphoto.jpg\n")
        self.assertEqual(self.backup.read_bytes(), original)

    def test_merge_creates_missing_output(self):
        self.add_files("2.jpg", "1.jpg")
        listing.main(str(self.source), output_filename=str(self.output), merge=True)
        self.assertEqual(self.output.read_bytes(), b"1.jpg\n2.jpg\n")
        self.assertFalse(self.backup.exists())

    def test_output_and_backup_are_included_when_inside_source_directory(self):
        self.add_files("1.jpg")
        output = self.source / "names.txt"
        backup = self.source / "names.txt.old"
        output.write_bytes(b"old output\n")
        backup.write_bytes(b"older output\n")
        listing.main(str(self.source), output_filename=str(output))
        self.assertEqual(output.read_bytes(), b"1.jpg\nnames.txt\nnames.txt.old\n")
        self.assertEqual(backup.read_bytes(), b"old output\n")

    def test_empty_listing_replaces_output_and_backs_up_previous_contents(self):
        self.output.write_bytes(b"old entry\n")
        listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"")
        self.assertEqual(self.backup.read_bytes(), b"old entry\n")

    def test_write_failure_preserves_output_and_backup_and_cleans_temporary_file(self):
        self.add_files("1.jpg")
        self.output.write_bytes(b"original\n")
        self.backup.write_bytes(b"previous backup\n")
        temporary_file = tempfile.NamedTemporaryFile(mode="w", dir=self.directory, delete=False)
        with (
            patch.object(listing.tempfile, "NamedTemporaryFile", return_value=temporary_file),
            patch.object(temporary_file, "writelines", side_effect=OSError("Disk full")),
            self.assertRaisesRegex(OSError, "Disk full"),
        ):
            listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"original\n")
        self.assertEqual(self.backup.read_bytes(), b"previous backup\n")
        self.assertEqual({path.name for path in self.directory.iterdir()}, {"source", "names.txt", "names.txt.old"})

    def test_backup_failure_preserves_output_and_cleans_temporary_file(self):
        self.add_files("1.jpg")
        self.output.write_bytes(b"original\n")
        self.backup.mkdir()
        with self.assertRaises(OSError):
            listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"original\n")
        self.assertEqual(list(self.backup.iterdir()), [])
        self.assertEqual({path.name for path in self.directory.iterdir()}, {"source", "names.txt", "names.txt.old"})

    def test_replace_failure_preserves_output_and_cleans_temporary_file(self):
        self.add_files("1.jpg")
        self.output.write_bytes(b"original\n")
        with patch.object(listing.os, "replace", side_effect=OSError("Cannot replace")), self.assertRaisesRegex(OSError, "Cannot replace"):
            listing.main(str(self.source), output_filename=str(self.output))
        self.assertEqual(self.output.read_bytes(), b"original\n")
        self.assertEqual(self.backup.read_bytes(), b"original\n")
        self.assertEqual({path.name for path in self.directory.iterdir()}, {"source", "names.txt", "names.txt.old"})

    def test_cli_saves_and_merges_using_short_and_original_long_options(self):
        self.add_files("10.JPG", "1.jpg", "2.jpg")
        script = str(Path(listing.__file__).resolve())
        for output_flag, extensions_flag, strip_flag in (("-o", "-e", "-d"), ("--output", "--extensions_filter", "--drop_extension")):
            with self.subTest(output_flag=output_flag):
                self.output.write_bytes(b"gone.jpg\n")
                result = subprocess.run(
                    [sys.executable, script, str(self.source), output_flag, str(self.output), extensions_flag, ".jpg", strip_flag, "--merge"],
                    capture_output=True, text=True, check=True,
                )
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")
                self.assertEqual(self.output.read_bytes(), b"1\n2\n10\ngone.jpg\n")
                self.assertEqual(self.backup.read_bytes(), b"gone.jpg\n")

    def test_merge_requires_output(self):
        with self.assertRaisesRegex(ValueError, "--merge requires --output"):
            listing.main(str(self.source), merge=True)
        result = subprocess.run(
            [sys.executable, str(Path(listing.__file__).resolve()), str(self.source), "--merge"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--merge requires --output", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
