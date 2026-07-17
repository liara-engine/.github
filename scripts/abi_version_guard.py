#!/usr/bin/env python3
"""Version-bump guard: the declared change level must cover the ABI diff.

In this project versions are bumped by release-please from conventional
commits, and squash-merge uses the PR title as the final commit. The PR title
(+ body footer) is therefore the authoritative *declaration* of the change
level:

    declared major  <-  type ends with '!'  OR  body contains 'BREAKING CHANGE'
    declared minor  <-  type is 'feat'
    declared patch  <-  anything else valid (fix, docs, chore, ...)

The guard compares that declaration with the *required* bump computed by
abi_snapshot.py diff, and fails when the declaration is insufficient:

    required major  -> must declare major
    required minor  -> must declare minor or major
    required patch/none -> anything

Over-declaration (e.g. 'feat!' with no ABI change) is reported as info only:
a change can be breaking for reasons the snapshot cannot see.

Note: pre-1.0, release-please maps breaking -> minor numerically
(bump-minor-pre-major); the guard reasons about the conventional-commit
marker, not the number, so it stays correct across that boundary.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LEVELS = ["none", "patch", "minor", "major"]
CC_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<bang>!)?:\s+\S")


def declared_level(title: str, body: str) -> tuple[str, str]:
    m = CC_RE.match(title.strip())
    if not m:
        return "invalid", f"PR title is not a conventional commit: '{title.strip()}'"
    if m.group("bang") or "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body:
        return "major", "breaking marker ('!' or BREAKING CHANGE footer)"
    if m.group("type") == "feat":
        return "minor", "type 'feat'"
    return "patch", f"type '{m.group('type')}'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Liara ABI version-bump guard.")
    parser.add_argument("--required", required=True, choices=LEVELS)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", type=Path, default=None)
    args = parser.parse_args()

    body = args.body_file.read_text(encoding="utf-8") if args.body_file and args.body_file.exists() else ""
    declared, reason = declared_level(args.title, body)

    print(f"Required by ABI diff : {args.required.upper()}")
    if declared == "invalid":
        print(f"Declared by PR       : INVALID ({reason})")
        print("::error::PR title must be a conventional commit (enforced by commitlint too).")
        return 1
    print(f"Declared by PR       : {declared.upper()} ({reason})")
    print()

    required_idx = LEVELS.index(args.required)
    declared_idx = LEVELS.index(declared)

    if declared_idx >= required_idx:
        if declared == "major" and required_idx < LEVELS.index("major"):
            print("Note: breaking change declared but the ABI snapshot sees no "
                  "breaking surface change. This is allowed (semantic breaks are "
                  "invisible to the snapshot) - double-check it is intentional.")
        print("Version-bump declaration covers the ABI change. OK.")
        return 0

    hint = {
        "minor": "declare it with a 'feat:' PR title",
        "major": "declare it with '!' after the type (e.g. 'feat!:') or a "
                 "'BREAKING CHANGE:' footer in the PR description",
    }[args.required]
    print(f"::error::ABI diff requires a {args.required.upper()} bump but the PR "
          f"declares only {declared.upper()}; {hint}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())