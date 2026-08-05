#!/usr/bin/env python3
"""Resolve which liara-interfaces ref a repository should be built against.

A module states the ABI versions it works with in ``manifest.json``, per version of itself. The
version it is currently developing is the one ``.release-please-manifest.json`` targets. The
highest entry of that version's ``abi_compatibility`` is therefore the contract the working tree
is written against -- not whatever ``main`` happens to hold, which is only correct by accident and
stops being correct the moment the ABI moves first and the modules catch up afterwards, which is
the normal direction of travel.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PACKAGE_KEY = {"liara": "launcher"}


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def resolve(repo_dir: Path, module: str) -> tuple[str, str]:
    """Return (version, explanation) for the ABI this repository targets."""
    rp_path = repo_dir / ".release-please-manifest.json"
    mf_path = repo_dir / "manifest.json"

    if not rp_path.is_file() or not mf_path.is_file():
        return "", "no manifest.json / .release-please-manifest.json in this repository"

    package = PACKAGE_KEY.get(module, ".")
    target = json.loads(rp_path.read_text(encoding="utf-8")).get(package)
    if not target:
        return "", f"no '{package}' entry in .release-please-manifest.json"

    entry = json.loads(mf_path.read_text(encoding="utf-8")).get("versions", {}).get(target)
    if entry is None:
        return "", f"version {target} is absent from manifest.json"

    compat = entry.get("abi_compatibility") or []
    usable = [v for v in compat if v not in ("dev", "")]
    if not usable:
        return "", f"version {target} declares no concrete abi_compatibility"

    best = max(usable, key=parse_version)
    return best, f"{module} {target} targets ABI {best}"


def tag_exists(owner: str, tag: str) -> bool:
    url = f"https://github.com/{owner}/liara-interfaces.git"
    result = subprocess.run(["git", "ls-remote", "--tags", "--exit-code", url, tag],
                            capture_output=True, text=True)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", required=True, type=Path)
    parser.add_argument("--module", required=True)
    parser.add_argument("--owner", default="liara-engine")
    parser.add_argument("--override", default="", help="Explicit ref; bypasses resolution entirely.")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    if args.override:
        ref, note = args.override, f"explicit override: {args.override}"
    else:
        version, note = resolve(args.repo_dir, args.module)
        if not version:
            ref = "main"
            note = f"{note}; falling back to main"
        else:
            tag = f"v{version}"
            if tag_exists(args.owner, tag):
                ref = tag
            else:
                ref = "main"
                note = f"{note}, which has no tag yet; falling back to main"

    print(f"interfaces ref: {ref}  ({note})")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"interfaces-ref={ref}\n")
            handle.write(f"interfaces-note={note}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())