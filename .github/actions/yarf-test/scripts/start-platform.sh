#!/bin/bash
# Start the platform YARF will run against.
#
# For the built-in Mir/Vnc providers this starts a virtual Mir compositor
# (no graphics hardware required) at the requested resolution, waits for the
# Wayland socket to appear and, for Vnc, also starts wayvnc. WAYLAND_DISPLAY
# is exported to $GITHUB_ENV so later steps inherit it. For the custom provider
# it runs the caller-supplied setup and readiness commands instead.
#
# Environment:
#   PLATFORM_PROVIDER        Mir, Vnc, or custom (default: Mir).
#   DISPLAY_SIZE             Virtual output resolution (default: 1280x1024).
#   PLATFORM_SETUP_COMMAND   Command(s) to start a custom platform.
#   PLATFORM_READY_COMMAND   Command(s) that block until a custom platform is ready.
#   GITHUB_ENV               File used to export variables to later steps.
set -euo pipefail

PLATFORM_PROVIDER="${PLATFORM_PROVIDER:-Mir}"
DISPLAY_SIZE="${DISPLAY_SIZE:-1280x1024}"

case "${PLATFORM_PROVIDER}" in
Mir | Vnc)
  export WAYLAND_DISPLAY="wayland-99"

  # Start Mir on a virtual display (doesn't require graphics hardware).
  mir-test-tools.demo-server \
    --add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 \
    --platform-display-libs mir:virtual \
    --virtual-output "${DISPLAY_SIZE}" &

  # Bounded wait so a failed compositor startup surfaces as a clear timeout
  # instead of hanging the workflow.
  if ! inotifywait --timeout 60 --event create \
      --include "^${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}\$" "${XDG_RUNTIME_DIR}"; then
    echo "Timed out waiting for Mir Wayland socket at ${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}" >&2
    exit 1
  fi

  if [ "${PLATFORM_PROVIDER}" = "Vnc" ]; then
    wayvnc &
  fi

  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY}" >> "${GITHUB_ENV}"
  ;;
custom)
  if [ -n "${PLATFORM_SETUP_COMMAND:-}" ]; then
    echo "Running platform setup command"
    bash -c "${PLATFORM_SETUP_COMMAND}"
  fi
  if [ -n "${PLATFORM_READY_COMMAND:-}" ]; then
    echo "Running platform ready command"
    bash -c "${PLATFORM_READY_COMMAND}"
  fi
  ;;
*)
  echo "Unknown platform-provider: '${PLATFORM_PROVIDER}' (expected Mir, Vnc, or custom)" >&2
  exit 1
  ;;
esac
