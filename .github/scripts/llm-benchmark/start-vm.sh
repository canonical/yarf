#!/bin/bash
# Boot the newest Ubuntu desktop ISO of ISO_BASE_URL (e.g.
# https://releases.ubuntu.com/noble) in a live session, on VNC display :0.
# The HMP monitor at QEMU_MONITOR lets the suite save and restore snapshots,
# which are stored in VM_STATE_DIR.
set -euo pipefail

: "${ISO_BASE_URL:?}"
monitor="${QEMU_MONITOR:-/tmp/yarf-vm-monitor.sock}"
state_dir="${VM_STATE_DIR:-${RUNNER_TEMP:-/tmp}}"

# GitHub-hosted runners expose /dev/kvm, but only to root by default.
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' \
  | sudo tee /etc/udev/rules.d/99-kvm4all.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=kvm

sudo apt-get update -qq
sudo apt-get install -y -qq qemu-system-x86 qemu-utils

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

# A snapshot holds all guest RAM (~8 GB). The image is not attached to a
# device, so the guest does not see it.
sudo mkdir -p "$state_dir"
sudo chown "$(id -u):$(id -g)" "$state_dir"
qemu-img create -q -f qcow2 "$state_dir/vm-state.qcow2" 16G

qemu-system-x86_64 -enable-kvm -m 8192M -smp 2 -audio none \
  -cdrom "$iso" -boot d \
  -blockdev "driver=qcow2,node-name=vmstate,file.driver=file,file.filename=$state_dir/vm-state.qcow2" \
  -monitor "unix:$monitor,server=on,wait=off" \
  -vnc :0 -display none -daemonize
