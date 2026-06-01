#!/bin/bash
set -euo pipefail

pip install check-jsonschema

uv run yarf --platform Mir --output-format TestSubmissionSchema tests/canary_test

OUTPUT=/tmp/yarf-outdir/TestSubmissionSchema_output.json
version=$(jq -r '.version' "$OUTPUT")
check-jsonschema \
  --schemafile "https://raw.githubusercontent.com/canonical/test-submission-schema/refs/heads/main/test_submission_schema/schemas/v${version}.json" \
  "$OUTPUT"
