#!/bin/bash
set -euo pipefail

PLATFORM="$1"

bash "$(dirname "$0")/snap-install.sh" mir-test-tools
sudo apt update -qq
sudo apt-get --yes --no-install-recommends install \
ffmpeg \
inotify-tools \
gnome-calculator \
eog

if [ "$PLATFORM" == "Vnc" ]; then
    sudo apt-get --yes --no-install-recommends install wayvnc
fi
