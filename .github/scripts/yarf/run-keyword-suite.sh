#!/bin/bash
set -euo pipefail

SUITE=${1:?usage: run-keyword-suite.sh <suite-name>}
LISTENER=${KEYWORDS_LISTENER_PATH:-.github/scripts/yarf/keywords_listener.py}

# Fresh coverage file on every invocation: the listener loads the
# existing file and removes used keywords from it, so leftover state
# from a previous (failed) attempt would skew the result.
rm -f keywords_coverage.json

# asttokens is imported by the keywords listener, which runs inside
# the yarf uv-managed venv. `uv run --with` makes uv add the
# dependency to that runtime environment.
run_yarf() {
  uv run --with asttokens yarf --platform Mir tests/keyword_suite -- \
    --suite "$SUITE" --listener "$LISTENER" "$@"
}

case "$SUITE" in
  hid_keyboard_test|hid_pointer_test)
    WAYLAND_DEBUG=client run_yarf 2> ~/wayland.trace
    ;;
  llm_client_test)
    python3 tests/keyword_suite/server/llm_stub_server.py &
    STUB_PID=$!
    trap 'kill "$STUB_PID" 2>/dev/null || true' EXIT
    run_yarf
    ;;
  grid_test)
    # The grid app is a GTK4/libadwaita application managed by uv; install its
    # system GObject bindings and create its venv with access to them,
    # mirroring the tutorial tests setup.
    sudo apt-get --yes --no-install-recommends install \
      python3-gi \
      gir1.2-gtk-4.0 \
      libadwaita-1-dev \
      gir1.2-adw-1
    uv venv --python=/usr/bin/python3 --system-site-packages \
      --project="$(pwd)/tests/keyword_suite/grid"
    run_yarf
    ;;
  *)
    run_yarf
    ;;
esac
