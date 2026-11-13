#!/bin/bash
set -euo pipefail

PLATFORM="$1"

sudo snap install mir-test-tools
sudo apt update -qq
sudo apt-get --yes --no-install-recommends install \
ffmpeg \
inotify-tools \
gnome-calculator \
eog

if [ "$PLATFORM" == "Vnc" ]; then
    sudo apt-get --yes --no-install-recommends install wayvnc
fi
