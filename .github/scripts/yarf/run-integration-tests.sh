#!/bin/bash
set -euo pipefail

MAX_ATTEMPTS=${INTEGRATION_TEST_MAX_ATTEMPTS:-3}

# shellcheck source=.github/scripts/yarf/_retry.sh
. "$(dirname "$0")/_retry.sh"

pip install check-jsonschema

run_integration() {
  uv run yarf --platform Mir --output-format TestSubmissionSchema tests/canary_test

  local output=/tmp/yarf-outdir/TestSubmissionSchema_output.json
  local version
  version=$(jq -r '.version' "$output")
  check-jsonschema \
    --schemafile "https://raw.githubusercontent.com/canonical/test-submission-schema/refs/heads/main/test_submission_schema/schemas/v${version}.json" \
    "$output"
}

retry_attempts "Integration tests" "$MAX_ATTEMPTS" run_integration
