#!/usr/bin/env bash
# Manus glove -> Sharpa Wave teleop launcher (wraps Sharpa's sharpa-manus-sdk in vendor/).
#
#   bash scripts/teleop.sh client            # terminal A: glove client (Space quits)
#   bash scripts/teleop.sh wave              # terminal B: retarget + drive the hand (Ctrl-C stops)
#   bash scripts/teleop.sh plot              # terminal B: retarget + 3D plot only, robot not driven
#   bash scripts/teleop.sh watch             # print the retargeted joint angles (read-only)
#   bash scripts/teleop.sh calibrate <name>  # glove calibration GUI; saves to calib/<name>/ and activates it
#   bash scripts/teleop.sh use <name>        # activate a saved calibration (restart the client after)
#   bash scripts/teleop.sh pair [--list]     # pair gloves whose LED blinks white
#   bash scripts/teleop.sh check             # read-only check of the whole teleop stack
#
# Extra arguments after `wave` / `plot` go to the retargeting script, e.g. `wave -filter_alpha 0.3`.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

CMD="${1:-}"; shift || true
GLOVE_IPS=(-glove_left_ip 192.168.10.98 -glove_right_ip 192.168.10.99)  # labels for the virtual gloves in Pilot

retarget() {
  need_manus_sdk
  local py rt; py=$(env_python) || die "conda env $ENV_NAME missing; run: bash scripts/setup_teleop.sh"
  rt=$(rt_dir)
  cd "$rt" && exec "$py" retargeting_manus_demo_multiprocess.py "$@"
}

install_calib() {  # source-dir: copy Calibration_{left,right}.mcal into the client folder
  local f n=0 shipped="$M/client/calibration_backup/sharpa_shipped"
  if [ ! -d "$shipped" ]; then  # keep Sharpa's original files once, before the first overwrite
    mkdir -p "$shipped" && cp "$M"/client/Calibration_{left,right}.mcal "$shipped"/ 2>/dev/null || true
  fi
  for f in "$1"/Calibration_left.mcal "$1"/Calibration_right.mcal; do
    [ -f "$f" ] && cp "$f" "$M/client/" && echo "  active: $(basename "$f")" && n=$((n + 1))
  done
  [ $n -gt 0 ] || die "no Calibration_*.mcal in $1"
}

case "$CMD" in
  client)
    need_manus_sdk
    pgrep -f "CalibrationGUI.out|manus_pair" >/dev/null && die "close CalibrationGUI / manus_pair first (they hold the dongle)"
    cd "$M/client" && exec ./SharpaManusClient.out ;;
  wave) retarget -wave "${GLOVE_IPS[@]}" "$@" ;;
  plot) retarget -plot "$@" ;;
  watch)
    py=$(env_python) || die "conda env $ENV_NAME missing; run: bash scripts/setup_teleop.sh"
    exec "$py" "$ROOT/scripts/watch_hand_action.py" "$@" ;;
  calibrate)
    need_manus_sdk
    NAME="${1:?usage: teleop.sh calibrate <operator-name>}"
    pgrep -f "SharpaManusClient.out|manus_pair" >/dev/null && die "stop the client / manus_pair first (they hold the dongle)"
    GUI="$M/client/CalibrationGUI"
    [ -x "$GUI/CalibrationGUI.out" ] || die "calibration GUI not built; run: bash scripts/setup_teleop.sh"
    MARK=$(mktemp); trap 'rm -f "$MARK"' EXIT
    (cd "$GUI" && ./CalibrationGUI.out) || true
    OUT="$ROOT/calib/$NAME"; mkdir -p "$OUT"; n=0
    for f in "$GUI"/Calibration_left.mcal "$GUI"/Calibration_right.mcal; do
      [ "$f" -nt "$MARK" ] && cp "$f" "$OUT/" && n=$((n + 1))
    done
    [ $n -gt 0 ] || die "no new calibration was written (finish all steps until 'Calibration Complete')"
    echo "Saved $n file(s) to calib/$NAME/"
    install_calib "$OUT"
    echo "Restart the client to load it." ;;
  use)
    need_manus_sdk
    NAME="${1:?usage: teleop.sh use <operator-name>}"
    install_calib "$ROOT/calib/$NAME"
    echo "Restart the client to load it." ;;
  pair)
    BIN="$ROOT/tools/manus_pair/manus_pair"
    [ -x "$BIN" ] || die "manus_pair not built; run: bash scripts/setup_teleop.sh"
    pgrep -f "SharpaManusClient.out|CalibrationGUI.out" >/dev/null && die "close the client / CalibrationGUI first (they hold the dongle)"
    exec "$BIN" "$@" ;;
  check) exec bash "$ROOT/scripts/check_teleop.sh" ;;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 2 ;;
esac
