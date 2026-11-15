#!/bin/bash
# Prepare the word grid app that the canary grid suites launch from the
# workflow.
#
# The venv must live outside tests/: YARF copies the suite folder before it
# runs the suite, and the strictly confined snap cannot follow the venv's
# symlink to /usr/bin/python3, so a venv inside the suite folder breaks the
# copy. Launch the app with UV_PROJECT_ENVIRONMENT set to the same path.
#
# Usage: setup-grid-app.sh <venv path>
set -euo pipefail

VENV="$1"

sudo apt-get update -qq
sudo apt-get --yes --no-install-recommends install \
  python3-gi \
  gir1.2-gtk-4.0 \
  libadwaita-1-dev \
  gir1.2-adw-1

# Use Ubuntu's interpreter because `python3-gi` is installed for it.
/usr/bin/python3 -m venv --system-site-packages "${VENV}"
