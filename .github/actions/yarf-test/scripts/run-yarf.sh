#!/bin/bash
# Run YARF against a test suite, capture the result and clean up.
#
# Invokes YARF (via the snap or the source-installed entry point depending on
# YARF_INSTALL_MODE), records the outcome and output directory to
# $GITHUB_OUTPUT, and makes a best-effort attempt to stop the launched app.
# It always exits 0; the captured YARF exit code is exported so a later step
# can propagate pass/fail to the job.
#
# Environment:
#   PLATFORM             Value passed to `yarf --platform` (required).
#   TEST_PATH            Path to the YARF test suite to run (required).
#   YARF_ARGS            Extra yarf options placed before the test path.
#   ROBOTFRAMEWORK_ARGS  Extra args appended after `--`.
#   YARF_INSTALL_MODE    snap or source (default: snap).
#   YARF_OUTPUT_DIR      Resolved YARF output directory.
#   YARF_APP_PID         PID of the app launched under test, if any.
#   GITHUB_OUTPUT        File used to expose step outputs.
set -euo pipefail

PLATFORM="${PLATFORM:?platform is required}"
TEST_PATH="${TEST_PATH:?test-path is required}"
YARF_ARGS="${YARF_ARGS:-}"
ROBOTFRAMEWORK_ARGS="${ROBOTFRAMEWORK_ARGS:-}"
YARF_INSTALL_MODE="${YARF_INSTALL_MODE:-snap}"
YARF_OUTPUT_DIR="${YARF_OUTPUT_DIR:-}"

if [ "${YARF_INSTALL_MODE}" = "snap" ]; then
  cmd=(snap run yarf)
else
  cmd=(yarf)
fi

cmd+=(--platform "${PLATFORM}")
# Intentional word splitting: these inputs carry multiple CLI arguments.
# shellcheck disable=SC2206
[ -n "${YARF_ARGS}" ] && cmd+=(${YARF_ARGS})
cmd+=("${TEST_PATH}")
if [ -n "${ROBOTFRAMEWORK_ARGS}" ]; then
  # shellcheck disable=SC2206
  cmd+=(-- ${ROBOTFRAMEWORK_ARGS})
fi

echo "Running: ${cmd[*]}"
set +e
"${cmd[@]}"
exit_code=$?
set -e

# Best-effort cleanup of the app launched under test.
if [ -n "${YARF_APP_PID:-}" ]; then
  kill "${YARF_APP_PID}" 2>/dev/null || true
fi

if [ "${exit_code}" -eq 0 ]; then
  result="passed"
else
  result="failed"
fi

{
  echo "result=${result}"
  echo "output-dir=${YARF_OUTPUT_DIR}"
  echo "exit-code=${exit_code}"
} >> "${GITHUB_OUTPUT}"

echo "YARF finished with result=${result} (exit code ${exit_code})"
