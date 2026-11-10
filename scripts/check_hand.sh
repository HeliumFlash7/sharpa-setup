#!/usr/bin/env bash
# Read-only checks before using a Sharpa Wave W01: OS, Pilot/SDK install, Ethernet link, host IP,
# routing (VPN), firewall, and whether the hands answer ping. Changes nothing.
#
#   bash scripts/check_hand.sh [interface]
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
FAIL=0
fail() { bad "$@"; FAIL=$((FAIL + 1)); }

hdr "Host"
. /etc/os-release
case "$VERSION_ID" in
  22.04|24.04) ok "$PRETTY_NAME" ;;
  *) warn "$PRETTY_NAME (Sharpa supports Ubuntu 22.04 / 24.04)" ;;
esac
[ "$(uname -m)" = x86_64 ] && ok "x86_64" || warn "$(uname -m): the Pilot .deb is amd64-only"

hdr "Sharpa software"
v=$(dpkg-query -W -f='${Status} ${Version}' sharpa-pilot 2>/dev/null)
case "$v" in "install ok installed "*) ok "sharpa-pilot ${v##* }" ;; *) fail "Sharpa Pilot not installed (README step 2)" ;; esac
if [ -f /opt/sharpa-wave-sdk/VERSION ]; then
  ok "SDK $(sed -n 's/^VERSION=//p' /opt/sharpa-wave-sdk/VERSION) in /opt/sharpa-wave-sdk"
  if out=$(python3 -c "import sys; sys.path.insert(0, '/opt/sharpa-wave-sdk/python'); import sharpa" 2>&1); then
    ok "python3 ($(python3 -V 2>&1)) can import sharpa"
  else warn "python3 cannot import sharpa: $(printf '%s' "$out" | tail -n 1) (SDK needs Python 3.10-3.13)"; fi
else
  fail "no /opt/sharpa-wave-sdk (Pilot installs it in the background ~30 s after apt; see /var/log/sharpa-pilot-bundled-sdk.log)"
fi
pgrep -f /opt/sharpa-pilot/sharpa-pilot >/dev/null && info "Sharpa Pilot is running (close it before SDK scripts)"

IF="${1:-$(eth_iface)}"
hdr "Ethernet ${IF:-?}"
if [ -z "$IF" ] || [ ! -d "/sys/class/net/$IF" ]; then
  fail "no Ethernet interface chosen; run: bash scripts/setup_network.sh [interface]"
  echo; echo "Summary: $FAIL problem(s)"; exit 1
fi
if [ "$(cat "/sys/class/net/$IF/carrier" 2>/dev/null)" != 1 ]; then
  fail "no link: cable in the connection box? box LED solid green? hand powered?"
  nmcli connection show "$PROFILE" >/dev/null 2>&1 && info "profile $PROFILE exists; it activates when the link comes up" \
    || fail "no profile $PROFILE yet; run: bash scripts/setup_network.sh $IF"
  echo; echo "Summary: $FAIL problem(s)"; exit 1
fi
sp=$(cat "/sys/class/net/$IF/speed" 2>/dev/null)
[ "${sp:-0}" -ge 1000 ] && ok "link up, $sp Mb/s" || warn "link up but ${sp:-?} Mb/s (tactile data needs gigabit)"
if ip -4 -o addr show dev "$IF" | grep -q " $HOST_IP/24 "; then ok "$IF has $HOST_IP/24"
else fail "$IF does not have $HOST_IP/24; run: bash scripts/setup_network.sh $IF"; fi

hdr "Routing / VPN / firewall"
for side in left right; do
  ipvar=${side^^}_IP; ip=${!ipvar}
  dev=$(ip route get "$ip" 2>/dev/null | grep -o 'dev [^ ]*' | head -1 | cut -d' ' -f2)
  [ "$dev" = "$IF" ] && ok "route to $side hand $ip via $IF" || fail "route to $side hand $ip goes via '${dev:-none}' (a VPN? disconnect it)"
done
vpn=$(ip -br link 2>/dev/null | awk '$1 ~ /^(tun|cscotun|wg|ppp)/ {print $1}' | xargs)
[ -n "$vpn" ] && warn "VPN interface up: $vpn. Disconnect it if the hand is not reachable."
grep -qs "^ENABLED=yes" /etc/ufw/ufw.conf && warn "ufw firewall enabled; if Pilot finds no hand: sudo ufw allow in on $IF"

hdr "Hands"
any=0
for side in left right; do
  ipvar=${side^^}_IP; ip=${!ipvar}
  if ping -c 2 -W 1 -I "$IF" "$ip" >/dev/null 2>&1; then ok "$side hand $ip answers ping"; any=1
  else info "$side hand $ip: no reply"; fi
done
[ $any = 1 ] || fail "no hand answers (powered > 20 s? rear LED breathing cyan? press the rear button 3x to reset its network)"

echo; echo "Summary: $FAIL problem(s)"
exit $((FAIL > 0))
