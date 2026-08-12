#!/bin/bash
# Install workflow dependencies for the YARF test action.
#
# Installs the base apt packages YARF needs and, for the built-in Mir/Vnc
# providers, the virtual compositor tooling (including the architecture
# specific wlrctl build on non-amd64 runners) plus wayvnc for Vnc.
#
# Environment:
#   PLATFORM_PROVIDER  Platform provider: Mir, Vnc, or custom (default: Mir).
set -euo pipefail

PLATFORM_PROVIDER="${PLATFORM_PROVIDER:-Mir}"

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  clang \
  git-lfs \
  jq \
  libgl1 \
  libxkbcommon-dev \
  python3-tk \
  tesseract-ocr

case "${PLATFORM_PROVIDER}" in
Mir | Vnc)
  sudo snap install mir-test-tools
  sudo apt-get install -y --no-install-recommends inotify-tools

  arch="$(dpkg --print-architecture)"
  if [ "${arch}" = "amd64" ]; then
    sudo apt-get install -y --no-install-recommends wlrctl
  else
    # wlrctl has no package outside amd64, so build it from a pinned release.
    wlrctl_tag="v0.2.2"
    wlrctl_commit="afe60da062ea315b92f2a9857e50b77e0b3a4b7e"
    sudo apt-get install -y --no-install-recommends \
      gcc libwayland-dev meson ninja-build scdoc wayland-protocols
    build_dir="$(mktemp -d)"
    git clone --depth 1 --branch "${wlrctl_tag}" \
      https://git.sr.ht/~brocellous/wlrctl "${build_dir}/wlrctl"
    actual_commit="$(git -C "${build_dir}/wlrctl" rev-parse HEAD)"
    if [ "${actual_commit}" != "${wlrctl_commit}" ]; then
      echo "wlrctl ${wlrctl_tag} resolved to ${actual_commit}, expected ${wlrctl_commit}" >&2
      exit 1
    fi
    meson setup "${build_dir}/wlrctl/build" "${build_dir}/wlrctl"
    ninja -C "${build_dir}/wlrctl/build"
    sudo ninja -C "${build_dir}/wlrctl/build" install
  fi

  if [ "${PLATFORM_PROVIDER}" = "Vnc" ]; then
    sudo apt-get install -y --no-install-recommends wayvnc
  fi
  ;;
custom) ;;
*)
  echo "Unknown platform-provider: '${PLATFORM_PROVIDER}' (expected Mir, Vnc, or custom)" >&2
  exit 1
  ;;
esac
