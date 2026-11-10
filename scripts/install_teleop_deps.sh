#!/usr/bin/env bash
# One-time system setup for Manus glove teleop (needs root):
#   1. packages to build/run Sharpa's Manus client and calibration GUI (official list, Ubuntu 24.04 names)
#   2. a udev rule so the Manus USB dongle can be opened without root
#
#   sudo bash scripts/install_teleop_deps.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run as root: sudo bash $0"; exit 1; }

apt-get update
apt-get install -y \
  build-essential curl libusb-1.0-0-dev zlib1g-dev libudev-dev libncurses-dev \
  libeigen3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev \
  libzmq3-dev libprotobuf-dev protobuf-compiler libprotoc-dev

cat > /etc/udev/rules.d/70-manus-hid.rules <<'EOF'
# Manus dongle / license key (HIDAPI via libusb and hidraw)
SUBSYSTEMS=="usb", ATTRS{idVendor}=="3325", MODE:="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="83fd", MODE:="0666"
KERNEL=="hidraw*", ATTRS{idVendor}=="3325", MODE:="0666"
EOF
udevadm control --reload-rules
udevadm trigger
echo
echo "Done. Unplug and replug the Manus dongle, then run: bash scripts/setup_teleop.sh"
