#!/bin/bash
set -euo pipefail

GITHUB_REF_NAME="$1"
SEMVER="$2"
INFORMATIONAL_VERSION="$3"

echo "Normalizing version for PEP 440 compliance..."

if [[ "$GITHUB_REF_NAME" == "main" ]]; then
  VERSION="$SEMVER"
  echo "Using semVer for main branch: $VERSION"
else
  VERSION="$INFORMATIONAL_VERSION"
  echo "Using informationalVersion for feature branch: $VERSION"
fi

VERSION_PEP440=$(uv tool run --with packaging python -c "from packaging.version import Version; print(Version('$VERSION'))")
echo "Normalized PEP 440 version: $VERSION_PEP440"

echo "version=$VERSION_PEP440" >> "$GITHUB_OUTPUT"
