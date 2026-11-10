#!/usr/bin/env python3
"""Print the joint angles the teleop retargeting publishes (ZMQ tcp://*:6668, protobuf HandAction),
in degrees, plus the message rate and the range seen per joint. Read-only: never talks to the robot.

    bash scripts/teleop.sh watch [--seconds 15] [--hand right|left]

Uses the protobuf module shipped in sharpa-manus-sdk (vendor/, see scripts/fetch_vendor.sh).
"""
import argparse
import math
import os
import sys
import time
from pathlib import Path

import zmq

ROOT = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get("SHARPA_MANUS_SDK", ROOT / "vendor/sharpa-manus-sdk-1.0.1"))
proto = sorted(SDK.glob("retargeting_alg_release_V*/include/proto_hand"))
if not proto:
    sys.exit(f"Protobuf module not found under {SDK}. Run: bash scripts/fetch_vendor.sh")
sys.path.insert(0, str(proto[-1]))
import sharpa_hand_pb2  # noqa: E402

# SDK joint order (manual: User Guide > Hand Control > Joint Order Definitions)
SHORT = ["thCMCfe", "thCMCaa", "thMCPfe", "thMCPaa", "thIP", "ixMCP", "ixAA", "ixPIP", "ixDIP",
         "mdMCP", "mdAA", "mdPIP", "mdDIP", "rgMCP", "rgAA", "rgPIP", "rgDIP",
         "pkCMC", "pkMCP", "pkAA", "pkPIP", "pkDIP"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--address", default="tcp://localhost:6668")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--every", type=float, default=1.0, help="print period [s]")
    ap.add_argument("--hand", choices=["right", "left"], default="right")
    args = ap.parse_args()

    sock = zmq.Context().socket(zmq.SUB)
    sock.connect(args.address)
    sock.setsockopt_string(zmq.SUBSCRIBE, "")
    sock.setsockopt(zmq.RCVTIMEO, 500)
    t0 = last = time.time()
    n, lo, hi = 0, [math.inf] * 22, [-math.inf] * 22
    while time.time() - t0 < args.seconds:
        try:
            payload = sock.recv()
        except zmq.Again:
            continue
        msg = sharpa_hand_pb2.HandAction()
        msg.ParseFromString(payload)
        q = [math.degrees(x) for x in getattr(msg, f"joint_{args.hand}").position]
        if len(q) != 22:
            continue
        n += 1
        lo = [min(a, b) for a, b in zip(lo, q)]
        hi = [max(a, b) for a, b in zip(hi, q)]
        if time.time() - last >= args.every:
            last = time.time()
            print(f"[{last - t0:5.1f}s] " + " ".join(f"{s}={v:5.1f}" for s, v in zip(SHORT, q)), flush=True)
    dt = time.time() - t0
    print(f"\n{n} {args.hand}-hand messages in {dt:.1f} s ({n / dt:.0f} Hz)")
    if n:
        print("range per joint [deg]: " + "  ".join(f"{s}:{a:.0f}..{b:.0f}" for s, a, b in zip(SHORT, lo, hi)))
    else:
        print("Nothing received. Are the client and `teleop.sh plot` / `teleop.sh wave` running?")


if __name__ == "__main__":
    main()
