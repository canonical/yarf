#!/bin/bash
set -euo pipefail

VARIANT=${1:-}
MAX_ATTEMPTS=${TUTORIAL_TEST_MAX_ATTEMPTS:-3}

# shellcheck source=.github/scripts/yarf/_retry.sh
. "$(dirname "$0")/_retry.sh"

sudo apt-get --yes --no-install-recommends install \
  python3-gi \
  gir1.2-gtk-4.0 \
  libadwaita-1-dev \
  gir1.2-adw-1

uv venv --python=/usr/bin/python3 --system-site-packages \
  --project="$(pwd)/examples/yarf-example-simple-counter"

run_tutorial() {
  if [ -n "$VARIANT" ]; then
    SIMPLE_COUNTER_THEME="$VARIANT" uv run yarf --platform Mir --variant "$VARIANT" \
      examples/yarf-example-simple-counter/yarf_tests
  else
    uv run yarf --platform Mir examples/yarf-example-simple-counter/yarf_tests
  fi
}

retry_attempts "Tutorial tests (${VARIANT:-default})" "$MAX_ATTEMPTS" run_tutorial
