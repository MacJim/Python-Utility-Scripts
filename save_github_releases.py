#!/usr/bin/env python3
"""
Save one page of GitHub releases as Markdown and complete JSON objects.

Example: python3 save_github_releases.py restic/restic -n 10 -o releases
Set GITHUB_TOKEN to authenticate when needed. Existing files are never overwritten.
"""

import argparse
import json
import os
import re
import sys
from contextlib import ExitStack
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MAX_RELEASES = 100
API_VERSION = "2026-03-10"
FORBIDDEN_CHARACTERS = frozenset('<>:"/\\|?*')
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}"
    for prefix in ("COM", "LPT") for number in "123456789¹²³"
}
STATUS_COLORS = {"SAVED": "32", "SKIPPED": "33", "RENAMED": "33", "ERROR": "31"}


def print_color(status: str, message: str) -> None:
    stream = sys.stderr if status == "ERROR" else sys.stdout
    label = f"[{status}]"
    if stream.isatty() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb":
        label = f"\033[{STATUS_COLORS[status]}m{label}\033[0m"
    print(f"{label} {message}", file=stream)


def fetch_releases(repo: str, count: int) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases?per_page={count}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "save-github-releases",
        "X-GitHub-Api-Version": API_VERSION,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            releases = json.load(response)
    except HTTPError as error:
        message = str(error.reason)
        try:
            with error:
                details = json.load(error)
            if isinstance(details, dict):
                message = details.get("message") or message
        except (ValueError, OSError, HTTPException):
            pass
        raise RuntimeError(f"GitHub HTTP {error.code}: {message}") from error
    except (OSError, HTTPException) as error:
        raise RuntimeError(f"Could not fetch releases: {error}") from error
    except ValueError as error:
        raise RuntimeError("GitHub returned invalid JSON.") from error

    if not isinstance(releases, list):
        raise RuntimeError("Expected a JSON array of releases from GitHub.")
    for index, release in enumerate(releases, start=1):
        if (
            not isinstance(release, dict)
            or not isinstance(release.get("id"), int)
            or isinstance(release["id"], bool)
            or release["id"] < 1
            or not isinstance(release.get("tag_name"), str)
            or any(release.get(field) is not None and not isinstance(release[field], str) for field in ("name", "body"))
        ):
            raise RuntimeError(f"Invalid release object at position {index}.")
    return releases


def is_safe_filename(stem: str) -> bool:
    """Use portable filenames, even when running on a less restrictive filesystem."""
    if not stem or stem.endswith((".", " ")):
        return False
    if any(character in FORBIDDEN_CHARACTERS or ord(character) < 32 or ord(character) == 127 for character in stem):
        return False
    if stem.split(".", 1)[0].rstrip(" ").upper() in RESERVED_NAMES:
        return False
    try:
        stem.encode("utf-8")
    except UnicodeError:
        return False
    return True


def write_pair(output_dir: Path, stem: str, contents: dict[str, str]) -> list[tuple[str, str]]:
    """Open both missing files exclusively; remove new files if either write fails."""
    created = []
    results = []
    try:
        with ExitStack() as files:
            pending = []
            for extension, content in contents.items():
                path = output_dir / f"{stem}.{extension}"
                try:
                    stream = files.enter_context(path.open("x", encoding="utf-8", newline=""))
                except FileExistsError:
                    if path.is_dir():
                        raise IsADirectoryError(f"{path} is a directory.") from None
                    results.append(("SKIPPED", path.name))
                else:
                    created.append(path)
                    pending.append((stream, content))
                    results.append(("SAVED", path.name))
            for stream, content in pending:
                stream.write(content)
    except BaseException:  # Roll back created files, and re-raise.
        for path in created:
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                raise RuntimeError(f"Could not remove incomplete file {str(path)!r}: {error}") from error
        raise
    return results


def save_release(release: dict, output_dir: Path) -> bool:
    tag = release["tag_name"]
    name = release.get("name") or tag
    title = f"# {name}" if name == tag else f"# {name} ({tag})"
    contents = {
        "md": f"{title}\n\n{release.get('body') or ''}",
        "json": json.dumps(release, ensure_ascii=False, indent=2) + "\n",
    }

    try:
        if is_safe_filename(tag):
            try:
                results = write_pair(output_dir, tag, contents)
            except (OSError, UnicodeError) as error:
                reason = str(error)
            else:
                for status, filename in results:
                    print_color(status, f"{tag!r}: {filename!r}")
                return True
        else:
            reason = "tag is not a portable filename"

        stem = f"release-{release['id']}"
        print_color("RENAMED", f"{tag!r} -> {stem!r}: {reason}")
        for status, filename in write_pair(output_dir, stem, contents):
            print_color(status, f"{tag!r}: {filename!r}")
        return True
    except (OSError, UnicodeError, RuntimeError) as error:
        print_color("ERROR", f"{tag!r}: {error}")
        return False


def main(repo: str, count: int = 10, output_dir: str | Path = ".") -> int:
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo) or repo.split("/")[-1] in {".", ".."}:
        raise ValueError("Repository must use the form username/project.")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= MAX_RELEASES:
        raise ValueError(f"Release count must be between 1 and {MAX_RELEASES}; only one page is supported.")

    output_dir = Path(output_dir).expanduser()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        releases = fetch_releases(repo, count)
    except (OSError, RuntimeError) as error:
        print_color("ERROR", str(error))
        return 1

    print(f"Received {len(releases)} release(s) from {repo}; saving to {output_dir}.")
    n_failed = 0
    for release in releases:
        if not save_release(release, output_dir):
            n_failed += 1
    if n_failed:
        print_color("ERROR", f"Could not save {n_failed} release(s); continued processing the others.")
    return 1 if n_failed else 0


def cli():
    parser = argparse.ArgumentParser(
        description="Save GitHub release notes (.md) and complete release objects (.json), skipping existing files.",
        epilog="Fetches only the first page in GitHub's order, including prereleases and any visible drafts. "
        "Set GITHUB_TOKEN for authentication. Set NO_COLOR to disable terminal colors.",
    )
    parser.add_argument("repo", help="GitHub repository in username/project form")
    parser.add_argument("-n", "--count", type=int, default=10, help=f"number of releases, 1 ~ {MAX_RELEASES} (default: %(default)s)")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."), help="output directory; created if missing (default: current directory)")
    args = parser.parse_args()
    try:
        status = main(args.repo, args.count, args.output_dir)
    except ValueError as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
    else:
        sys.exit(status)


if __name__ == "__main__":
    cli()
