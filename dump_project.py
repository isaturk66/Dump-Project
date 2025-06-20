#!/usr/bin/env python3
"""dump_project.py

Author: İsa Türk
License: MIT

MIT License
-----------
Copyright (c) 2025 İsa Türk

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from os.path import abspath, dirname, join
from pathlib import Path
from typing import Callable, Iterable, List, Reversible, Tuple, Union

_READ_SIZE = 1024  # bytes to sample when detecting "binaryness"

# ---------------------------------------------------------------------------
# Low‑level helpers
# ---------------------------------------------------------------------------


def is_binary_file(path: Path, read_size: int = _READ_SIZE) -> bool:
    """Return **True** when *path* appears to be a binary file."""
    try:
        with path.open("rb") as fh:
            return b"\0" in fh.read(read_size)
    except OSError:
        return True


def path_is_hidden(path: Path) -> bool:
    """Return **True** if *path* or one of its components starts with a dot."""
    return any(part.startswith(".") for part in path.parts)


# ---------------------------------------------------------------------------
# .dumpignore parsing logic
# Attribution: The following code for parsing gitignore-style files is
# adapted from the 'gitignore_parser' library by Michael Herrmann (mherrmann).
# License: MIT
# ---------------------------------------------------------------------------


def handle_negation(file_path, rules: Reversible["IgnoreRule"]):
    for rule in reversed(rules):
        if rule.match(file_path):
            return not rule.negation
    return False


def parse_dumpignore(full_path, base_dir=None):
    if base_dir is None:
        base_dir = dirname(full_path)
    with open(full_path) as ignore_file:
        return _parse_dumpignore_lines(ignore_file, full_path, base_dir)


def _parse_dumpignore_lines(lines, full_path, base_dir):
    base_dir = _normalize_path(base_dir)
    rules = []
    
    # Add a dynamic rule to ignore the ignore-file itself
    ignore_filename = Path(full_path).name
    default_rule = rule_from_pattern(
        ignore_filename, base_path=base_dir, source=("default", 0)
    )
    if default_rule:
        rules.append(default_rule)

    for line_no, line in enumerate(lines, start=1):
        rule = rule_from_pattern(
            line.rstrip("\n"), base_path=base_dir, source=(full_path, line_no)
        )
        if rule:
            rules.append(rule)
    if not any(r.negation for r in rules):
        return lambda file_path: any(r.match(file_path) for r in rules)
    else:
        # We have negation rules. We can't use a simple "any" to evaluate them.
        # Later rules override earlier rules.
        return lambda file_path: handle_negation(file_path, rules)


def rule_from_pattern(pattern, base_path=None, source=None):
    """
    Take a .dumpignore match pattern and return an IgnoreRule.
    """
    orig_pattern = pattern
    if pattern.strip() == "" or pattern[0] == "#":
        return None

    if pattern[0] == "!":
        negation = True
        pattern = pattern[1:]
    else:
        negation = False

    pattern = re.sub(r"([^/])\*{2,}", r"\1*", pattern)
    pattern = re.sub(r"\*{2,}([^/])", r"*\1", pattern)

    if pattern.rstrip() == "/":
        return None

    directory_only = pattern[-1] == "/"
    anchored = "/" in pattern[:-1]

    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.startswith("**"):
        pattern = pattern[2:]
        anchored = False
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.endswith("/"):
        pattern = pattern[:-1]

    if pattern.startswith("\\") and pattern[1] in ("#", "!"):
        pattern = pattern[1:]

    i = len(pattern) - 1
    striptrailingspaces = True
    while i > 1 and pattern[i] == " ":
        if pattern[i - 1] == "\\":
            pattern = pattern[: i - 1] + pattern[i:]
            i = i - 1
            striptrailingspaces = False
        else:
            if striptrailingspaces:
                pattern = pattern[:i]
        i = i - 1

    regex = fnmatch_pathname_to_regex(
        pattern, directory_only, negation, anchored=bool(anchored)
    )
    return IgnoreRule(
        pattern=orig_pattern,
        regex=regex,
        negation=negation,
        directory_only=directory_only,
        anchored=anchored,
        base_path=base_path if base_path else None,
        source=source,
    )


IGNORE_RULE_FIELDS = [
    "pattern",
    "regex",
    "negation",
    "directory_only",
    "anchored",
    "base_path",
    "source",
]


class IgnoreRule(collections.namedtuple("IgnoreRule_", IGNORE_RULE_FIELDS)):
    def __str__(self):
        return self.pattern

    def __repr__(self):
        return "".join(["IgnoreRule('", self.pattern, "')"])

    def match(self, abs_path: Union[str, Path]):
        matched = False
        if self.base_path:
            try:
                rel_path = str(_normalize_path(abs_path).relative_to(self.base_path))
            except ValueError:
                 # On Windows, abs_path and self.base_path may be on different drives.
                 return False
        else:
            rel_path = str(_normalize_path(abs_path))

        if self.negation and isinstance(abs_path, str) and abs_path.endswith("/"):
            rel_path += "/"

        if rel_path.startswith("./"):
            rel_path = rel_path[2:]

        if re.search(self.regex, rel_path):
            matched = True
        return matched


def fnmatch_pathname_to_regex(
    pattern, directory_only: bool, negation: bool, anchored: bool = False
):
    i, n = 0, len(pattern)
    seps = [re.escape(os.sep)]
    if os.altsep is not None:
        seps.append(re.escape(os.altsep))
    seps_group = "[" + "|".join(seps) + "]"
    nonsep = r"[^{}]".format("|".join(seps))
    res = []
    while i < n:
        c = pattern[i]
        i += 1
        if c == "*":
            try:
                if pattern[i] == "*":
                    i += 1
                    if i < n and pattern[i] == "/":
                        i += 1
                        res.append("".join(["(.*", seps_group, ")?"]))
                    else:
                        res.append(".*")
                else:
                    res.append("".join([nonsep, "*"]))
            except IndexError:
                res.append("".join([nonsep, "*"]))
        elif c == "?":
            res.append(nonsep)
        elif c == "/":
            res.append(seps_group)
        elif c == "[":
            j = i
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                res.append("\\[")
            else:
                stuff = pattern[i:j].replace("\\", "\\\\").replace("/", "")
                i = j + 1
                if stuff[0] == "!":
                    stuff = "".join(["^", stuff[1:]])
                elif stuff[0] == "^":
                    stuff = "".join("\\" + stuff)
                res.append("[{}]".format(stuff))
        else:
            res.append(re.escape(c))

    if anchored:
        res.insert(0, "^")
    else:
        res.insert(0, f"(^|{seps_group})")

    if not directory_only:
        res.append("$")
    elif directory_only and negation:
        res.append("/$")
    else:
        res.append("($|\\/)")
    return "".join(res)


def _normalize_path(path: Union[str, Path]) -> Path:
    return Path(abspath(path))


def load_dumpignore_rules(
    root_path: Path, ignore_file: Path | None
) -> Callable[[Path], bool]:
    """Load ignore rules from .dumpignore or a custom file."""
    if ignore_file:
        dumpignore_path = ignore_file
    else:
        dumpignore_path = root_path / ".dumpignore"

    if dumpignore_path.is_file():
        return parse_dumpignore(str(dumpignore_path), base_dir=str(root_path))
    return lambda path: False


# ---------------------------------------------------------------------------
# Project walking and presentation
# ---------------------------------------------------------------------------


def walk_project(
    root: Path, is_ignored: Callable[[Path], bool]
) -> Iterable[Tuple[Path, List[Path], List[Path]]]:
    """Yield (dir, sub_dirs, files), skipping hidden and ignored paths."""
    for cur_dir, dirs, files in os.walk(root, topdown=True):
        cur_path = Path(cur_dir)

        if path_is_hidden(cur_path.relative_to(root)):
            dirs[:] = []
            continue

        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and not is_ignored(cur_path / d)
        ]
        visible_files = [f for f in files if not is_ignored(cur_path / f)]

        yield cur_path, [cur_path / d for d in dirs], [
            cur_path / f for f in visible_files
        ]


def print_tree_view(root: Path, is_ignored: Callable[[Path], bool]) -> None:
    """Pretty‑print the folder hierarchy under *root*."""
    for directory, _, files in walk_project(root, is_ignored):
        indent = "  " * len(directory.relative_to(root).parts)
        print(f"{indent}{directory.name}/")
        sub_indent = indent + "  "
        for file in sorted(files, key=lambda p: p.name):
            print(f"{sub_indent}{file.name}")


def dump_project_contents(root: Path, is_ignored: Callable[[Path], bool]) -> None:
    """Print the contents of every readable, non‑binary file under *root*."""
    print("\n\n### Project File Contents ###\n")
    files = [
        file for _, _, fs in walk_project(root, is_ignored) for file in fs
    ]
    files.sort(key=lambda p: (len(p.relative_to(root).parts), p.as_posix()))
    for path in files:
        rel = path.relative_to(root)
        print(f"{"#" *20} {rel} {"#" *20}")
        if is_binary_file(path):
            print("This file could not be read or is a binary file.\n")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            text = "This file could not be read or is a binary file."
        print(text, "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print project tree and file contents, honoring a .dumpignore file."
    )
    parser.add_argument(
        "directory", type=Path, help="Root directory of the project to inspect."
    )
    parser.add_argument(
        "--ignore-file",
        type=Path,
        help="Path to a custom .dumpignore file.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = _parse_args(argv)
    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    is_ignored = load_dumpignore_rules(root, args.ignore_file)

    print("### Folder Structure (tree style) ###\n")
    print_tree_view(root, is_ignored)
    dump_project_contents(root, is_ignored)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)