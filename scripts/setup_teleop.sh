#!/usr/bin/env bash
# One-time user-level teleop setup (no sudo; run after install_teleop_deps.sh):
#   1. conda env "sharpa-manus" for Sharpa's retargeting (from the package's environment.yml)
#   2. build the Manus calibration GUI (downloads Dear ImGui from GitHub on first build)
#   3. build tools/manus_pair (pairs gloves to the dongle on Linux)
#
#   bash scripts/setup_teleop.sh
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
[ "$(id -u)" != 0 ] || die "run without sudo: bash $0"
need_manus_sdk
RT=$(rt_dir)

hdr "1/3 conda env $ENV_NAME"
CONDA=$(conda_exe) || die "conda not found. Install Miniforge: https://github.com/conda-forge/miniforge"
if PY=$(env_python); then
  ok "exists: $PY"
else
  "$CONDA" env create -n "$ENV_NAME" -f "$RT/environment.yml"
  PY=$(env_python) || die "env creation failed"
fi
(cd "$RT" && "$PY" -c "import sys; sys.path.insert(0, 'include'); import hand_retargeting_optimizer") \
  && ok "retargeting optimizer imports" || die "optimizer import failed in $ENV_NAME"

hdr "2/3 Manus calibration GUI"
if [ -x "$M/client/CalibrationGUI/CalibrationGUI.out" ]; then ok "already built"
else (cd "$M/client/CalibrationGUI" && ./build.sh) || die "calibration GUI build failed"; ok "built"; fi

hdr "3/3 manus_pair"
make -B -C "$ROOT/tools/manus_pair" MANUS="$M/client/ManusSDK" --no-print-directory || die "manus_pair build failed"
ok "built tools/manus_pair/manus_pair"

[ -x "$M/client/SharpaManusClient.out" ] || warn "no prebuilt client; build it: (cd $M/client && make all)"
echo
echo "Done. Next: pair (if needed) and calibrate the gloves, README step 6."
