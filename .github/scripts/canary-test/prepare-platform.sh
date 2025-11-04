#!/bin/bash
set -euo pipefail

PLATFORM="$1"

export WAYLAND_DISPLAY=wayland-99
export WAYLAND_DEBUG=client

# Start Mir on a virtual display (doesn't require graphics hardware)
mir-test-tools.demo-server \
--add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 \
--platform-display-libs mir:virtual \
--virtual-output 1280x1024 &

# Wait for the compositor to start
inotifywait --event create --include "^$XDG_RUNTIME_DIR/wayland-99\$" $XDG_RUNTIME_DIR

if [ "$PLATFORM" == "Vnc" ]; then
    # Start vnc session
    wayvnc &
fi
