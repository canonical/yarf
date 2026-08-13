#!/bin/bash
# Install YARF from source at a given git ref, into a dedicated uv venv.
#
# The venv is put on $GITHUB_PATH and exported through VIRTUAL_ENV so later
# steps (a custom platform's setup command, the YARF run itself) install into
# and run from the same environment. That matters because YARF discovers
# platform plugins in the site-packages of the interpreter it runs on. The
# output directory is exported too, so later steps need not hardcode a path.
#
# Environment:
#   YARF_REF     Git ref (branch/tag/SHA) to build YARF from (default: main).
#   RUNNER_TEMP  Directory the venv and the checkout are created in.
#   GITHUB_ENV   File used to export variables to later steps.
#   GITHUB_PATH  File used to extend PATH for later steps.
set -euo pipefail

YARF_REF="${YARF_REF:-main}"
output_dir="${TMPDIR:-/tmp}/yarf-outdir"
venv="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/yarf-venv"
src="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/yarf-src"

if ! command -v uv > /dev/null; then
  echo "Installing uv"
  python3 -m pip install --break-system-packages --user uv
  user_bin="$(python3 -m site --user-base)/bin"
  export PATH="${user_bin}:${PATH}"
  echo "${user_bin}" >> "${GITHUB_PATH}"
fi

# uv-managed Python builds lack os.memfd_create, which the Mir platform needs,
# so the venv has to be built on an interpreter already on the runner.
# System site packages stay visible so callers can prepare dependencies before
# this action runs, and pip is seeded so a plain `pip install` in a caller's
# command lands in this venv rather than escaping to the system one.
uv --no-managed-python venv --seed --system-site-packages "${venv}"

echo "Installing YARF from source at ref '${YARF_REF}'"
# Checked out here rather than installed straight from the git URL, because pip
# and uv do not fetch Git LFS objects and YARF ships assets that need them.
rm -rf "${src}"
git init --quiet "${src}"
git -C "${src}" remote add origin https://github.com/canonical/yarf.git
git -C "${src}" fetch --quiet --depth 1 origin "${YARF_REF}"
git -C "${src}" checkout --quiet FETCH_HEAD
# Only the packaged assets are needed; a caller's own suite assets come from
# their checkout.
git -C "${src}" lfs pull --include="yarf/**"

uv pip install --python "${venv}/bin/python" "${src}"

{
  echo "VIRTUAL_ENV=${venv}"
  echo "YARF_OUTPUT_DIR=${output_dir}"
} >> "${GITHUB_ENV}"
echo "${venv}/bin" >> "${GITHUB_PATH}"

echo "Installed YARF in ${venv}; output dir: ${output_dir}"
