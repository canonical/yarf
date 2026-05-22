#!/bin/bash
set -euo pipefail

SUITE=${1:?usage: run-keyword-suite.sh <suite-name>}
LISTENER=${KEYWORDS_LISTENER_PATH:-.github/scripts/yarf/keywords_listener.py}
MAX_ATTEMPTS=${KEYWORD_SUITE_MAX_ATTEMPTS:-3}

sudo apt-get update -qq
sudo apt-get --yes --no-install-recommends install eog mpv

# asttokens is imported by the keywords listener, which runs inside
# the yarf uv-managed venv. `uv run --with` makes uv add the
# dependency to that runtime environment.
run_yarf() {
  uv run --with asttokens yarf --platform Mir tests/keyword_suite -- \
    --suite "$SUITE" --listener "$LISTENER" "$@"
}

attempt_suite() {
  # Fresh coverage file each attempt: the listener loads the existing
  # file and removes used keywords from it, so leftover state from a
  # partial previous attempt would skew the result.
  rm -f keywords_coverage.json

  case "$SUITE" in
    hid_keyboard_test|hid_pointer_test)
      WAYLAND_DEBUG=client run_yarf 2> ~/wayland.trace
      ;;
    llm_client_test)
      python3 tests/keyword_suite/server/llm_stub_server.py &
      local stub_pid=$!
      local ec=0
      run_yarf || ec=$?
      kill "$stub_pid" 2>/dev/null || true
      return $ec
      ;;
    *)
      run_yarf
      ;;
  esac
}

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if attempt_suite; then
    if [ "$attempt" -gt 1 ]; then
      echo "::notice::Keyword suite '$SUITE' passed on attempt $attempt/$MAX_ATTEMPTS"
    fi
    exit 0
  fi
  echo "::warning::Keyword suite '$SUITE' failed on attempt $attempt/$MAX_ATTEMPTS"
done

echo "::error::Keyword suite '$SUITE' failed after $MAX_ATTEMPTS attempts"
exit 1
