#!/bin/bash
# Prepare the simple counter example the tutorial suite drives.
#
# The suite starts the app itself with `uv --project ... run simple-counter`,
# which reuses this venv rather than creating an isolated one. It has to see
# the system site packages, because the app imports the GTK bindings from apt.
set -euo pipefail

sudo apt-get update -qq
sudo apt-get --yes --no-install-recommends install \
  python3-gi \
  gir1.2-gtk-4.0 \
  libadwaita-1-dev \
  gir1.2-adw-1 \
  gsettings-desktop-schemas

python3 -m venv --system-site-packages \
  examples/yarf-example-simple-counter/.venv
