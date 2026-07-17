#!/usr/bin/env python3
"""ABI snapshot generator and differ for the Liara interfaces.

``generate`` serializes the public ABI surface of the headers to JSON:
functions (signatures), structs (fields, offsets, size, align), enums
(ordered constants), typedefs, and public object/function-like macros
(``LIARA_*``, excluding ``LIARA_PRIVATE_*`` which change on every release by
design).

``diff`` compares two snapshots and classifies every change according to the
table in INTERFACES.md section 8, then reports the *required version bump*:
none, patch, minor, or major. Notable rules implemented:

  - removing/renaming/retyping anything public ............... MAJOR
  - reordering or retyping struct fields (offset changes) .... MAJOR
  - return type change, EXCEPT void -> liara_result .......... MAJOR (exc: MINOR)
  - appending fields to a *versioned* struct (first field
    named ``struct_version``, existing layout untouched) ..... MINOR
  - adding functions/structs/typedefs/macros ................. MINOR
  - enum constant added at the end ........................... MINOR
  - enum constant added in the middle / value changed ........ MAJOR
  - macro body changed ....................................... MAJOR
  - parameter *name* change only ............................. PATCH (note)

Usage::

    abi_snapshot.py generate --include-dir include --output abi.json
    abi_snapshot.py diff --old base.json --new head.json --summary-out req.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from clang import cindex

LEVELS = ["none", "patch", "minor", "major"]
MACRO_RE = re.compile(r"^\s*#\s*define\s+(LIARA_\w+)(\([^)]*\))?\s*(.*)$")


def builtin_include_args(compiler: str, extra: list[str]) -> list[str]:
    args = [a for path in extra for a in ("-isystem", path)]
    resolved = shutil.which(compiler)
    if not resolved:
        return args
    try:
        proc = subprocess.run([resolved, "-E", "-x", "c++", "-v", os.devnull],
                              capture_output=True, text=True)
    except OSError:
        return args
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


# --- snapshot generation ------------------------------------------------------

def collect_macros(header: Path, macros: dict) -> None:
    """Lexical #define extraction, handling backslash continuations."""
    raw = header.read_text(encoding="utf-8").splitlines()
    logical: list[str] = []
    buffer = ""
    for line in raw:
        if line.rstrip().endswith("\\"):
            buffer += line.rstrip()[:-1] + " "
            continue
        logical.append(buffer + line)
        buffer = ""
    if buffer:
        logical.append(buffer)
    for line in logical:
        m = MACRO_RE.match(line)
        if not m:
            continue
        name, params, body = m.group(1), m.group(2), m.group(3)
        if name.startswith("LIARA_PRIVATE_"):
            continue
        macros[name] = {"params": params or None,
                        "body": re.sub(r"\s+", " ", body).strip()}


def snapshot(include_dir: Path, parse_args: list[str]) -> dict:
    index = cindex.Index.create()
    snap = {"functions": {}, "structs": {}, "enums": {},
            "enum_constants": {}, "typedefs": {}, "macros": {}}

    for header in sorted(include_dir.rglob("*.h")):
        collect_macros(header, snap["macros"])
        tu = index.parse(str(header), args=parse_args,
                         options=cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
        resolved = header.resolve()
        for cursor in tu.cursor.walk_preorder():
            loc = cursor.location
            if not (loc.file and Path(loc.file.name).resolve() == resolved):
                continue

            if cursor.kind == cindex.CursorKind.FUNCTION_DECL:
                snap["functions"][cursor.spelling] = {
                    "return": cursor.result_type.spelling,
                    "params": [{"name": a.spelling, "type": a.type.spelling}
                               for a in cursor.get_arguments()],
                    "variadic": cursor.type.is_function_variadic(),
                }

            elif cursor.kind in (cindex.CursorKind.STRUCT_DECL,
                                 cindex.CursorKind.UNION_DECL):
                if not cursor.is_definition() or cursor.is_anonymous():
                    continue
                t = cursor.type
                if t.get_size() <= 0 or t.spelling in snap["structs"]:
                    continue
                fields = [{"name": f.spelling, "type": f.type.spelling,
                           "offset": f.get_field_offsetof() // 8}
                          for f in cursor.get_children()
                          if f.kind == cindex.CursorKind.FIELD_DECL]
                snap["structs"][t.spelling] = {
                    "size": t.get_size(), "align": t.get_align(),
                    "fields": fields,
                    "versioned": bool(fields) and fields[0]["name"] == "struct_version",
                }

            elif cursor.kind == cindex.CursorKind.ENUM_DECL and cursor.is_definition():
                constants = [(c.spelling, c.enum_value)
                             for c in cursor.get_children()
                             if c.kind == cindex.CursorKind.ENUM_CONSTANT_DECL]
                if cursor.is_anonymous():
                    snap["enum_constants"].update(dict(constants))
                else:
                    snap["enums"][cursor.spelling] = constants

            elif cursor.kind == cindex.CursorKind.TYPEDEF_DECL:
                underlying = cursor.underlying_typedef_type.spelling
                # typedef struct X X: covered by the struct entry, keep anyway
                snap["typedefs"][cursor.spelling] = underlying
    return snap


# --- diff and classification --------------------------------------------------

class Diff:
    def __init__(self) -> None:
        self.changes: list[tuple[str, str]] = []

    def add(self, level: str, message: str) -> None:
        self.changes.append((level, message))

    @property
    def required(self) -> str:
        idx = max((LEVELS.index(lvl) for lvl, _ in self.changes), default=0)
        return LEVELS[idx]


def diff_dicts(diff: Diff, kind: str, old: dict, new: dict,
               removed_level: str = "major", added_level: str = "minor"):
    """Yields common keys; records added/removed entries."""
    for name in sorted(old.keys() - new.keys()):
        diff.add(removed_level, f"{kind} '{name}' removed")
    for name in sorted(new.keys() - old.keys()):
        diff.add(added_level, f"{kind} '{name}' added")
    return sorted(old.keys() & new.keys())


def diff_functions(diff: Diff, old: dict, new: dict) -> None:
    for name in diff_dicts(diff, "function", old, new):
        o, n = old[name], new[name]
        o_types = [p["type"] for p in o["params"]]
        n_types = [p["type"] for p in n["params"]]
        if o_types != n_types or o["variadic"] != n["variadic"]:
            diff.add("major", f"function '{name}' parameter types changed "
                              f"({o_types} -> {n_types})")
        else:
            for op, np in zip(o["params"], n["params"]):
                if op["name"] != np["name"]:
                    diff.add("patch", f"function '{name}' parameter renamed "
                                      f"'{op['name']}' -> '{np['name']}'")
        if o["return"] != n["return"]:
            if o["return"] == "void" and n["return"] == "liara_result":
                diff.add("minor", f"function '{name}' return void -> liara_result "
                                  f"(newly fallible, allowed as MINOR)")
            else:
                diff.add("major", f"function '{name}' return type changed "
                                  f"'{o['return']}' -> '{n['return']}'")


def diff_structs(diff: Diff, old: dict, new: dict) -> None:
    for name in diff_dicts(diff, "struct", old, new):
        o, n = old[name], new[name]
        o_fields = [(f["name"], f["type"], f["offset"]) for f in o["fields"]]
        n_fields = [(f["name"], f["type"], f["offset"]) for f in n["fields"]]
        if o_fields == n_fields:
            if (o["size"], o["align"]) != (n["size"], n["align"]):
                diff.add("major", f"struct '{name}' size/align changed "
                                  f"{o['size']}/{o['align']} -> {n['size']}/{n['align']}")
            continue
        appended = (len(n_fields) > len(o_fields)
                    and n_fields[:len(o_fields)] == o_fields)
        if appended and o["versioned"]:
            extra = [f[0] for f in n_fields[len(o_fields):]]
            diff.add("minor", f"versioned struct '{name}' extended with {extra} "
                              f"(appended, existing layout untouched)")
        elif appended:
            diff.add("major", f"struct '{name}' grew (fields appended to a "
                              f"non-versioned struct changes sizeof)")
        else:
            diff.add("major", f"struct '{name}' fields changed "
                              f"(removed/renamed/retyped/reordered)")


def diff_enums(diff: Diff, old: dict, new: dict) -> None:
    for name in diff_dicts(diff, "enum", old, new):
        o, n = [tuple(c) for c in old[name]], [tuple(c) for c in new[name]]
        if o == n:
            continue
        if len(n) > len(o) and n[:len(o)] == o:
            extra = [c[0] for c in n[len(o):]]
            diff.add("minor", f"enum '{name}' constants appended: {extra}")
        else:
            diff.add("major", f"enum '{name}' constants removed, reordered, "
                              f"revalued, or inserted mid-enum")


def diff_flat_values(diff: Diff, kind: str, old: dict, new: dict) -> None:
    for name in diff_dicts(diff, kind, old, new):
        if old[name] != new[name]:
            diff.add("major", f"{kind} '{name}' changed "
                              f"'{old[name]}' -> '{new[name]}'")


def diff_macros(diff: Diff, old: dict, new: dict) -> None:
    for name in diff_dicts(diff, "macro", old, new):
        if old[name] != new[name]:
            diff.add("major", f"macro '{name}' value/signature changed")


def run_diff(old: dict, new: dict) -> Diff:
    diff = Diff()
    diff_functions(diff, old["functions"], new["functions"])
    diff_structs(diff, old["structs"], new["structs"])
    diff_enums(diff, old["enums"], new["enums"])
    diff_flat_values(diff, "enum constant", old["enum_constants"], new["enum_constants"])
    diff_flat_values(diff, "typedef", old["typedefs"], new["typedefs"])
    diff_macros(diff, old["macros"], new["macros"])
    return diff


# --- CLI ----------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Liara ABI snapshot / diff.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--include-dir", required=True, type=Path)
    gen.add_argument("--output", required=True, type=Path)
    gen.add_argument("--std", default="c++20")
    gen.add_argument("--clang", default="clang")
    gen.add_argument("--isystem", action="append", default=[])
    gen.add_argument("--include-extra", action="append", default=[],
                     help="Additional -I dirs (e.g. the CMake-generated headers).")
    gen.add_argument("--libclang", default=None)

    dif = sub.add_parser("diff")
    dif.add_argument("--old", required=True, type=Path)
    dif.add_argument("--new", required=True, type=Path)
    dif.add_argument("--summary-out", type=Path, default=None,
                     help="Write the required bump (none|patch|minor|major) to this file.")

    args = parser.parse_args()

    if args.cmd == "generate":
        if args.libclang:
            cindex.Config.set_library_file(args.libclang)
        include_dir = args.include_dir.resolve()
        if not include_dir.is_dir():
            print(f"::error::include directory not found: {include_dir}", file=sys.stderr)
            return 2
        parse_args = ["-x", "c++", f"-std={args.std}", "-I", str(include_dir)]
        for extra in args.include_extra:
            parse_args += ["-I", extra]
        parse_args += builtin_include_args(args.clang, args.isystem)
        snap = snapshot(include_dir, parse_args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        counts = {k: len(v) for k, v in snap.items()}
        print(f"Wrote {args.output}: {counts}")
        return 0

    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))
    diff = run_diff(old, new)

    if not diff.changes:
        print("No ABI surface changes detected.")
    else:
        for level, message in sorted(diff.changes, key=lambda c: -LEVELS.index(c[0])):
            print(f"[{level.upper():5}] {message}")
    print()
    print(f"Required version bump: {diff.required.upper()}")

    if args.summary_out:
        args.summary_out.write_text(diff.required + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())