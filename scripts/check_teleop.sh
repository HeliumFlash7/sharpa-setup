#!/usr/bin/env bash
# Read-only check of the Manus teleop stack: system packages, udev rule, USB dongle, vendor package,
# builds, glove calibration, conda env, hand reachability, running processes. Changes nothing.
#
#   bash scripts/check_teleop.sh
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
FAIL=0
bad() { printf '  \e[31mFAIL\e[0m  %s\n' "$*"; FAIL=$((FAIL + 1)); }

hdr "System (sudo bash scripts/install_teleop_deps.sh)"
miss=""
for p in build-essential curl libusb-1.0-0-dev zlib1g-dev libudev-dev libncurses-dev libeigen3-dev libglfw3-dev \
         libgl1-mesa-dev libglu1-mesa-dev libzmq3-dev libprotobuf-dev protobuf-compiler libprotoc-dev; do
  dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || miss="$miss $p"
done
[ -z "$miss" ] && ok "packages installed" || bad "missing:$miss"
[ -f /etc/udev/rules.d/70-manus-hid.rules ] && ok "udev rule" || bad "no udev rule /etc/udev/rules.d/70-manus-hid.rules"

hdr "USB"
usb=$(lsusb 2>/dev/null | grep -iE "ID 3325:|ID 1915:83fd")
[ -n "$usb" ] && printf '%s\n' "$usb" | sed 's/^/  OK    /' || bad "no Manus dongle on USB (vendor 3325)"

hdr "Vendor package ($M)"
if [ -d "$M/client" ]; then
  ok "sharpa-manus-sdk present"
  [ -x "$M/client/SharpaManusClient.out" ] && ok "client binary" || bad "no client binary: (cd $M/client && make all)"
  [ -x "$M/client/CalibrationGUI/CalibrationGUI.out" ] && ok "calibration GUI built" || bad "calibration GUI not built: bash scripts/setup_teleop.sh"
  SHIPPED="$M/client/calibration_backup/sharpa_shipped"
  for s in left right; do
    f="$M/client/Calibration_$s.mcal"
    if [ ! -f "$f" ]; then bad "no Calibration_$s.mcal"
    elif [ ! -f "$SHIPPED/Calibration_$s.mcal" ] || cmp -s "$f" "$SHIPPED/Calibration_$s.mcal"; then
      warn "$s glove: still Sharpa's shipped calibration (run: bash scripts/teleop.sh calibrate <name>)"
    else ok "$s glove: operator calibration ($(date -r "$f" '+%F %R'))"; fi
  done
else
  bad "missing: bash scripts/fetch_vendor.sh"
fi
[ -x "$ROOT/tools/manus_pair/manus_pair" ] && ok "manus_pair built" || warn "manus_pair not built: bash scripts/setup_teleop.sh"

hdr "Python env $ENV_NAME"
if PY=$(env_python); then
  RT=$(rt_dir)
  out=$(cd "$RT" && "$PY" -c "import sys; sys.path.insert(0, 'include'); import zmq, google.protobuf, casadi, hand_retargeting_optimizer; print('OK')" 2>&1 | tail -1)
  [ "$out" = OK ] && ok "retargeting imports ($(basename "$RT"))" || bad "import failed: $out"
else bad "env missing: bash scripts/setup_teleop.sh"; fi

hdr "Hand / processes"
for side in right left; do
  ipvar=${side^^}_IP; ip=${!ipvar}
  ping -c 1 -W 1 "$ip" >/dev/null 2>&1 && ok "$side hand $ip reachable" || info "$side hand $ip not reachable"
done
for p in SharpaManusClient.out retargeting_manus_demo /opt/sharpa-pilot/sharpa-pilot; do
  pgrep -f "$p" >/dev/null && info "running: $(basename "$p")"
done
echo; echo "Summary: $FAIL problem(s)"
exit $((FAIL > 0))
