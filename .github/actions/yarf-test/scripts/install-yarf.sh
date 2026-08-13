#!/bin/bash
# Install YARF from source at a given git ref.
#
# The output directory is exported to $GITHUB_ENV so later steps can locate
# YARF's results without hardcoding a path.
#
# Environment:
#   YARF_REF    Git ref (branch/tag/SHA) to build YARF from (default: main).
#   GITHUB_ENV  File used to export variables to later steps.
set -euo pipefail

YARF_REF="${YARF_REF:-main}"
output_dir="${TMPDIR:-/tmp}/yarf-outdir"

echo "Installing YARF from source at ref '${YARF_REF}'"
# --break-system-packages installs the console script onto PATH on
# PEP 668 externally-managed runners.
python3 -m pip install --break-system-packages \
  "yarf @ git+https://github.com/canonical/yarf.git@${YARF_REF}"

echo "YARF_OUTPUT_DIR=${output_dir}" >> "${GITHUB_ENV}"

echo "Installed YARF; output dir: ${output_dir}"
