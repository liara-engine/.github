#!/usr/bin/env python3
"""Resolve which liara-interfaces ref a repository should be built against.

A module states, in ``manifest.json`` (schema v2) and per version of itself, the ABI versions it
is written against. *Which* of its versions to ask about is the caller's business rather than this
script's guess: a branch build wants ``dev``, a build of the released line wants ``latest``, and
the two routinely disagree -- the ABI moves first and the modules catch up afterwards, which is
the normal direction of travel. Guessing wrong is what forced callers to override the result.

Usage::

    resolve_module_refs.py --repo-dir . --version dev
    resolve_module_refs.py --repo-dir . --version latest
    resolve_module_refs.py --repo-dir . --version 0.3.1
    resolve_module_refs.py --repo-dir . --artifact launcher --version dev

A repository whose own ``kind`` declares no ABI (``contract``, ``infrastructure``) can still
publish something that does: ``liara`` is infrastructure, and its launcher's compatibility lives
in the ``launcher`` artifact. That is what --artifact selects.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCHEMA_URL = "https://liara-engine.github.io/liara/schemas/module-manifest-v2.schema.json"

DEV = "dev"
VERSION_RE = re.compile(r"^(?:dev|\d+\.\d+\.\d+)$")

# Kinds whose own versions are not built against an ABI: a contract's versions *are* the ABI, and
# infrastructure has no ABI relation at all.
ABI_LESS_KINDS = ("contract", "infrastructure")


class ResolutionError(Exception):
    """The manifest cannot answer the question that was asked of it."""


@dataclass(frozen=True)
class Table:
    """One version line: the repository's own, or one of its artifacts'."""

    versions: dict
    latest: str
    label: str


def version_key(text: str) -> tuple:
    """Sort key over manifest version strings. ``dev`` ranks above every numbered version, being
    the one still being written; a malformed key ranks below everything rather than raising, so an
    error message can still list what the manifest holds."""
    if text == DEV:
        return (2,)
    if VERSION_RE.match(text):
        return (1,) + tuple(int(part) for part in text.split("."))
    return (0, text)


def known(versions) -> str:
    return ", ".join(sorted(versions, key=version_key)) or "none"


def load_manifest(repo_dir: Path) -> dict:
    path = repo_dir / "manifest.json"
    if not path.is_file():
        raise ResolutionError(f"no manifest.json in {repo_dir}")

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ResolutionError(f"manifest.json is not valid JSON: {error}") from error

    generation = manifest.get("manifest_version")
    if generation != 2:
        raise ResolutionError(
            f"manifest.json is not a v2 manifest (manifest_version: {generation!r}, expected 2). "
            f"See {SCHEMA_URL}"
        )
    return manifest


def version_table(manifest: dict, artifact: str) -> Table:
    metadata = manifest.get("metadata") or {}
    repo = metadata.get("repo") or "this repository"

    if artifact:
        artifacts = manifest.get("artifacts") or {}
        entry = artifacts.get(artifact)
        if entry is None:
            listed = ", ".join(sorted(artifacts)) or "none"
            raise ResolutionError(f"{repo} declares no artifact '{artifact}' (declares: {listed})")

        versions = entry.get("versions") or {}
        # An artifact carries no `latest` of its own in the schema, so `latest` means the newest
        # version it has released.
        numbered = [v for v in versions if v != DEV and VERSION_RE.match(v)]
        latest = max(numbered, key=version_key) if numbered else ""
        return Table(versions, latest, f"{repo} artifact '{artifact}'")

    kind = manifest.get("kind")
    if kind in ABI_LESS_KINDS:
        raise ResolutionError(
            f"{repo} is kind '{kind}', which declares no ABI target of its own. Name the artifact "
            "that does with --artifact, or do not resolve an interfaces ref for this repository."
        )

    return Table(manifest.get("versions") or {}, metadata.get("latest") or "", repo)


def select_version(table: Table, wanted: str) -> tuple[str, object]:
    """Return (version, entry) for the version asked for, `latest` resolved through the manifest."""
    if wanted == "latest":
        if not table.latest:
            raise ResolutionError(f"{table.label} names no latest version")
        version = table.latest
    else:
        version = wanted

    entry = table.versions.get(version)
    if entry is None:
        where = f"'latest' names {version}, which is" if wanted == "latest" else f"version {version} is"
        raise ResolutionError(f"{where} absent from {table.label} (holds: {known(table.versions)})")

    return version, entry


def abi_anchors(entry: object, where: str) -> tuple[list[str], str]:
    """The ABI versions a version entry is written against, in any of the schema's three forms:
    a bare version, an array of them, or an object carrying them under `abi`."""
    note = ""
    if isinstance(entry, dict):
        note = str(entry.get("note") or "")
        target = entry.get("abi")
    else:
        target = entry

    if target is None:
        raise ResolutionError(f"{where} declares no abi target")

    anchors = [target] if isinstance(target, str) else list(target)
    if not anchors:
        raise ResolutionError(f"{where} declares an empty abi target")

    for anchor in anchors:
        if not isinstance(anchor, str) or not VERSION_RE.match(anchor):
            raise ResolutionError(f"{where} declares {anchor!r}, which is not a version or 'dev'")

    return anchors, note


def resolve(repo_dir: Path, wanted: str, artifact: str) -> tuple[str, str]:
    """Return (abi anchor, explanation) for the version line and version asked for."""
    manifest = load_manifest(repo_dir)
    table = version_table(manifest, artifact)
    version, entry = select_version(table, wanted)
    anchors, note = abi_anchors(entry, f"{table.label} {version}")

    # Several anchors mean the version is claimed to work under each of them, which only happens
    # across majors. One ref has to be built against: the newest of them, `dev` counting as newer
    # than any released ABI.
    anchor = max(anchors, key=version_key)

    explanation = f"{table.label} {version} targets ABI {anchor}"
    if len(anchors) > 1:
        explanation += f" (newest of {', '.join(anchors)})"
    if note:
        explanation += f" -- {note}"
    return anchor, explanation


def tag_exists(owner: str, tag: str) -> bool:
    url = f"https://github.com/{owner}/liara-interfaces.git"
    result = subprocess.run(["git", "ls-remote", "--tags", "--exit-code", url, tag],
                            capture_output=True, text=True)
    return result.returncode == 0


def ref_for(anchor: str, owner: str) -> tuple[str, str]:
    """Turn an ABI anchor into a liara-interfaces ref."""
    if anchor == DEV:
        return "main", "the ABI still being written"

    tag = f"v{anchor}"
    if tag_exists(owner, tag):
        return tag, ""
    # The only legitimate fallback: an ABI can be declared before it is released. Every other way
    # of failing to resolve is an error, because building against main instead is a green build of
    # something other than what the manifest declares.
    return "main", f"{tag} is not tagged yet, falling back to main"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-dir", required=True, type=Path)
    parser.add_argument("--version", default=DEV,
                        help="Version of this repository to read the ABI target of: 'dev', "
                             "'latest', or an explicit X.Y.Z. Defaults to dev.")
    parser.add_argument("--artifact", default="",
                        help="Resolve within this artifact's version line instead of the "
                             "repository's own, e.g. 'launcher' in the liara manifest.")
    parser.add_argument("--owner", default="liara-engine")
    parser.add_argument("--override", default="", help="Explicit ref; bypasses resolution entirely.")
    parser.add_argument("--github-output", type=Path)
    # Accepted and unused. Callers pinned to an older tag of this repository still run this script
    # from the default branch, so removing an argument they pass would break them mid-flight.
    parser.add_argument("--module", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.override:
        ref, note = args.override, f"explicit override: {args.override}"
    else:
        try:
            anchor, note = resolve(args.repo_dir, args.version or DEV, args.artifact)
        except ResolutionError as error:
            print(f"::error::cannot resolve the interfaces ref: {error}", file=sys.stderr)
            return 1

        ref, extra = ref_for(anchor, args.owner)
        if extra:
            note = f"{note}; {extra}"

    print(f"interfaces ref: {ref}  ({note})")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"interfaces-ref={ref}\n")
            handle.write(f"interfaces-note={note}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
