#!/bin/bash
set -euo pipefail

PLATFORM="$1"

export WAYLAND_DISPLAY="$2"
export WAYLAND_DEBUG=client

# Start Mir on a virtual display (doesn't require graphics hardware)
mir-test-tools.demo-server \
--add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 \
--platform-display-libs mir:virtual \
--virtual-output 1280x1024 &

# Wait for the compositor to start
inotifywait --event create --include "^$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY\$" "$XDG_RUNTIME_DIR"

if [ "$PLATFORM" == "Vnc" ]; then
    # Start vnc session
    wayvnc &
    wayvncctl --wait version > /dev/null

    # Work around wayvnc exiting when it restarts its capture between YARF's
    # connections: https://github.com/any1/wayvnc/issues/401
    # The holder uses YARF's vendored asyncvnc, so run it with the snap's
    # Python, then wait until wayvnc lists it as a client.
    holder="$(realpath "$(dirname "$0")/hold_vnc_connection.py")"
    snap run --shell yarf -c "\"\$SNAP/bin/python3\" $(printf '%q' "$holder")" &
    timeout 60 bash -c \
        'until wayvncctl --json client-list | jq -e "length > 0" > /dev/null; do sleep 0.5; done'
fi
