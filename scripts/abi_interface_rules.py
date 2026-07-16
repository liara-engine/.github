#!/usr/bin/env python3
"""libclang-based linter for the mechanical rules of INTERFACES.md.

Each public header is parsed *as C++* (the consumer's view) and its AST is
checked against the rules that can be verified structurally:

  extern-c   Every public function/variable is inside an ``extern "C"`` block
             (section 2 / checklist).
  prefix     Every public symbol carries the module prefix: functions and types
             are ``liara[_module]_...`` (lowercase), enum constants are
             ``LIARA_...`` (uppercase) (section 3).
  fixed-width  No bare int/short/long in public signatures or struct fields;
             fixed-width types only (section 4). ``char`` is allowed (strings),
             ``bool``/``float``/``double`` are allowed.
  out-param  A parameter that is a pointer to non-const data is an output and
             must be named ``out_...`` (section 5). Handle inputs
             (``liara_x_handle*``), ``void*`` passthroughs and function-pointer
             callbacks are excluded.
  includes   No forbidden headers (<stdio.h>, <stdlib.h>, <windows.h>, ...)
             (section 2). Checked lexically.

Usage::

    python3 abi_interface_rules.py --include-dir include --prefix liara \
        --std c++20
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from clang import cindex


def builtin_include_args(compiler: str, extra: list[str]) -> list[str]:
    """Locate the system and builtin headers (stddef.h, stdint.h, ...).

    The PyPI libclang wheel ships the library but not its resource headers, and
    does not reliably add the platform's default search paths. We therefore ask
    a real compiler driver (clang or gcc) for its full include search list.
    Explicit --isystem paths override the auto-detection.
    """
    if extra:
        return [arg for path in extra for arg in ("-isystem", path)]

    resolved = shutil.which(compiler)
    if not resolved:
        return []
    try:
        proc = subprocess.run([resolved, "-E", "-x", "c++", "-v", os.devnull],
                              capture_output=True, text=True)
    except OSError:
        return []

    args: list[str] = []
    capture = False
    for line in proc.stderr.splitlines():
        stripped = line.strip()
        if stripped.startswith("#include <...> search starts here:"):
            capture = True
            continue
        if stripped.startswith("End of search list."):
            break
        if capture and stripped:
            path = stripped.split(" (")[0]
            if Path(path).is_dir():
                args += ["-isystem", path]
    return args

# --- Configuration -----------------------------------------------------------

# Bare (non-fixed-width) integer spellings that are forbidden in signatures and
# fields. `char` is intentionally absent (const char* strings are allowed).
BARE_INT_SPELLINGS = {
    "int", "signed", "signed int", "unsigned", "unsigned int",
    "short", "short int", "signed short", "unsigned short", "short unsigned int",
    "long", "long int", "signed long", "unsigned long", "long unsigned int",
    "long long", "long long int", "signed long long",
    "unsigned long long", "long long unsigned int",
}

FORBIDDEN_INCLUDES = {
    "stdio.h", "stdlib.h", "windows.h", "unistd.h",
    "cstdio", "cstdlib", "cstddef", "cstdint",
    "vulkan.h", "vulkan/vulkan.h",
}

LOWER_SYMBOL_RE = re.compile(r"^liara(_[a-z0-9]+)+$")
UPPER_SYMBOL_RE = re.compile(r"^LIARA(_[A-Z0-9]+)+$")
INCLUDE_RE = re.compile(r'^\s*#\s*include\s*<([^>]+)>')


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    col: int
    rule: str
    message: str


# --- Helpers -----------------------------------------------------------------

def strip_const(spelling: str) -> str:
    spelling = re.sub(r"\bconst\b", "", spelling)
    return re.sub(r"\s+", " ", spelling).strip()


def leaf_type(t: cindex.Type) -> cindex.Type:
    """Peel pointers and arrays down to the underlying element type."""
    seen = 0
    while seen < 32:
        seen += 1
        if t.kind == cindex.TypeKind.POINTER:
            t = t.get_pointee()
        elif t.kind in (cindex.TypeKind.CONSTANTARRAY,
                        cindex.TypeKind.INCOMPLETEARRAY,
                        cindex.TypeKind.VARIABLEARRAY):
            t = t.get_array_element_type()
        else:
            return t
    return t


def bare_int(t: cindex.Type) -> str | None:
    spelling = strip_const(leaf_type(t).spelling)
    return spelling if spelling in BARE_INT_SPELLINGS else None


def is_extern_c(cursor: cindex.Cursor) -> bool:
    """A LINKAGE_SPEC cursor for extern "C" carries a "C" string token."""
    for tok in cursor.get_tokens():
        if tok.spelling == '"C"':
            return True
        if tok.spelling == "{":
            break
    return False


def at(cursor: cindex.Cursor, rule: str, message: str) -> Violation:
    loc = cursor.location
    return Violation(loc.file.name if loc.file else "?", loc.line, loc.column, rule, message)


# --- Rule checks (per declaration) -------------------------------------------

def check_prefix(cursor: cindex.Cursor, out: list[Violation]) -> None:
    name = cursor.spelling
    if not name:
        return
    if cursor.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
        if not UPPER_SYMBOL_RE.match(name):
            out.append(at(cursor, "prefix",
                          f"enum constant '{name}' must be LIARA_UPPER_SNAKE_CASE"))
    else:
        if not LOWER_SYMBOL_RE.match(name):
            out.append(at(cursor, "prefix",
                          f"symbol '{name}' must be lower_snake_case with a 'liara_' prefix"))


def check_fixed_width_type(cursor: cindex.Cursor, t: cindex.Type,
                           what: str, out: list[Violation]) -> None:
    bare = bare_int(t)
    if bare is not None:
        out.append(at(cursor, "fixed-width",
                      f"{what} uses bare '{bare}'; use a fixed-width type (e.g. int32_t)"))


def is_output_candidate(t: cindex.Type) -> bool:
    """A pointer-to-non-const parameter, excluding handle inputs, void* and callbacks."""
    if t.kind != cindex.TypeKind.POINTER:
        return False
    pointee = t.get_pointee()
    if pointee.is_const_qualified():
        return False                                   # const T*  -> input
    canon = pointee.get_canonical()
    if canon.kind == cindex.TypeKind.VOID:
        return False                                   # void*     -> passthrough
    if canon.kind == cindex.TypeKind.FUNCTIONPROTO:
        return False                                   # callback  -> input
    # liara_x_handle* (single pointer) is an input handle; the output form is
    # liara_x_handle** (pointer-to-pointer), whose pointee is itself a pointer.
    if pointee.kind != cindex.TypeKind.POINTER and pointee.spelling.rstrip().endswith("_handle"):
        return False
    return True


def check_function(cursor: cindex.Cursor, out: list[Violation]) -> None:
    check_fixed_width_type(cursor, cursor.result_type, "return type", out)
    for arg in cursor.get_arguments():
        check_fixed_width_type(arg, arg.type, f"parameter '{arg.spelling}'", out)
        name = arg.spelling
        if is_output_candidate(arg.type):
            if not name.startswith("out_"):
                out.append(at(arg, "out-param",
                              f"output parameter '{name}' must be named 'out_{name or '...'}'"))
        elif name.startswith("out_"):
            out.append(at(arg, "out-param",
                          f"parameter '{name}' is prefixed 'out_' but is not an output "
                          f"(non-const) pointer"))


# --- Header traversal --------------------------------------------------------

def in_file(cursor: cindex.Cursor, header: Path) -> bool:
    loc = cursor.location
    return bool(loc.file) and Path(loc.file.name).resolve() == header


def walk(cursor: cindex.Cursor, header: Path, in_extern_c: bool,
         out: list[Violation]) -> None:
    for child in cursor.get_children():
        if not in_file(child, header):
            continue
        kind = child.kind
        if kind == cindex.CursorKind.LINKAGE_SPEC:
            walk(child, header, in_extern_c or is_extern_c(child), out)
        elif kind in (cindex.CursorKind.FUNCTION_DECL, cindex.CursorKind.VAR_DECL):
            if not in_extern_c:
                out.append(at(child, "extern-c",
                              f"'{child.spelling}' must be declared inside an extern \"C\" block"))
            check_prefix(child, out)
            if kind == cindex.CursorKind.FUNCTION_DECL:
                check_function(child, out)
        elif kind in (cindex.CursorKind.STRUCT_DECL, cindex.CursorKind.UNION_DECL,
                      cindex.CursorKind.ENUM_DECL, cindex.CursorKind.TYPEDEF_DECL):
            check_prefix(child, out)
            for field in child.get_children():
                if field.kind == cindex.CursorKind.FIELD_DECL:
                    check_fixed_width_type(field, field.type,
                                           f"field '{field.spelling}'", out)
                elif field.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
                    check_prefix(field, out)
        else:
            walk(child, header, in_extern_c, out)


def check_includes(header: Path, out: list[Violation]) -> None:
    for n, line in enumerate(header.read_text(encoding="utf-8").splitlines(), start=1):
        m = INCLUDE_RE.match(line)
        if m and m.group(1) in FORBIDDEN_INCLUDES:
            out.append(Violation(str(header), n, 1, "includes",
                                 f"forbidden include <{m.group(1)}>"))


# --- Driver ------------------------------------------------------------------

def lint_header(index: cindex.Index, header: Path, args: list[str]) -> list[Violation]:
    tu = index.parse(str(header), args=args,
                     options=cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    violations: list[Violation] = []
    for diag in tu.diagnostics:
        if diag.severity >= cindex.Diagnostic.Error:
            loc = diag.location
            violations.append(Violation(loc.file.name if loc.file else str(header),
                                        loc.line, loc.column, "parse", diag.spelling))
    walk(tu.cursor, header.resolve(), in_extern_c=False, out=violations)
    check_includes(header, violations)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Liara ABI interface-rules linter.")
    parser.add_argument("--include-dir", required=True, type=Path)
    parser.add_argument("--std", default="c++20", help="C++ standard used to parse headers.")
    parser.add_argument("--prefix", default="liara", help="Required symbol prefix (informational).")
    parser.add_argument("--libclang", default=None, help="Path to libclang shared library, if not auto-found.")
    parser.add_argument("--clang", default="clang", help="Compiler used to locate builtin headers.")
    parser.add_argument("--isystem", action="append", default=[],
                        help="Explicit system include dir(s) for builtin headers. Repeatable.")
    args = parser.parse_args()

    if args.libclang:
        cindex.Config.set_library_file(args.libclang)

    include_dir: Path = args.include_dir.resolve()
    if not include_dir.is_dir():
        print(f"::error::include directory not found: {include_dir}", file=sys.stderr)
        return 2

    parse_args = (["-x", "c++", f"-std={args.std}", "-I", str(include_dir)]
                  + builtin_include_args(args.clang, args.isystem))
    index = cindex.Index.create()

    headers = sorted(include_dir.rglob("*.h"))
    if not headers:
        print(f"::error::no headers (*.h) found under {include_dir}", file=sys.stderr)
        return 2

    all_violations: list[Violation] = []
    for header in headers:
        violations = lint_header(index, header, parse_args)
        rel = header.relative_to(include_dir).as_posix()
        if violations:
            print(f"[FAIL] {rel}  ({len(violations)} issue(s))")
            for v in violations:
                print(f"::error file={v.file},line={v.line},col={v.col}::[{v.rule}] {v.message}")
                print(f"    {v.file}:{v.line}:{v.col}  [{v.rule}] {v.message}")
            all_violations.extend(violations)
        else:
            print(f"[ok]   {rel}")

    print()
    print(f"Checked {len(headers)} header(s); {len(all_violations)} issue(s) found.")
    if all_violations:
        return 1
    print("All headers satisfy the interface rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())