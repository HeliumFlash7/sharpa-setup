# Shared settings and helpers for the scripts in this folder. Sourced, not run.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Factory-default network of the Sharpa Wave W01 (manual: Get Started > 5.1 Default Network Settings)
HOST_IP=192.168.10.240
LEFT_IP=192.168.10.10
RIGHT_IP=192.168.10.20
PROFILE=sharpa-w01                      # NetworkManager profile created by setup_network.sh

# Manus teleop package (unpacked by fetch_vendor.sh) and its conda env (created by setup_teleop.sh)
M="${SHARPA_MANUS_SDK:-$ROOT/vendor/sharpa-manus-sdk-1.0.1}"
ENV_NAME="${SHARPA_MANUS_ENV:-sharpa-manus}"

ok()   { printf '  \e[32mOK\e[0m    %s\n' "$*"; }
warn() { printf '  \e[33mWARN\e[0m  %s\n' "$*"; }
bad()  { printf '  \e[31mFAIL\e[0m  %s\n' "$*"; }
info() { printf '  --    %s\n' "$*"; }
hdr()  { printf '\n== %s\n' "$*"; }
die()  { printf '\e[31mError:\e[0m %s\n' "$*" >&2; exit 1; }

# Ethernet interface for the hand: $SHARPA_IFACE, else the sharpa-w01 profile's interface,
# else the only wired interface NetworkManager knows. Prints nothing if it can't decide.
eth_iface() {
  if [ -n "${SHARPA_IFACE:-}" ]; then echo "$SHARPA_IFACE"; return; fi
  local i
  i=$(nmcli -g connection.interface-name connection show "$PROFILE" 2>/dev/null || true)
  if [ -n "$i" ]; then echo "$i"; return; fi
  i=$(nmcli -t -f DEVICE,TYPE device 2>/dev/null | awk -F: '$2=="ethernet"{print $1}')
  [ "$(printf '%s\n' "$i" | grep -c .)" = 1 ] && echo "$i"
  return 0
}

# Newest retargeting folder inside the Manus package (V4.0 in v1.0.1, V5.0 in v1.2.0).
rt_dir() { ls -d "$M"/retargeting_alg_release_V* 2>/dev/null | sort -V | tail -1; }

need_manus_sdk() {
  [ -d "$M/client" ] || die "Manus package not found at $M. Run: bash scripts/fetch_vendor.sh"
}

conda_exe() {
  local c
  for c in "${CONDA_EXE:-}" "$(command -v conda 2>/dev/null)" "$HOME"/miniforge3/bin/conda \
           "$HOME"/miniconda3/bin/conda "$HOME"/anaconda3/bin/conda; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return; }
  done
  return 1
}

# Python of the teleop conda env (empty if the env does not exist).
env_python() {
  local c p
  c=$(conda_exe) || return 1
  p=$("$c" env list 2>/dev/null | awk -v n="$ENV_NAME" '$1==n {print $NF}')
  [ -n "$p" ] && [ -x "$p/bin/python" ] && echo "$p/bin/python"
}
