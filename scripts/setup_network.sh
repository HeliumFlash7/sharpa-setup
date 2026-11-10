#!/usr/bin/env bash
# Give the Ethernet port the host address the W01 expects: 192.168.10.240/24, no gateway, never the
# default route, so Wi-Fi / internet keep working. Creates (or updates) NetworkManager profile
# "sharpa-w01". No sudo needed in a desktop session.
#
#   bash scripts/setup_network.sh [interface]      # interface: auto-detected if there is only one
#
# Undo: nmcli connection delete sharpa-w01
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

command -v nmcli >/dev/null || die "nmcli not found (NetworkManager is required)"
IF="${1:-$(eth_iface)}"
if [ -z "$IF" ]; then
  echo "Wired interfaces:"; nmcli -t -f DEVICE,TYPE,STATE device | awk -F: '$2=="ethernet"{print "  "$1" ("$3")"}'
  die "pick the one the hand is plugged into: bash $0 <interface>"
fi
[ -d "/sys/class/net/$IF" ] || die "no interface $IF (list them with: ip -br link)"

if nmcli connection show "$PROFILE" >/dev/null 2>&1; then
  echo "Updating profile $PROFILE on $IF"
else
  echo "Creating profile $PROFILE on $IF"
  nmcli connection add type ethernet ifname "$IF" con-name "$PROFILE" >/dev/null
fi
nmcli connection modify "$PROFILE" \
  connection.interface-name "$IF" \
  ipv4.method manual ipv4.addresses "$HOST_IP/24" ipv4.gateway "" ipv4.never-default yes ipv4.dns "" \
  ipv6.method disabled \
  connection.autoconnect yes connection.autoconnect-priority 50

if [ "$(cat "/sys/class/net/$IF/carrier" 2>/dev/null)" = 1 ]; then
  nmcli connection up "$PROFILE" >/dev/null && echo "Active: $IF = $HOST_IP/24"
else
  echo "No link on $IF yet. The profile activates by itself when the hand's connection box is plugged in and on."
fi
