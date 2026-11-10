#!/usr/bin/env python3
"""Print each Sharpa Wave's serial, firmware and fault code by listening to its UDP heartbeat
(port 54321). It only listens: no SDK, nothing sent, so it is safe while Sharpa Pilot runs.
Look the fault code up in the manual: Support > Troubleshooting (FaultCode, device level).

    python3 -I scripts/hand_status.py [--seconds 4]

Uses the heartbeat parser shipped in sharpa-manus-sdk (vendor/, see scripts/fetch_vendor.sh).
"""
import argparse
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get("SHARPA_MANUS_SDK", ROOT / "vendor/sharpa-manus-sdk-1.0.1"))
inc = sorted(SDK.glob("retargeting_alg_release_V*/include"))
if not inc:
    sys.exit(f"Heartbeat parser not found under {SDK}. Run: bash scripts/fetch_vendor.sh")
sys.path.insert(0, str(inc[-1]))
from heartbeat_wave import HeartbeatWAVE  # noqa: E402  (Sharpa's heartbeat packet parser)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--seconds", type=float, default=4.0)
args = ap.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
try:
    s.bind(("0.0.0.0", 54321))
except OSError as e:
    sys.exit(f"Cannot listen on UDP 54321 ({e}). Another program holds the port exclusively; read the fault code in Pilot.")
s.settimeout(1.0)
seen, t0 = {}, time.time()
while time.time() - t0 < args.seconds:
    try:
        data, addr = s.recvfrom(4096)
        p = HeartbeatWAVE.unpack(data)._asdict()
    except Exception:  # timeouts and packets that aren't hand heartbeats
        continue
    sn = p["device_sn"]
    sn = sn.decode(errors="ignore").strip("\x00") if isinstance(sn, bytes) else str(sn)
    if sn.startswith("Glove"):  # virtual gloves from the teleop retargeting
        continue
    code = p["status"]["error_code"]
    fw = ".".join(map(str, p["firmware_version"][:3]))
    seen[addr[0]] = f"sn={sn} fw={fw} fault=0x{code:04X} {'(none)' if code == 0 else '<- look up in the manual'}"
for ip, txt in sorted(seen.items()):
    print(ip, txt)
if not seen:
    print(f"No hand heartbeat in {args.seconds:.0f} s. Hand powered? Network up? (bash scripts/check_hand.sh)")
    sys.exit(1)
