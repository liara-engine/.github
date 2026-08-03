#!/usr/bin/env python3
"""Render the CI pipeline sticky PR comment from per-step artifacts.

Each step of the CI pipeline uploads one artifact per matrix leg, laid out as::

    <reports-dir>/<artifact-name>/
        meta.json   # {"order": 1, "step": "Header portability", "leg": "...", "status": "success|failure"}
        log.txt     # captured output for that leg

This script is deliberately step-agnostic: it discovers whatever artifacts are
present, groups them by (order, step), and renders a summary table plus a
foldable <details> block per step. Adding a new pipeline step therefore needs
no change here -- the new step just uploads artifacts in the same shape.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

PASS_ICON = "PASS"
FAIL_ICON = "FAIL"

# Keep the comment comfortably under GitHub's 65536-char limit.
MAX_LOG_CHARS = 6000


@dataclass
class Leg:
    name: str
    status: str
    log: str
    summary: str = ""

    @property
    def icon(self) -> str:
        return PASS_ICON if self.status == "success" else FAIL_ICON


@dataclass
class Step:
    order: int
    name: str
    legs: list[Leg] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(leg.status == "success" for leg in self.legs)

    @property
    def icon(self) -> str:
        return PASS_ICON if self.ok else FAIL_ICON


def load_steps(reports_dir: Path) -> dict[tuple[int, str], list[Step]]:
    """Group fragments by section, then by step, accepting both meta.json shapes."""
    sections: dict[tuple[int, str], dict[tuple[int, str], Step]] = {}
    for meta_path in sorted(reports_dir.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        if "section" in meta:
            sec_key = (int(meta["section"]["order"]), str(meta["section"]["name"]))
            step_key = (int(meta["step"]["order"]), str(meta["step"]["name"]))
        else:
            # Legacy flat shape
            sec_key = (1, "ABI")
            step_key = (int(meta["order"]), str(meta["step"]))

        log_path = meta_path.with_name("log.txt")
        log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        step = sections.setdefault(sec_key, {}).setdefault(step_key, Step(order=step_key[0], name=step_key[1]))
        step.legs.append(Leg(str(meta.get("leg", "")), str(meta["status"]), log, str(meta.get("summary", ""))))

    return {sec: [steps[k] for k in sorted(steps)] for sec, steps in sorted(sections.items())}


def truncate(log: str) -> str:
    log = log.rstrip()
    if len(log) <= MAX_LOG_CHARS:
        return log or "(no output)"
    return "... (truncated, see the full run)\n" + log[-MAX_LOG_CHARS:]


def render(title: str, steps: list[Step], run_url: str) -> str:
    out: list[str] = [f"## {title}", ""]

    if not steps:
        out += ["No CI checks reported for this run.", "",
                f"<sub>[Full run]({run_url}) - updates automatically on each push.</sub>"]
        return "\n".join(out)

    failing = [s for s in steps if not s.ok]
    headline = (f"**{len(failing)} check(s) need attention.**"
                if failing else "**All CI checks passed.**")
    out += [f"{headline} - [full run]({run_url})", ""]

    out += ["| Step | Result |", "| --- | :---: |"]
    out += [f"| {s.order}. {s.name} | {s.icon} |" for s in steps]
    out.append("")

    for s in steps:
        open_attr = " open" if not s.ok else ""
        out += [f"<details{open_attr}>", f"<summary>{s.order}. {s.name} &mdash; {s.icon}</summary>", ""]
        for leg in sorted(step.legs, key=lambda leg: leg.name):
            if leg.status == "success":
                out.append(f"- **{leg.name}** &mdash; {leg.icon}" + (f" &middot; {leg.summary}" if leg.summary else ""))
            else:
                out += [f"- **{leg.name}** &mdash; {leg.icon}" + (f" &middot; {leg.summary}" if leg.summary else ""),
                        "", "```", truncate(leg.log), "```", ""]
        out += ["</details>", ""]

    out.append("<sub>Updates automatically on each push to this PR.</sub>")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the CI pipeline sticky PR comment.")
    parser.add_argument("--reports-dir", required=True, type=Path)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default="CI pipeline report")
    args = parser.parse_args()

    steps = load_steps(args.reports_dir) if args.reports_dir.is_dir() else []
    body = render(args.title, steps, args.run_url)
    args.output.write_text(body + "\n", encoding="utf-8")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())