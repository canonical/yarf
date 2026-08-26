#!/bin/bash
# Install YARF from source, into a dedicated uv venv.
#
# The source comes from YARF_PATH when set, otherwise from a git checkout of
# YARF_REPOSITORY at YARF_REF.
#
# The venv is put on $GITHUB_PATH and exported through VIRTUAL_ENV so later
# steps (a custom platform's setup command, the YARF run itself) install into
# and run from the same environment. That matters because YARF discovers
# platform plugins in the site-packages of the interpreter it runs on. The
# output directory is exported too, so later steps need not hardcode a path.
#
# Environment:
#   YARF_PATH        Path to a YARF source tree; takes priority over YARF_REF.
#   YARF_REF         Git ref (branch/tag/SHA) to build YARF from (default: main).
#   YARF_REPOSITORY  Repository to fetch YARF from (default: canonical/yarf).
#   RUNNER_TEMP      Directory the venv and the checkout are created in.
#   GITHUB_ENV       File used to export variables to later steps.
#   GITHUB_PATH      File used to extend PATH for later steps.
set -euo pipefail

YARF_PATH="${YARF_PATH:-}"
YARF_REF="${YARF_REF:-}"
YARF_REPOSITORY="${YARF_REPOSITORY:-canonical/yarf}"
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

# Built on an interpreter already on the runner so its site packages stay
# visible, letting callers prepare dependencies before this action runs. pip is
# seeded so a plain `pip install` in a caller's command lands in this venv
# rather than escaping to the system one.
uv --no-managed-python venv --seed --system-site-packages "${venv}"

if [ -n "${YARF_PATH}" ]; then
  echo "Installing YARF from '${YARF_PATH}'"
  src="${YARF_PATH}"
else
  if [ -z "${YARF_REF}" ]; then
    echo "No yarf-ref specified, defaulting to 'main'"
    YARF_REF="main"
  fi
  echo "Installing YARF from '${YARF_REPOSITORY}' at ref '${YARF_REF}'"
  # Checked out here rather than installed straight from the git URL, because
  # pip and uv do not fetch Git LFS objects and YARF ships assets that need
  # them.
  rm -rf "${src}"
  git init --quiet "${src}"
  git -C "${src}" remote add origin "https://github.com/${YARF_REPOSITORY}.git"
  git -C "${src}" fetch --quiet --depth 1 origin "${YARF_REF}"
  git -C "${src}" checkout --quiet FETCH_HEAD
  # Only the packaged assets are needed; a caller's own suite assets come from
  # their checkout.
  git -C "${src}" lfs pull --include="yarf/**"
fi

# Install the locked dependency set when the source tree ships a lock file, so
# a run is reproducible rather than resolving to whatever is latest.
if [ -f "${src}/uv.lock" ]; then
  requirements="$(mktemp)"
  uv export --frozen --no-dev --no-emit-project --project "${src}" -o "${requirements}"
  uv pip install --python "${venv}/bin/python" -r "${requirements}" "${src}"
else
  uv pip install --python "${venv}/bin/python" "${src}"
fi

{
  echo "VIRTUAL_ENV=${venv}"
  echo "YARF_OUTPUT_DIR=${output_dir}"
} >> "${GITHUB_ENV}"
echo "${venv}/bin" >> "${GITHUB_PATH}"

echo "Installed YARF in ${venv}; output dir: ${output_dir}"
