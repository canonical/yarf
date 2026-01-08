#!/bin/bash
set -euo pipefail

ARCH="$1"

sudo apt update -qq

if [ "$ARCH" == "arm64" ]; then
    sudo apt-get --yes --no-install-recommends install \
    libwayland-dev \
    wayland-protocols
fi
