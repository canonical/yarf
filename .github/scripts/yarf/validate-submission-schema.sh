#!/bin/bash
# Validate YARF's test submission schema output against the published schema.
#
# Arguments:
#   $1  YARF output directory holding TestSubmissionSchema_output.json.
set -euo pipefail

OUTPUT_DIR=${1:?usage: validate-submission-schema.sh <yarf-output-dir>}
OUTPUT="${OUTPUT_DIR}/TestSubmissionSchema_output.json"

# Lands in the venv the yarf-test action set up.
uv pip install check-jsonschema

version=$(jq -r '.version' "$OUTPUT")
check-jsonschema \
  --schemafile "https://raw.githubusercontent.com/canonical/test-submission-schema/refs/heads/main/test_submission_schema/schemas/v${version}.json" \
  "$OUTPUT"
