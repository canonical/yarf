#!/bin/bash
set -euo pipefail

export WAYLAND_DISPLAY=wayland-99

# Start Mir on a virtual display (doesn't require graphics hardware)
mir-test-tools.demo-server \
  --add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 \
  --platform-display-libs mir:virtual \
  --virtual-output 1280x1024 &

# Wait for the compositor to start. Bounded so a failed Mir startup
# surfaces as a clear timeout instead of hanging the workflow.
if ! inotifywait --timeout 60 --event create \
    --include "^$XDG_RUNTIME_DIR/wayland-99\$" "$XDG_RUNTIME_DIR"; then
  echo "Timed out waiting for Mir Wayland socket at $XDG_RUNTIME_DIR/wayland-99" >&2
  exit 1
fi

# Persist the variable for all future steps
echo "WAYLAND_DISPLAY=wayland-99" >> "$GITHUB_ENV"
