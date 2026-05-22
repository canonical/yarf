#!/bin/bash
set -euo pipefail

sudo snap install mir-test-tools
sudo apt-get --yes --no-install-recommends install \
  ffmpeg \
  inotify-tools \
  gnome-calculator
