#!/bin/bash
# Boot the newest Ubuntu desktop ISO of ISO_BASE_URL (e.g.
# https://releases.ubuntu.com/noble) in a live session, on VNC display :0.
set -euo pipefail

: "${ISO_BASE_URL:?}"

# GitHub-hosted runners expose /dev/kvm, but only to root by default.
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' \
  | sudo tee /etc/udev/rules.d/99-kvm4all.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=kvm

sudo apt-get update -qq
sudo apt-get install -y -qq qemu-system-x86

# Only the current point release is downloadable, older ones return 403.
read -r iso_sha256 iso_name < <(
  curl -fsSL --retry 3 "$ISO_BASE_URL/SHA256SUMS" \
    | awk '$2 ~ /^\*?ubuntu-[0-9.]+-desktop-amd64\.iso$/ {
        sub(/^\*/, "", $2); print $1, $2 }' \
    | sort -V -k2 | tail -n1
)
echo "Using $iso_name"
if [[ -n "${RESULTS_DIR:-}" ]]; then
  mkdir -p "$RESULTS_DIR"
  echo "$iso_name" > "$RESULTS_DIR/iso.txt"
fi

iso="${RUNNER_TEMP:-/tmp}/ubuntu-desktop.iso"
curl -fsSL --retry 3 -o "$iso" "$ISO_BASE_URL/$iso_name"
echo "$iso_sha256  $iso" | sha256sum --check --strict

qemu-system-x86_64 -enable-kvm -m 8192M -smp 2 \
  -cdrom "$iso" -boot d -vnc :0 -display none -daemonize
