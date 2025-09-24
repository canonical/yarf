#!/bin/bash
set -euo pipefail

COMMIT_SHA="$1"
COMMIT_SHA_SHORT="$2"
OUTPUT_FILE="yarf/_commit_sha.py"

echo "Adding commit SHA to snap..."
cat > "$OUTPUT_FILE" << EOF
COMMIT_SHA = "$COMMIT_SHA"
COMMIT_SHA_SHORT = "$COMMIT_SHA_SHORT"
EOF
