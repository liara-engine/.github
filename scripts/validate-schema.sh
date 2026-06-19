#!/usr/bin/env bash
set -euo pipefail

# Centralized JSON Schema Validation Script
# Usage: ./validate-schema.sh <path_to_json_file>

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <json_file>" >&2
    exit 1
fi

JSON_FILE="$1"

if [ ! -f "$JSON_FILE" ]; then
    echo "ERROR: File not found: $JSON_FILE" >&2
    exit 1
fi

SCHEMA_URL=""
if command -v jq &> /dev/null; then
    SCHEMA_URL=$(jq -r '."$schema" // empty' "$JSON_FILE")
else
    SCHEMA_URL=$(grep -oP '"\$schema"\s*:\s*"\K[^"]+' "$JSON_FILE" || true)
fi

if [ -z "${SCHEMA_URL}" ]; then
    echo "ERROR: $JSON_FILE does not declare a \$schema" >&2
    exit 2
fi

if [ -z "${SCHEMA_CACHE_DIR:-}" ]; then
    CACHE_DIR=$(mktemp -d)
    trap 'rm -rf "$CACHE_DIR"' EXIT
else
    CACHE_DIR="$SCHEMA_CACHE_DIR"
fi

SCHEMA_HASH=$(echo -n "${SCHEMA_URL}" | md5sum | cut -d' ' -f1)
CACHED_SCHEMA="${CACHE_DIR}/${SCHEMA_HASH}.json"

if [ ! -f "${CACHED_SCHEMA}" ]; then
    if ! curl -fsSL "${SCHEMA_URL}" -o "${CACHED_SCHEMA}"; then
        echo "ERROR: Failed to download schema from ${SCHEMA_URL}" >&2
        exit 3
    fi
fi

if ! npx ajv validate -s "${CACHED_SCHEMA}" -d "${JSON_FILE}" --strict=true; then
    exit 4
fi