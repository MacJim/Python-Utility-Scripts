import io
import json
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import save_github_releases as saver


def release(tag="v1.0", release_id=123, name="v1.0", body="Release notes: café\n\n- A change\n"):
    return {
        "id": release_id, "tag_name": tag, "name": name, "body": body,
        "prerelease": True, "author": {"login": "example"}, "assets": [{"id": 456}],
    }


class SaveGitHubReleasesTest(unittest.TestCase):
    def setUp(self):
        temporary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_dir.cleanup)
        self.output_dir = Path(temporary_dir.name)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.enterContext(redirect_stdout(self.stdout))
        self.enterContext(redirect_stderr(self.stderr))

    def run_main(self, releases):
        with patch.object(saver, "fetch_releases", return_value=releases):
            return saver.main("navidrome/navidrome", output_dir=self.output_dir)

    def test_titles_body_and_complete_json(self):
        for name, title in (("v1.0", "# v1.0"), ("Release One", "# Release One (v1.0)"), (None, "# v1.0")):
            for body in ("Notes: café\r\n\n- A change\n", None):
                with self.subTest(name=name, body=body), tempfile.TemporaryDirectory() as directory:
                    item = release(name=name, body=body)
                    self.assertTrue(saver.save_release(item, Path(directory)))
                    self.assertEqual((Path(directory) / "v1.0.md").read_bytes(), f"{title}\n\n{body or ''}".encode())
                    self.assertEqual(json.loads((Path(directory) / "v1.0.json").read_text(encoding="utf-8")), item)

    def test_existing_markdown_is_preserved_and_missing_json_is_saved(self):
        markdown = self.output_dir / "v1.0.md"
        markdown.write_text("My edited notes", encoding="utf-8")
        self.assertEqual(self.run_main([release()]), 0)
        self.assertEqual(markdown.read_text(encoding="utf-8"), "My edited notes")
        self.assertEqual(json.loads((self.output_dir / "v1.0.json").read_text(encoding="utf-8")), release())
        before = {path.name: path.read_bytes() for path in self.output_dir.iterdir()}
        self.assertEqual(self.run_main([release(body="Changed upstream")]), 0)
        self.assertEqual({path.name: path.read_bytes() for path in self.output_dir.iterdir()}, before)
        self.assertIn("[SKIPPED]", self.stdout.getvalue())
        self.assertIn("[SAVED]", self.stdout.getvalue())
        self.assertNotIn("\033[", self.stdout.getvalue())

    def test_existing_json_is_preserved_and_missing_markdown_is_saved(self):
        json_path = self.output_dir / "v1.0.json"
        json_path.write_text("Keep this file", encoding="utf-8")
        self.assertEqual(self.run_main([release()]), 0)
        self.assertEqual(json_path.read_text(encoding="utf-8"), "Keep this file")
        self.assertTrue((self.output_dir / "v1.0.md").is_file())

    def test_unsafe_tags_use_stable_ids_and_skip_on_rerun(self):
        tags = ["../escape", "/absolute", "a\\b", "a:b", "a?b", "a*b", 'a"b', "a|b", "a<b>", "a\x00b", "a\nb", "a\x7fb", "CON", "nul.txt", "LPT¹", "trailing.", "trailing ", ".", "..", ""]
        items = [release(tag=tag, release_id=index) for index, tag in enumerate(tags, start=1)]
        self.assertEqual(self.run_main(items), 0)
        expected = {f"release-{index}.{extension}" for index in range(1, len(items) + 1) for extension in ("md", "json")}
        self.assertEqual({path.name for path in self.output_dir.iterdir()}, expected)
        before = {path.name: path.read_bytes() for path in self.output_dir.iterdir()}
        self.assertEqual(self.run_main(items), 0)
        self.assertEqual({path.name: path.read_bytes() for path in self.output_dir.iterdir()}, before)
        self.assertIn("[RENAMED]", self.stdout.getvalue())

    def test_long_tag_rolls_back_first_file_before_using_generic_pair(self):
        # The Markdown name fits a 255-byte component limit; the JSON name does not.
        self.assertEqual(self.run_main([release(tag="v" * 251)]), 0)
        self.assertEqual({path.name for path in self.output_dir.iterdir()}, {"release-123.md", "release-123.json"})

    def test_directory_collision_uses_generic_pair(self):
        (self.output_dir / "v1.0.json").mkdir()
        self.assertEqual(self.run_main([release()]), 0)
        self.assertFalse((self.output_dir / "v1.0.md").exists())
        self.assertTrue((self.output_dir / "v1.0.json").is_dir())
        self.assertTrue((self.output_dir / "release-123.md").is_file())
        self.assertTrue((self.output_dir / "release-123.json").is_file())

    def test_symlink_is_not_followed_or_overwritten(self):
        target = self.output_dir / "original.md"
        target.write_text("Original contents", encoding="utf-8")
        (self.output_dir / "v1.0.md").symlink_to(target)
        self.assertEqual(self.run_main([release()]), 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "Original contents")
        self.assertTrue((self.output_dir / "v1.0.md").is_symlink())
        self.assertTrue((self.output_dir / "v1.0.json").is_file())

    def test_failed_write_rolls_back_then_uses_generic_pair(self):
        original_open = Path.open

        @contextmanager
        def failing_open(path, *args, **kwargs):
            with original_open(path, *args, **kwargs) as stream:
                if path.name == "v1.0.json":
                    yield Mock(wraps=stream, write=Mock(side_effect=PermissionError("Cannot write this filename")))
                else:
                    yield stream

        with patch.object(Path, "open", failing_open):
            self.assertEqual(self.run_main([release()]), 0)
        self.assertEqual({path.name for path in self.output_dir.iterdir()}, {"release-123.md", "release-123.json"})
        self.assertEqual(json.loads((self.output_dir / "release-123.json").read_text(encoding="utf-8")), release())

    def test_interruption_removes_incomplete_files_and_preserves_existing_ones(self):
        markdown = self.output_dir / "v1.0.md"
        markdown.write_text("Keep my notes", encoding="utf-8")
        original_open = Path.open

        @contextmanager
        def interrupted_open(path, *args, **kwargs):
            with original_open(path, *args, **kwargs) as stream:
                yield Mock(wraps=stream, write=Mock(side_effect=KeyboardInterrupt))

        with patch.object(Path, "open", interrupted_open), self.assertRaises(KeyboardInterrupt):
            self.run_main([release()])
        self.assertEqual(markdown.read_text(encoding="utf-8"), "Keep my notes")
        self.assertFalse((self.output_dir / "v1.0.json").exists())

    def test_failed_release_does_not_prevent_saving_the_next_one(self):
        original_open = Path.open

        def denied_open(path, *args, **kwargs):
            if path.stem in {"v1.0", "release-123"}:
                raise PermissionError("Access denied")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", denied_open):
            self.assertEqual(self.run_main([release(), release(tag="v2.0", release_id=124)]), 1)
        self.assertEqual({path.name for path in self.output_dir.iterdir()}, {"v2.0.md", "v2.0.json"})
        self.assertIn("[ERROR]", self.stderr.getvalue())

    def test_existing_output_directory_and_empty_response_succeed(self):
        self.assertEqual(self.run_main([]), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_missing_output_directory_fails_before_fetching_and_is_not_created(self):
        output_dir = self.output_dir / "new" / "releases"
        with patch.object(saver, "fetch_releases") as fetch:
            self.assertEqual(saver.main("navidrome/navidrome", output_dir=output_dir), 1)
            fetch.assert_not_called()
        self.assertFalse(output_dir.parent.exists())
        self.assertIn("Output directory must be an existing directory", self.stderr.getvalue())

    def test_invalid_arguments_are_rejected_before_fetching(self):
        with patch.object(saver, "fetch_releases") as fetch:
            for count in (0, -1, 101, True):
                with self.subTest(count=count), self.assertRaisesRegex(ValueError, "between 1 and 100"):
                    saver.main("navidrome/navidrome", count, self.output_dir)
            for repo in ("navidrome", "https://github.com/a/b", "../repo", "owner/..", "a/b?c"):
                with self.subTest(repo=repo), self.assertRaisesRegex(ValueError, "username/project"):
                    saver.main(repo, output_dir=self.output_dir)
            fetch.assert_not_called()

    def test_output_path_that_is_a_file_fails_before_fetching(self):
        output_file = self.output_dir / "file"
        output_file.touch()
        with patch.object(saver, "fetch_releases") as fetch:
            self.assertEqual(saver.main("navidrome/navidrome", output_dir=output_file), 1)
            fetch.assert_not_called()
        self.assertTrue(output_file.is_file())
        self.assertIn("Output directory must be an existing directory", self.stderr.getvalue())

    def test_first_page_request_and_optional_authentication(self):
        items = [release()]
        with patch.dict("os.environ", {"GITHUB_TOKEN": "example-token"}):
            with patch.object(saver, "urlopen", return_value=io.BytesIO(json.dumps(items).encode())) as request:
                self.assertEqual(saver.fetch_releases("navidrome/navidrome", 100), items)
        args, kwargs = request.call_args
        self.assertEqual(args[0].full_url, "https://api.github.com/repos/navidrome/navidrome/releases?per_page=100")
        self.assertEqual(args[0].get_header("Authorization"), "Bearer example-token")
        self.assertEqual(args[0].get_header("Accept"), "application/vnd.github+json")
        self.assertEqual(kwargs["timeout"], 30)
        request.assert_called_once()

    def test_network_http_and_invalid_response_errors(self):
        http_error = HTTPError("https://api.github.com/", 403, "Forbidden", {}, io.BytesIO(b'{"message":"API rate limit exceeded"}'))
        for error, expected in ((URLError("Offline"), "Could not fetch releases"), (http_error, "GitHub HTTP 403: API rate limit exceeded")):
            with self.subTest(error=error), patch.object(saver, "urlopen", side_effect=error):
                self.assertEqual(saver.main("navidrome/navidrome", output_dir=self.output_dir), 1)
                self.assertIn(expected, self.stderr.getvalue())
        for payload in (b"not JSON", b'{}', b'[null]', b'[{"id":123,"tag_name":123}]', b'[{"id":123,"tag_name":"v1","body":42}]'):
            with self.subTest(payload=payload), patch.object(saver, "urlopen", return_value=io.BytesIO(payload)):
                self.assertEqual(saver.main("navidrome/navidrome", output_dir=self.output_dir), 1)
        self.assertEqual(list(self.output_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
