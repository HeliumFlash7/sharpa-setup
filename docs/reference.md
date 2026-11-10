# Reference

Facts the setup relies on. The [official manual](https://sharpa-robotics.github.io/sharpa-docs/) is authoritative.

## Versions

| Item | Tested here | Newer, untested | Where |
|---|---|---|---|
| Sharpa Pilot (bundles the SDK) | 2.0.11 (SDK 5.0.11) | 2.1.0 (2026-11-06) | https://github.com/sharpa-robotics/sharpa-wave/releases |
| Hand firmware | 3.0.6 | 3.0.11 (Pilot 2.0.11's matched version) | flash through Pilot; images at https://github.com/sharpa-robotics/sharpa-wave-firmware/releases |
| sharpa-manus-sdk | v1.0.1 (MetaGloves Pro) | v1.2.0 (Pro Haptics only) | https://github.com/sharpa-robotics/sharpa-manus-sdk/releases |

To use a newer Pilot, install its `.deb` instead. Upgrading or reinstalling Pilot is the only supported way
to change the SDK. Don't edit `/opt/sharpa-wave-sdk`.

## Network

| | Left hand | Right hand |
|---|---|---|
| Hand IP | 192.168.10.10 | 192.168.10.20 |
| Host PC IP (the hand's tactile destination) | 192.168.10.240 | 192.168.10.240 |
| Heartbeat / discovery | UDP 54321 | UDP 54321 |
| Tactile stream | UDP 50011 | UDP 50001 |
| Subnet | 255.255.255.0 | 255.255.255.0 |

`scripts/setup_network.sh` creates NetworkManager profile `sharpa-w01`: Ethernet IPv4 manual
`192.168.10.240/24`, no gateway, no DNS, never the default route, IPv6 off, autoconnect. Undo with
`nmcli connection delete sharpa-w01`. To do the same by hand:
**Settings → Network → Wired → ⚙ → IPv4 → Manual**, address `192.168.10.240`, netmask `255.255.255.0`, gateway
empty. Then tick "Use this connection only for resources on its network" under **IPv4**.

- Rear button: press **2×** to restart, **3×** to reset the network and control settings to the defaults above.
- Use gigabit Ethernet, connected directly. 180 Hz tactile data needs 1000BASE-T.

## Rear LED

| LED | Meaning |
|---|---|
| Breathing cyan | Initialized, ready |
| Solid white | Enabled and operating |
| Solid yellow | Warning: read the fault code |
| Solid red | Error: stop, read the fault code |
| Flashing red | Critical: stop immediately, contact support@sharpa.com |

Connection box LED solid green = power OK. Read the fault code with Pilot, or without disturbing Pilot with
`python3 scripts/hand_status.py`. Look it up in the manual: *Support → Troubleshooting → FaultCode (Device Level)*.

## Control

- **Control source:** only one commands the hand at a time. Set it in Pilot's bottom bar.
  - `APP` = Pilot
  - `SDK` = your code
  - `GLOVE` = teleop
  - `IDLE`
- **Control modes:** `POSITION` (default), `ZERO_FORCE` (back-drivable), `ADMITTANCE`, `MIT`.
- **Calibrate joints in Pilot after every power-on.**
- **Safety:**
  - Fingertip load: < 50 N normal, < 30 N shear.
  - No sharp objects, no liquids (IP20).
  - Avoid command jumps > 20° per frame.

### Joint order (SDK order, 22 joints)

```
 0 thumb_CMC_FE   1 thumb_CMC_AA   2 thumb_MCP_FE   3 thumb_MCP_AA   4 thumb_IP
 5 index_MCP_FE   6 index_MCP_AA   7 index_PIP      8 index_DIP
 9 middle_MCP_FE 10 middle_MCP_AA 11 middle_PIP    12 middle_DIP
13 ring_MCP_FE   14 ring_MCP_AA   15 ring_PIP      16 ring_DIP
17 pinky_CMC     18 pinky_MCP_FE  19 pinky_MCP_AA  20 pinky_PIP     21 pinky_DIP
```

All zeros = the calibrated open hand. Ranges are in the manual (*Overview → Specifications → Range of Motion*)
and in `scripts/first_move.py`.

### Python SDK

```python
import sys; sys.path.insert(0, "/opt/sharpa-wave-sdk/python")      # Python 3.10-3.13
from sharpa import SharpaWaveManager, ControlMode, ControlSource
mgr = SharpaWaveManager.get_instance()                             # wait ~1 s for discovery
sn = mgr.get_all_device_sn()[0]
wave = mgr.connect(sn)
wave.start()
while not wave.is_hand_ready(): pass
wave.set_control_mode(ControlMode.POSITION)
wave.set_speed_coeff(0.3); wave.set_current_coeff(0.6)
wave.set_control_source(ControlSource.SDK)
wave.set_joint_position(q_rad_22, True)                            # True = interpolate
err, q_deg = wave.get_joint_position_degree()
faults = wave.get_fault_code()                                     # {FaultCode: [indices]}
wave.stop(); mgr.disconnect_all()
```

Every setter returns an `Error`, where `err.code == 0` means OK. Getters return `(Error, value)`. Pilot and the
SDK share ports, so close Pilot before running SDK code.

## Teleop pipeline

```
glove ──2.4 GHz──▶ USB dongle (ours carries the Manus license; else also plug in the license key)
  ▼
[A] teleop.sh client   SharpaManusClient.out: Manus SDK "Integrated" mode (no MANUS Core), applies
                       Calibration_{left,right}.mcal, publishes 25 keypoints per hand
                       ZMQ tcp://127.0.0.1:2044 (protobuf MocapKeypoints)
  ▼
[B] teleop.sh wave     retargeting_manus_demo_multiprocess.py: 22 joint angles per hand (CasADi optimizer)
                       ZMQ tcp://*:6668 (protobuf HandAction, read by `teleop.sh watch`)
                       -wave: acts as a virtual glove: heartbeats on UDP 54321, joints on UDP 50030 (right)
                       / 50020 (left), broadcast to 192.168.10.255
  ▼
Sharpa Wave            follows the glove while Pilot's control source is GLOVE
```

- The `-glove_left_ip 192.168.10.98 -glove_right_ip 192.168.10.99` values in `teleop.sh` are only the
  names Pilot shows for the virtual gloves. They must be free `192.168.10.x` addresses. They are not
  assigned to the PC.
- **Left hand:** the same steps work. Calibrate the left glove too and pick the **Left Glove** card in Pilot.
  Both virtual gloves always appear; an unused one is harmless.

Useful retargeting options. Pass them after `teleop.sh wave` or `teleop.sh plot`:

| Option | Default | Meaning |
|---|---|---|
| `-filter_alpha` | 1.0 | Output low-pass, 0–1; lower is smoother. Sharpa recommends 0.2–0.5 for jerky motion |
| `-smoother_hz` / `-smoother_w` / `-smoother_z` | 250 / 100 / 0.2 | Second-order smoother before sending |
| `-plot_orientation` | off | Also plot the keypoint orientations (only with `teleop.sh plot`; there is no plot while driving hardware) |
| `-mocap_address` / `-hand_action_address` | `tcp://localhost:2044` / `tcp://*:6668` | ZMQ endpoints |

Sharpa's own guide is `SharpaWave with Manus User Manual.pdf` inside the package
(`vendor/sharpa-manus-sdk-1.0.1/`).

## Haptic gloves

For **MetaGloves Pro Haptics** only (fingertip vibration from the hand's tactile forces). Untested here.

```bash
bash scripts/fetch_vendor.sh --haptics
export SHARPA_MANUS_SDK=$PWD/vendor/sharpa-manus-sdk-1.2.0-haptics    # in every terminal (or ~/.bashrc)
(cd $SHARPA_MANUS_SDK/client && make all)                               # v1.2.0 ships no prebuilt client
bash scripts/setup_teleop.sh
bash scripts/teleop.sh wave -haptics
```

The haptics bridge reads the tactile ports (UDP 50001 / 50011), which Pilot holds. So set the control source
to GLOVE in Pilot first, then **close Pilot**. Details: the package's `README.md`.
