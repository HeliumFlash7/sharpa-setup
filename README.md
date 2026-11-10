# Sharpa Wave W01 setup

Step-by-step setup of a **Sharpa Wave W01** dexterous hand on Ubuntu. It covers installing Sharpa Pilot and
the SDK, connecting and calibrating the hand, moving it from Pilot and from Python, and teleoperating it with
**Manus MetaGloves Pro**.

Tested on Ubuntu 24.04 with a right hand, firmware 3.0.6, Sharpa Pilot 2.0.11 (SDK 5.0.11), and
sharpa-manus-sdk v1.0.1.

> Community project, not affiliated with Sharpa or Manus. Their software is proprietary. It is downloaded
> from the official GitHub releases by `scripts/fetch_vendor.sh` and is not part of this repository.

**Steps:** [1 Get the files](#1-get-the-files) · [2 Install Pilot](#2-install-sharpa-pilot-) ·
[3 Connect the hand](#3-connect-the-hand) · [4 Calibrate and move](#4-calibrate-and-move-it-in-pilot) ·
[5 Python](#5-move-it-from-python-optional) · [6 Teleop setup](#6-teleop-setup-one-time) ·
[7 Teleop](#7-teleop-every-session) · [Troubleshooting](docs/troubleshooting.md) · [Reference](docs/reference.md)

## Before you start

| You need | Notes |
|---|---|
| Sharpa Wave W01, connection box, power adapter, Ethernet cable | Hand mounted on its base, on a stable table |
| PC: Ubuntu 22.04 / 24.04, x86_64, a free gigabit Ethernet port | Wi-Fi and internet keep working alongside |
| `git`, `curl`, `python3` (3.10–3.13), NetworkManager | `sudo apt install git curl` if missing |
| For teleop: Manus MetaGloves Pro and their USB dongle; [Miniforge](https://github.com/conda-forge/miniforge) (conda) | Our dongle carried the license, so the separate license-key stick wasn't needed. Plug it in if yours doesn't. |
| About 8 GB of disk | The Pilot `.deb` (1 GB) can be deleted after installing |

| Official resources | |
|---|---|
| User manual (authoritative) | https://sharpa-robotics.github.io/sharpa-docs/ (embedded at https://www.sharpa.com/pages/documentation) |
| Downloads | https://www.sharpa.com/pages/downloads (links to the GitHub releases) |
| GitHub | https://github.com/sharpa-robotics |
| Support | support@sharpa.com |

Run all commands from the repository root. 🔑 marks a command that needs `sudo`.

## 1. Get the files

```bash
git clone https://github.com/HeliumFlash7/sharpa-setup.git && cd sharpa-setup
bash scripts/fetch_vendor.sh
```

This downloads Sharpa Pilot 2.0.11 and sharpa-manus-sdk v1.0.1 (about 1.2 GB) into `vendor/`, checks
their SHA-256 and unpacks them. Options:

- No gloves: add `--no-manus` (downloads Pilot only). `scripts/hand_status.py` then won't work, because it uses a parser from the Manus package.
- Manus MetaGloves Pro **Haptics**: add `--haptics` (see [Reference](docs/reference.md#haptic-gloves)).

## 2. Install Sharpa Pilot 🔑

Pilot ships with the matching Sharpa Wave SDK and installs it to `/opt/sharpa-wave-sdk`. Don't install
the SDK separately.

```bash
sudo apt install ./vendor/downloads/sharpa-pilot_2.0.11_amd64_linux.deb
```

The SDK finishes installing in the background about 30 s after `apt` returns. Then check:

```bash
cat /opt/sharpa-wave-sdk/VERSION          # VERSION=5.0.11
```

## 3. Connect the hand

1. With the power **off**, plug in the cables:
   - Wrist cable from the hand to the connection box: align the key, push straight in, tighten the nut.
   - Ethernet from the connection box **directly** to the PC, with no switch.
   - Power adapter last.
2. Give the PC's Ethernet port the address the hand expects:
   ```bash
   bash scripts/setup_network.sh            # Ethernet -> 192.168.10.240/24, no gateway
   ```
   If the PC has several wired ports, name the one the hand is on: `bash scripts/setup_network.sh <interface>`
   (list them with `nmcli device`). This port then stays dedicated to the hand. Undo with
   `nmcli connection delete sharpa-w01`.
   The hand has a fixed IP (right `192.168.10.20`, left `192.168.10.10`) and no DHCP server, and it streams
   tactile data to `192.168.10.240`. Without this step, Ubuntu shows "no wired connection". For the
   manual equivalent, see the [Reference](docs/reference.md#network).
3. Power **on**. **Don't touch the fingertips for 20 s**, because the tactile sensors zero during boot.
   The rear LED **breathing cyan** means ready. Yellow or red means a fault: see [Troubleshooting](docs/troubleshooting.md).
4. Disconnect any VPN, then check:
   ```bash
   bash scripts/check_hand.sh               # expect: link 1000 Mb/s, 192.168.10.240/24, hand answers ping
   ```

## 4. Calibrate and move it in Pilot

1. Run `sharpa-pilot`. A device card appears, showing the serial, side and firmware.
2. **Calib** → **Start Calibration**. The hand moves by itself for about 95 s, so keep the area clear.
   **Do this after every power-on.**
3. **Sliders:** move one joint a little and back. **Replay:** play a preset such as `Gestures`.

If Pilot offers a firmware update, follow it. Manual: *Get Started*, sections 4–8.

## 5. Move it from Python (optional)

**Close Pilot first**, because only one program can control the hand.

```bash
python3 scripts/first_move.py            # read-only: serial, firmware, fault codes, 22 joint angles
python3 scripts/first_move.py --move     # after you type "yes": flexes one finger at a time by 25°, slowly
```

- Ctrl-C returns the hand to zero.
- `--mock` runs without hardware.
- Sharpa's own sample, `python3 /opt/sharpa-wave-sdk/sample/python/sharpa_wave_example.py`, **immediately sweeps
  17 joints through their full range** three times. Clear the area first.
- API: manual, *Development → Python SDK Guide* (summary in the [Reference](docs/reference.md#python-sdk)).

## 6. Teleop setup (one time)

The glove streams to a USB dongle. Sharpa's **client** reads it through the Manus SDK (no MANUS Core or Windows
needed). Sharpa's **retargeting** turns the hand pose into 22 joint angles and sends them to the robot as a
"virtual glove". Pilot then hands control to it. [Details](docs/reference.md#teleop-pipeline).

1. 🔑 Install the system packages and the USB permission for the dongle, then unplug and replug the dongle:
   ```bash
   sudo bash scripts/install_teleop_deps.sh
   ```
2. Create the conda env and build the calibration GUI and the pairing tool:
   ```bash
   bash scripts/setup_teleop.sh
   ```
3. Plug in the dongle and switch the glove on. If the glove LED is **solid blue**, it is paired already:
   go to step 4. Otherwise put it in pairing mode: hold its switch to the right until the LED **blinks white**.
   Then run:
   ```bash
   bash scripts/teleop.sh pair              # stops once every glove it sees shows state=Paired (max 60 s)
   ```
   The pairing is stored on the glove, so this is needed only once.
4. **Calibrate the gloves for each operator.** The shipped calibration belongs to someone else.
   ```bash
   bash scripts/teleop.sh calibrate <your-name>
   ```
   In the GUI, click **Right Glove** (or **Left Glove**) and do the following:
   1. Hand flat, thumb out → **F5**, hold about 5 s.
   2. Make a fist → **F9**, hold about 5 s → **F9**.
   3. Touch your fingertips to the base of your palm, repeatedly → **F9** when prompted.
   4. Move your thumb to the base of your pinky and back out, repeatedly. When "Calibration Complete" appears → **F9**.

   Close the GUI. The calibration is saved to `calib/<your-name>/` and becomes active. Later, to switch back
   to it: `bash scripts/teleop.sh use <your-name>`.
5. Dry run without the robot, in two terminals:
   ```bash
   bash scripts/teleop.sh client            # terminal A: wait for "... Right is published"
   bash scripts/teleop.sh plot              # terminal B: blue dashed = your hand, red = robot hand
   ```
   Make a fist, pinch, spread your fingers. If the red hand looks wrong, recalibrate.
   To stop: Ctrl-C in B, then Space in A.

To check the whole stack at any time: `bash scripts/teleop.sh check`.

## 7. Teleop (every session)

1. **Hand:** power on, keep the fingertips free for 20 s, wait for the LED to breathe cyan.
2. **Pilot:** device card → **Calib** → **Start Calibration** (about 95 s). In the bottom bar, set
   **Control Source = APP**.
3. **Glove:** dongle in, glove on, LED solid blue.
4. **Terminal A:** `bash scripts/teleop.sh client`. Wait for `... Right is published`.
5. **Terminal B:** `bash scripts/teleop.sh wave`.
6. **Pilot:** wait until the **Right Glove** card shows **Online**. Hold your hand open and still, then set
   **Control Source → GLOVE**. The hand now follows your glove.

**Stop, in this order:**
1. Pilot → **APP**.
2. Terminal B: **Ctrl-C**.
3. Terminal A: **Space**.
4. Switch the glove off and charge it (USB-C).

> If anything looks wrong, switch Pilot back to **APP** first.

## Repository layout

```
scripts/
  fetch_vendor.sh          download + verify + unpack the vendor software into vendor/
  setup_network.sh         Ethernet profile "sharpa-w01" = 192.168.10.240/24
  check_hand.sh            read-only checks: Pilot/SDK, link, IP, route/VPN, firewall, ping
  first_move.py            SDK test: read-only by default, --move = gentle per-finger flex (--mock = no hardware)
  hand_status.py           firmware + fault code from the hand's heartbeat (safe while Pilot runs)
  install_teleop_deps.sh   (sudo) packages + udev rule for the Manus dongle
  setup_teleop.sh          conda env, calibration GUI, manus_pair
  teleop.sh                client | wave | plot | watch | calibrate | use | pair | check
  check_teleop.sh          read-only checks of the teleop stack
  watch_hand_action.py     print the retargeted joint angles (read-only)
  mock_sharpa.py           stand-in for the SDK, used by --mock
tools/manus_pair/          pair Manus gloves to the dongle on Linux (Manus SDK, Integrated mode)
docs/                      troubleshooting.md, reference.md
vendor/  calib/  logs/     local only (gitignored): vendor software, glove calibrations, test reports
```

## License

The scripts and docs in this repository are MIT licensed ([LICENSE](LICENSE)). Sharpa Pilot, the Sharpa Wave
SDK, sharpa-manus-sdk and the Manus SDK are proprietary and covered by their own licenses. Never commit
`vendor/`.
