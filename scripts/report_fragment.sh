#!/usr/bin/env bash
# Write one CI report fragment. Every workflow that wants to appear in the pull request comment
# calls this instead of hand-rolling the same twelve lines of jq-free JSON.
set -euo pipefail

section_order=1; section_name="Checks"
step_order=1;    step_name="Step"
leg=""; status=""; log=""; summary=""; out="ci-report"

while [ $# -gt 0 ]; do
  case "$1" in
    --section)      section_order="$2"; shift 2 ;;
    --section-name) section_name="$2";  shift 2 ;;
    --step)         step_order="$2";    shift 2 ;;
    --step-name)    step_name="$2";     shift 2 ;;
    --leg)          leg="$2";           shift 2 ;;
    --status)       status="$2";        shift 2 ;;
    --log)          log="$2";           shift 2 ;;
    --summary)      summary="$2";       shift 2 ;;
    --out)          out="$2";           shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$out"
[ -n "$log" ] && [ -f "$log" ] && cp "$log" "$out/log.txt" || echo "(no log captured)" > "$out/log.txt"

state="failure"
[ "$status" = "0" ] || [ "$status" = "success" ] && state="success"

python3 - "$out/meta.json" << PY
import json, sys
json.dump({
    "section": {"order": $section_order, "name": """$section_name"""},
    "step":    {"order": $step_order,    "name": """$step_name"""},
    "leg": """$leg""", "status": "$state", "summary": """$summary""",
}, open(sys.argv[1], "w"), indent=2)
PY