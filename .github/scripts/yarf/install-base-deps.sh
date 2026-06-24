#!/bin/bash
set -euo pipefail

sudo apt update -qq
sudo apt install -y \
  git-lfs \
  libgl1 \
  libxkbcommon-dev \
  jq \
  clang \
  python3-tk \
  tesseract-ocr
