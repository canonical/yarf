#!/bin/bash
set -euo pipefail

SUITE=${1:?usage: run-keyword-suite.sh <suite-name>}
LISTENER=${KEYWORDS_LISTENER_PATH:-.github/scripts/yarf/keywords_listener.py}

run_yarf() {
  uv run yarf --platform Mir tests/keyword_suite -- \
    --suite "$SUITE" --listener "$LISTENER" "$@"
}

case "$SUITE" in
  hid_keyboard_test|hid_pointer_test)
    export WAYLAND_DEBUG=client
    run_yarf 2> ~/wayland.trace
    ;;
  llm_client_test)
    python3 tests/keyword_suite/server/llm_stub_server.py &
    STUB_PID=$!
    trap 'kill "$STUB_PID" 2>/dev/null || true' EXIT
    run_yarf
    ;;
  *)
    run_yarf
    ;;
esac
