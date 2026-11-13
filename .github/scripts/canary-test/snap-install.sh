#!/bin/bash
# Install a snap, retrying on transient Snap Store errors such as HTTP 408.
# Usage: snap-install.sh <snap> [snap install options...]
set -euo pipefail

for attempt in 1 2 3; do
    if sudo snap install "$@"; then
        exit 0
    fi
    echo "snap install $* failed (attempt ${attempt}/3), retrying in 30 seconds"
    sleep 30
done

echo "snap install $* failed after 3 attempts" >&2
exit 1
