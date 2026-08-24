#!/bin/bash
# Install the applications the YARF suites drive.
#
# The compositor and its tooling come from the yarf-test action; these are the
# apps the suites open on it.
set -euo pipefail

sudo apt-get update -qq
sudo apt-get --yes --no-install-recommends install \
  eog \
  gnome-calculator \
  mpv

# Imported by the keywords listener, which runs in YARF's interpreter. A user
# install is enough, as the action's venv keeps user site packages visible, but
# only while that venv is built on the Python used here.
python3 -m pip install --break-system-packages --user asttokens
