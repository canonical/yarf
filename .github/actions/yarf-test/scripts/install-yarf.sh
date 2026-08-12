#!/bin/bash
# Install YARF from a snap channel or from source at a given git ref.
#
# When YARF_REF is set, YARF is built and installed from that git ref with pip;
# otherwise the yarf snap is installed from YARF_CHANNEL. The resolved install
# mode and output directory are exported to $GITHUB_ENV so later steps can
# locate YARF's results without hardcoding a path.
#
# Environment:
#   YARF_REF      Optional git ref (branch/tag/SHA) to build YARF from source.
#   YARF_CHANNEL  Snap channel to install from (default: latest/stable).
#   GITHUB_ENV    File used to export variables to later steps.
set -euo pipefail

YARF_REF="${YARF_REF:-}"
YARF_CHANNEL="${YARF_CHANNEL:-latest/stable}"

if [ -n "${YARF_REF}" ]; then
  echo "Installing YARF from source at ref '${YARF_REF}'"
  # --break-system-packages installs the console script onto PATH on
  # PEP 668 externally-managed runners.
  python3 -m pip install --break-system-packages \
    "yarf @ git+https://github.com/canonical/yarf.git@${YARF_REF}"
  install_mode="source"
  output_dir="${TMPDIR:-/tmp}/yarf-outdir"
else
  echo "Installing YARF snap from channel '${YARF_CHANNEL}'"
  sudo snap install yarf --channel="${YARF_CHANNEL}"
  install_mode="snap"
  output_dir="${HOME}/snap/yarf/common/yarf-outdir"
fi

{
  echo "YARF_INSTALL_MODE=${install_mode}"
  echo "YARF_OUTPUT_DIR=${output_dir}"
} >> "${GITHUB_ENV}"

echo "Installed YARF (mode=${install_mode}); output dir: ${output_dir}"
