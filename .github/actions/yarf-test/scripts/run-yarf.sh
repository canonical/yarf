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

# Intentional word splitting: these inputs each carry multiple CLI arguments.
# shellcheck disable=SC2206
yarf_args=(${YARF_ARGS})
# shellcheck disable=SC2206
rf_args=(${ROBOTFRAMEWORK_ARGS})

cmd+=(--platform "${PLATFORM}")
cmd+=("${yarf_args[@]}")
cmd+=("${TEST_PATH}")
if [ "${#rf_args[@]}" -gt 0 ]; then
  cmd+=(-- "${rf_args[@]}")
fi

# A caller-supplied --outdir in yarf-args overrides the install-mode default
# used for the reported output directory and the artifact upload path.
output_dir="${YARF_OUTPUT_DIR}"
for ((i = 0; i < ${#yarf_args[@]}; i++)); do
  case "${yarf_args[i]}" in
  --outdir=*) output_dir="${yarf_args[i]#--outdir=}" ;;
  --outdir) output_dir="${yarf_args[i + 1]:-${output_dir}}" ;;
  esac
done

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
  echo "output-dir=${output_dir}"
  echo "exit-code=${exit_code}"
} >> "${GITHUB_OUTPUT}"

echo "YARF finished with result=${result} (exit code ${exit_code})"
