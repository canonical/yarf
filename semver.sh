#!/usr/bin/env bash
set -euo pipefail

echo "Running GitVersion..." >&2
if ! JSON=$(docker run --rm -v "$(pwd):/repo" gittools/gitversion:6.4.0-ubuntu.24.04-8.0 /repo 2>&1); then
    echo "ERROR: GitVersion failed:" >&2
    echo "$JSON" >&2
    exit 1
fi

echo "For Debugging only:" >&2
echo "$JSON" >&2
echo "-----" >&2

echo "$JSON" | jq -r '.SemVer'
