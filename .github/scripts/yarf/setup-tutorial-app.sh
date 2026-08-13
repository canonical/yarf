#!/bin/bash
# Prepare the simple counter example the tutorial suite drives.
#
# The suite starts the app itself with `uv --project ... run simple-counter`,
# so its venv has to exist before YARF runs and must see the system site
# packages, because the app imports the GTK bindings from apt.
set -euo pipefail

APP_DIR="$(pwd)/examples/yarf-example-simple-counter"

sudo apt-get update -qq
sudo apt-get --yes --no-install-recommends install \
  python3-gi \
  gir1.2-gtk-4.0 \
  libadwaita-1-dev \
  gir1.2-adw-1

uv venv --python=/usr/bin/python3 --system-site-packages --project="${APP_DIR}"

# Syncs the venv and surfaces a broken app here, rather than as a blank screen
# 90 seconds into the suite.
uv --project "${APP_DIR}" run simple-counter --help > /dev/null
