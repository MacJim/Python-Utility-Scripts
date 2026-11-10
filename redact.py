#!/usr/bin/env python3

"""Redact text while preserving its overall structure."""

import string


PRESERVED_CHARS = frozenset(string.punctuation + string.whitespace)
REPLACEMENT_CHAR = "x"


def redact(text: str) -> str:
    return "".join(
        ch if ch in PRESERVED_CHARS else REPLACEMENT_CHAR
        for ch in text
    )


def main():
    try:
        while True:
            text = input("Enter text to redact: ")
            if not text:
                break
            print(redact(text))
    except (KeyboardInterrupt, EOFError):
        print()  # Tidy newline on Ctrl-C/D


if __name__ == "__main__":
    main()
