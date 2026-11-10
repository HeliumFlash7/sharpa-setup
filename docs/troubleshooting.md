# Troubleshooting

Check first: `bash scripts/check_hand.sh` for the hand and network, `bash scripts/teleop.sh check` for teleop.
Manual: *Support → Troubleshooting*.

## Hand and network

| Symptom | Fix |
|---|---|
| Ubuntu says "no wired connection" | Expected without the static IP: `bash scripts/setup_network.sh` |
| No link on the Ethernet port | Connection box LED green? Cable seated at both ends? Try another cable or port. |
| Link, but no ping | Waited 20 s after power-on? LED cyan? VPN disconnected (`check_hand.sh` shows the route)? `nmcli connection up sharpa-w01` (or rerun `setup_network.sh`). If the hand's IP was changed, press the rear button 3× to reset it. |
| Ping works, Pilot finds no hand | Firewall: `sudo ufw status`, then `sudo ufw allow in on <interface>`. Restart Pilot. |
| `/opt/sharpa-wave-sdk` missing after installing Pilot | Wait 30 s. Check `/var/log/sharpa-pilot-bundled-sdk.log`. |
| `import sharpa` fails | Use Python 3.10–3.13 and `sys.path.insert(0, "/opt/sharpa-wave-sdk/python")` |
| Hand found but doesn't move from code | Close Pilot. Then check: control source SDK, mode POSITION, `is_hand_ready()`, a 22-element command, fault codes |
| A joint is off / not zero at rest | Recalibrate in Pilot. If it persists, power-cycle and read the fault code. |
| Weak grip | Raise the current coeff (0.5–1.0). Check for thermal warnings and let the hand cool. |
| Tactile rate low or zero | Gigabit link? Recalibrate tactile in Pilot. Only one program can read tactile data. |

## Rear LED yellow / red

Read the fault code (safe while Pilot runs):

```bash
python3 scripts/hand_status.py        # e.g. 192.168.10.20 sn=... fw=3.0.6 fault=0x0000 (none)
```

| Fault code (seen here) | Meaning | Fix |
|---|---|---|
| 0x0501 | Joint angle limit exceeded (warning) | Usually before calibration: run **Calib** in Pilot |
| 0x0702 | Tactile config write error (warning) | Power cycle (rear button 2×), then recalibrate. If it returns, update the firmware via Pilot. |

All codes: manual, *Support → Troubleshooting → FaultCode (Device Level)*. Flashing red = critical: stop and contact support@sharpa.com.

## Gloves and teleop

| Symptom | Fix |
|---|---|
| Glove LED blinking white | Unpaired: `bash scripts/teleop.sh pair` (close the client and the calibration GUI first) |
| Glove LED breathing blue | Connecting: dongle plugged in? Glove near the dongle? Otherwise pair again. |
| Client prints no `... is published` | Dongle in `lsusb` (vendor 3325)? udev rule installed (`install_teleop_deps.sh`) and dongle replugged? Glove LED solid blue? "No compatible license": plug in the Manus license key too. |
| `teleop.sh` says the dongle is in use | Only one of client / calibration GUI / `manus_pair` can run at a time |
| Robot fingers don't match yours | Calibrate for this operator (`teleop.sh calibrate <name>`), then restart the client |
| No glove card in Pilot | `teleop.sh wave` running? PC still on 192.168.10.240 (`check_hand.sh`)? Firewall blocking UDP broadcast? |
| Glove card online, hand doesn't move | Pilot control source = **GLOVE**? Hand calibrated this power-on? LED not yellow/red? |
| Jerky motion | `bash scripts/teleop.sh wave -filter_alpha 0.3`. Close heavy programs. |
| Repeated `CasADi Inf` messages | No valid data for one hand (glove off or unpaired). Harmless for an unused hand. |
| Client fails to start on another Ubuntu version | Rebuild it: `(cd vendor/sharpa-manus-sdk-1.0.1/client && make clean && make all)` |
