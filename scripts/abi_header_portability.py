#!/usr/bin/env python3
"""Header portability check for the Liara C ABI.

For every public header, generate a tiny translation unit that includes the
header *twice* -- exercising both self-containment (the header pulls in
everything it needs on its own) and include-guard idempotence -- and compile it
with ``-fsyntax-only`` as *both* C and C++, across several language standards,
with warnings promoted to errors.

Compiling the same header as C and as C++ is what actually enforces the
"valid C, includable from C++" contract of INTERFACES.md, so no separate
``-Wc++-compat`` pass is needed for the base (it can be added later as an extra
signal).

The header is the contract: if it does not compile standalone and warning-free
in every configuration, that is an ABI portability defect to fix in the header,
not a bug in this script.

Usable both in CI and locally, e.g.::

    python3 abi_header_portability.py \
        --include-dir include --cc gcc-14 --cxx g++-14 \
        --c-standards '11;17;23' --cxx-standards '17;20;23'
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Warning surface applied to every configuration. Kept deliberately small for
# the base; extend here (e.g. -Wshadow, -Wconversion, -Wc++-compat for C) as
# the interface grows.
COMMON_FLAGS_GCC = ["-fsyntax-only", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]

# /Zs : Syntax check only (equivalent of -fsyntax-only)
# /W4 : Warning level 4
# /WX : Treat warnings as errors (equivalent of -Werror)
COMMON_FLAGS_MSVC = ["/Zs", "/W4", "/WX"]


@dataclass(frozen=True)
class Case:
    """A single (header, language, standard, compiler) compilation to attempt."""

    header: Path        # path to the header on disk (for diagnostics)
    include: str        # how it is referenced, e.g. "liara/abi_version.h"
    lang: str           # "c" or "c++"
    std: str            # bare standard number, e.g. "11", "20", "23"
    compiler: str       # compiler binary used

    @property
    def is_msvc(self) -> bool:
        """Helper to determine if we are invoking MSVC."""
        binary_name = Path(self.compiler).stem.lower()
        return binary_name == "cl"

    @property
    def lang_std(self) -> str:
        """The standard flag formatted for the appropriate compiler."""
        if self.is_msvc:
            if self.lang == "c":
                # MSVC supports C11 and C17. If 23 is requested, fallback to clatest or c17.
                if self.std == "23":
                    return "/std:clatest"
                return f"/std:c{self.std}"
            else:
                if self.std == "23":
                    return "/std:c++latest"
                return f"/std:c++{self.std}"
        else:
            prefix = "c" if self.lang == "c" else "c++"
            return f"-std={prefix}{self.std}"

    def __str__(self) -> str:
        return f"{self.include}  [{self.lang_std}]  {self.compiler}"


def discover_headers(include_dir: Path) -> list[tuple[Path, str]]:
    """Return (path, include-spelling) for every *.h under include_dir."""
    headers: list[tuple[Path, str]] = []
    for path in sorted(include_dir.rglob("*.h")):
        include = path.relative_to(include_dir).as_posix()
        headers.append((path, include))
    return headers


def make_tu(tmp: Path, include: str, lang: str) -> Path:
    """Write a translation unit that includes the header twice."""
    ext = ".c" if lang == "c" else ".cpp"
    tu = tmp / (include.replace("/", "_") + ext)
    # Adding a dummy definition to avoid "translation unit is empty" warnings in some compilers.
    tu.write_text(f"#include <{include}>\n#include <{include}>\nint dummy;\n")
    return tu


def compile_case(case: Case, include_dir: Path, tu: Path) -> tuple[bool, str]:
    """Attempt one compilation. Returns (ok, stderr)."""
    if case.is_msvc:
        # /TC forces C compilation, /TP forces C++ compilation
        lang_flag = "/TC" if case.lang == "c" else "/TP"
        cmd = [
            case.compiler,
            lang_flag,
            case.lang_std,
            *COMMON_FLAGS_MSVC,
            f"/I{include_dir}",
            str(tu),
        ]
    else:
        cmd = [
            case.compiler,
            "-x", case.lang,
            case.lang_std,
            *COMMON_FLAGS_GCC,
            "-I", str(include_dir),
            str(tu),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        output = f"{proc.stdout}\n{proc.stderr}".strip()
        return proc.returncode == 0, output


def parse_standards(value: str) -> list[str]:
    return [s.strip() for s in value.split(";") if s.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Liara C ABI header portability check.")
    parser.add_argument("--include-dir", required=True, type=Path,
                        help="Root directory holding the public headers.")
    parser.add_argument("--cc", required=True, help="C compiler binary (e.g. gcc-14).")
    parser.add_argument("--cxx", required=True, help="C++ compiler binary (e.g. g++-14).")
    parser.add_argument("--c-standards", default="11;17;23",
                        help="Semicolon-separated C standards.")
    parser.add_argument("--cxx-standards", default="17;20;23",
                        help="Semicolon-separated C++ standards.")
    args = parser.parse_args()

    include_dir: Path = args.include_dir.resolve()
    if not include_dir.is_dir():
        print(f"::error::include directory not found: {include_dir}", file=sys.stderr)
        return 2

    c_stds = parse_standards(args.c_standards)
    cxx_stds = parse_standards(args.cxx_standards)

    headers = discover_headers(include_dir)
    if not headers:
        print(f"::error::no headers (*.h) found under {include_dir}", file=sys.stderr)
        return 2

    cases: list[Case] = []
    for path, include in headers:
        for std in c_stds:
            cases.append(Case(path, include, "c", std, args.cc))
        for std in cxx_stds:
            cases.append(Case(path, include, "c++", std, args.cxx))

    failures: list[tuple[Case, str]] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for case in cases:
            tu = make_tu(tmp, case.include, case.lang)
            ok, stderr = compile_case(case, include_dir, tu)
            print(f"[{'ok' if ok else 'FAIL'}] {case}")
            if not ok:
                failures.append((case, stderr))

    print()
    print(f"Checked {len(headers)} header(s) across {len(cases)} configuration(s).")

    if failures:
        print(f"{len(failures)} configuration(s) failed:\n")
        for case, stderr in failures:
            # GitHub Actions annotation: surfaces the failure on the PR diff.
            print(f"::error file={case.header}::portability failed ({case})")
            for line in stderr.splitlines():
                print(f"    {line}")
            print()
        return 1

    print("All headers compile standalone and warning-free in every configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())