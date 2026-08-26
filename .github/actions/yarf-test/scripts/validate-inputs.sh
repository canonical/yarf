#!/bin/bash
# Validate the action inputs before anything is installed or started.
#
# Only checks what the action definition cannot express: values that depend on
# the selected platform-provider, values whose format matters, and whether the
# test suite is actually in the checkout. All problems are collected and
# reported together so a broken workflow needs a single round of fixes. The
# canonical platform-provider spelling is exported to $GITHUB_ENV for the later
# steps.
#
# Environment:
#   PLATFORM                   Value passed to `yarf --platform`.
#   PLATFORM_PROVIDER          stock or custom.
#   PLATFORM_SETUP_COMMAND     Command(s) to start a custom platform.
#   PLATFORM_READY_COMMAND     Command(s) that block until a custom platform is ready.
#   PLATFORM_TEARDOWN_COMMAND  Command(s) to tear down a custom platform.
#   TEST_PATH                  Path to the YARF test suite to run.
#   DISPLAY_SIZE               Virtual output resolution for the stock platform.
#   UPLOAD_ARTIFACT            Whether to upload the YARF output dir.
#   GITHUB_ENV                 File used to export variables to later steps.
set -euo pipefail

# Accept any casing and pass the canonical spelling on to the scripts that
# match on it.
case "${PLATFORM_PROVIDER:-}" in
[Ss][Tt][Oo][Cc][Kk]) PLATFORM_PROVIDER="stock" ;;
[Cc][Uu][Ss][Tt][Oo][Mm]) PLATFORM_PROVIDER="custom" ;;
esac

errors=()

if [ ! -e "${TEST_PATH:-}" ]; then
  errors+=("test-path '${TEST_PATH:-}' does not exist; did the workflow run actions/checkout?")
fi

case "${PLATFORM_PROVIDER:-}" in
stock)
  for input in setup ready teardown; do
    var="PLATFORM_${input^^}_COMMAND"
    if [ -n "${!var:-}" ]; then
      errors+=("platform-${input}-command is only used when platform-provider is custom")
    fi
  done
  ;;
custom)
  for input in setup ready teardown; do
    var="PLATFORM_${input^^}_COMMAND"
    if [ -z "${!var:-}" ]; then
      errors+=("platform-${input}-command is required when platform-provider is custom")
    fi
  done
  ;;
*)
  errors+=("platform-provider '${PLATFORM_PROVIDER:-}' is invalid (expected stock or custom)")
  ;;
esac

if ! [[ "${DISPLAY_SIZE:-}" =~ ^[0-9]+x[0-9]+$ ]]; then
  errors+=("display-size '${DISPLAY_SIZE:-}' is invalid (expected <width>x<height>)")
fi

case "${UPLOAD_ARTIFACT:-}" in
true | false) ;;
*)
  errors+=("upload-artifact '${UPLOAD_ARTIFACT:-}' is invalid (expected true or false)")
  ;;
esac

if [ "${#errors[@]}" -gt 0 ]; then
  for error in "${errors[@]}"; do
    echo "Invalid input: ${error}" >&2
  done
  exit 1
fi

echo "PLATFORM_PROVIDER=${PLATFORM_PROVIDER}" >> "${GITHUB_ENV:-/dev/null}"

echo "Inputs validated for platform '${PLATFORM:-}' (provider: ${PLATFORM_PROVIDER})"
