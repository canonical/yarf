#!/bin/bash
# Boot the Ubuntu desktop ISO in a live session, with its display on VNC :0.
set -euo pipefail

: "${ISO_URL:?}" "${ISO_SHA256:?}"

# GitHub-hosted runners expose /dev/kvm, but only to root by default.
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' \
  | sudo tee /etc/udev/rules.d/99-kvm4all.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=kvm

sudo apt-get update -qq
sudo apt-get install -y -qq qemu-system-x86

iso="${RUNNER_TEMP:-/tmp}/ubuntu-desktop.iso"
curl -fsSL --retry 3 -o "$iso" "$ISO_URL"
echo "$ISO_SHA256  $iso" | sha256sum --check --strict

qemu-system-x86_64 -enable-kvm -m 8192M -smp 2 \
  -cdrom "$iso" -boot d -vnc :0 -display none -daemonize
