#!/usr/bin/env python3
"""First motion from code: find the Sharpa Wave W01, read it, then optionally move it gently.

Follows the official W01 manual (Development > Python SDK Guide, SDK 5.0.x) and the SDK sample
/opt/sharpa-wave-sdk/sample/python/sharpa_wave_example.py. Only the standard library is needed,
so any Python 3.10-3.13 works (the versions the SDK ships builds for).

    python3 scripts/first_move.py                    # READ-ONLY: discover, connect, info, faults, angles
    python3 scripts/first_move.py --move             # + flex one finger at a time by --amp degrees
    python3 scripts/first_move.py --mock --move --yes   # no hardware

Before --move: joints calibrated in Sharpa Pilot (Calib panel) after this power-on, the hand
mounted on its base, nothing within reach of the fingers, and Sharpa Pilot CLOSED (only one control
source may command the hand). Motion is slow (speed coeff 0.2), low-current (0.5), small (25 deg),
and every frame step is far below the manual's "avoid > 20 deg per frame" limit.
Ctrl-C at any time ramps the hand back to the zero pose and disconnects.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE.parent / "logs"
DEFAULT_SDK_PYTHON = "/opt/sharpa-wave-sdk/python"

# SDK joint order (W01 manual, User Guide > Hand Control > 4. Joint Order Definitions)
JOINTS = [
    "thumb_CMC_FE", "thumb_CMC_AA", "thumb_MCP_FE", "thumb_MCP_AA", "thumb_IP",
    "index_MCP_FE", "index_MCP_AA", "index_PIP", "index_DIP",
    "middle_MCP_FE", "middle_MCP_AA", "middle_PIP", "middle_DIP",
    "ring_MCP_FE", "ring_MCP_AA", "ring_PIP", "ring_DIP",
    "pinky_CMC", "pinky_MCP_FE", "pinky_MCP_AA", "pinky_PIP", "pinky_DIP",
]
N = len(JOINTS)
# Range of motion in degrees (W01 manual, Overview > Specifications > 4. Range of Motion)
_TH = [(-5, 105), (-18, 18), (-25, 75), (-18, 18), (0, 95)]
_FI = [(-10, 84), (-18, 18), (0, 95), (0, 75)]
LIMITS_DEG = _TH + _FI * 3 + [(0, 25)] + _FI
assert len(LIMITS_DEG) == N

# One flexion joint per finger: each is moved alone, from the zero pose, so nothing can collide.
TEST_JOINTS = ["index_MCP_FE", "middle_MCP_FE", "ring_MCP_FE", "pinky_MCP_FE", "thumb_IP", "thumb_CMC_FE"]


# ---------------------------------------------------------------------------------------------
def log(msg: str = "") -> None:
    print(msg, flush=True)


def ok(ret) -> bool:
    """SDK convention: Error with code == 0, or (Error, value), or a bool."""
    if isinstance(ret, tuple):
        ret = ret[0]
    if hasattr(ret, "code"):
        return ret.code == 0
    return bool(ret)


def err_text(ret) -> str:
    e = ret[0] if isinstance(ret, tuple) else ret
    return f"code={getattr(e, 'code', '?')} message={getattr(e, 'message', e)}"


def try_call(obj, name, *args):
    """Call an optional SDK method; return (available, result_or_exception_text)."""
    fn = getattr(obj, name, None)
    if fn is None:
        return False, "<not in this SDK>"
    try:
        return True, fn(*args)
    except Exception as e:  # bindings may raise on unsupported calls
        return True, f"<raised {type(e).__name__}: {e}>"


def must(ret, what: str) -> None:
    if not ok(ret):
        raise RuntimeError(f"{what} failed: {err_text(ret)}")


def public_fields(o) -> dict:
    out = {}
    for k in dir(o):
        if k.startswith("_"):
            continue
        try:
            v = getattr(o, k)
        except Exception as e:
            v = f"<{e}>"
        if not callable(v):
            out[k] = str(v)
    return out


def clip_deg(q):
    return [min(max(x, lo), hi) for x, (lo, hi) in zip(q, LIMITS_DEG)]


# ---------------------------------------------------------------------------------------------
def load_sdk(args):
    if args.mock:
        sys.path.insert(0, str(HERE))
        return importlib.import_module("mock_sharpa")
    if sys.version_info[:2] not in ((3, 10), (3, 11), (3, 12), (3, 13)):
        log(f"WARNING: Python {sys.version.split()[0]}; the SDK ships builds for 3.10-3.13 only.")
    sys.path.insert(0, args.sdk_path)
    try:
        return importlib.import_module("sharpa")
    except ImportError as e:
        raise SystemExit(
            f"Cannot import the Sharpa SDK from {args.sdk_path} ({e}).\n"
            "  * Install Sharpa Pilot (it installs the matching SDK to /opt/sharpa-wave-sdk), README step 2\n"
            "  * Use Python 3.10-3.13\n  * Or run with --mock")


def read_angles_deg(hand):
    avail, ret = try_call(hand, "get_joint_position_degree")
    if avail and isinstance(ret, tuple) and ok(ret):
        return [float(x) for x in ret[1]]
    return [math.degrees(float(x)) for x in hand.get_states().angles]


def send_deg(hand, q_deg) -> None:
    q = clip_deg(q_deg)
    must(hand.set_joint_position([math.radians(x) for x in q], True), "set_joint_position")


def ramp(hand, q_from, q_to, seconds: float, rate: float) -> None:
    """Smooth (cosine) ramp, streamed at `rate` Hz like the official sample (100 Hz)."""
    n = max(2, int(seconds * rate))
    for k in range(1, n + 1):
        s = 0.5 - 0.5 * math.cos(math.pi * k / n)
        send_deg(hand, [a + s * (b - a) for a, b in zip(q_from, q_to)])
        time.sleep(1.0 / rate)


def print_angles(q, title: str) -> None:
    log(title)
    for i in range(0, N, 2):
        row = []
        for j in (i, i + 1):
            if j < N:
                lo, hi = LIMITS_DEG[j]
                flag = "  <-- outside spec range" if not (lo - 2 <= q[j] <= hi + 2) else ""
                row.append(f"  [{j:2d}] {JOINTS[j]:<14} {q[j]:7.2f} deg{flag}")
        log("".join(f"{r:<52}" for r in row))


# ---------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="use scripts/mock_sharpa.py instead of the SDK")
    ap.add_argument("--sdk-path", default=DEFAULT_SDK_PYTHON)
    ap.add_argument("--sn", default=None, help="serial number (default: the only hand found)")
    ap.add_argument("--timeout", type=float, default=20.0, help="seconds to wait for discovery / readiness")
    ap.add_argument("--move", action="store_true", help="actually move the hand (default: read-only)")
    ap.add_argument("--yes", action="store_true", help="skip the typed 'yes' confirmation")
    ap.add_argument("--speed", type=float, default=0.2, help="speed coeff (official sample uses 0.3)")
    ap.add_argument("--current", type=float, default=0.5, help="current coeff (official sample uses 0.6)")
    ap.add_argument("--amp", type=float, default=25.0, help="flexion amplitude per test joint [deg]")
    ap.add_argument("--move-time", type=float, default=1.5, help="seconds per ramp")
    ap.add_argument("--hold-time", type=float, default=0.7)
    ap.add_argument("--rate", type=float, default=100.0, help="command rate [Hz]")
    ap.add_argument("--joints", nargs="+", default=TEST_JOINTS, choices=JOINTS)
    ap.add_argument("--ignore-faults", action="store_true", help="allow --move even if fault codes are reported")
    args = ap.parse_args()
    if not (0 < args.speed <= 1 and 0 < args.current <= 1 and 0 < args.amp <= 45):
        raise SystemExit("--speed/--current must be in (0, 1], --amp in (0, 45]")

    report = {"time": dt.datetime.now().isoformat(timespec="seconds"), "mock": args.mock, "argv": sys.argv[1:]}
    sdk = load_sdk(args)
    log(f"[{'MOCK' if args.mock else 'REAL'}] sharpa module: {getattr(sdk, '__file__', '?')}  (Python {sys.version.split()[0]})")

    # 1. discovery ------------------------------------------------------------------------------
    mgr = sdk.SharpaWaveManager.get_instance()
    time.sleep(0 if args.mock else 1.0)          # official sample waits 1 s for discovery
    t0, sns = time.time(), []
    while not sns:
        sns = list(mgr.get_all_device_sn() or [])
        if sns:
            break
        if time.time() - t0 > args.timeout:
            pilot = subprocess.run(["pgrep", "-f", "/opt/sharpa-pilot/sharpa-pilot"], capture_output=True).returncode == 0
            raise SystemExit("No hand discovered. " + ("Sharpa Pilot is running: close it first. " if pilot else "") +
                             "Run: bash scripts/check_hand.sh (network, VPN, firewall); see docs/troubleshooting.md.")
        log("  ... no device yet")
        time.sleep(1.0)
    log(f"Discovered: {sns}")
    report["discovered"] = sns
    avail, devs = try_call(mgr, "get_all_devices")
    if avail and isinstance(devs, (list, tuple)):
        report["devices"] = [public_fields(d) for d in devs]
        for d in report["devices"]:
            log(f"  device: {d}")
    if args.sn is None and len(sns) > 1:
        raise SystemExit(f"{len(sns)} hands found; pick one with --sn {{{', '.join(sns)}}}")
    sn = args.sn or sns[0]
    if sn not in sns:
        raise SystemExit(f"--sn {sn} not among {sns}")

    # 2. connect + readiness -------------------------------------------------------------------
    hand = mgr.connect(sn)
    have_control = False
    try:
        log(f"Connected to {sn}; start() -> {hand.start()}")
        if hasattr(hand, "is_hand_ready"):
            t0 = time.time()
            while not hand.is_hand_ready():
                if time.time() - t0 > args.timeout:
                    raise RuntimeError("is_hand_ready() stayed False. Check the rear LED and the fault codes in Sharpa Pilot.")
                time.sleep(0.2)
            log(f"Hand ready after {time.time() - t0:.1f} s")

        # 3. information (read-only) ---------------------------------------------------------
        info = hand.get_device_info()
        report["device_info"] = public_fields(info)
        log("Device info:")
        for k, v in report["device_info"].items():
            log(f"  {k:<22} {v}")
        avail, js = try_call(hand, "get_device_info_json")
        if avail:
            report["device_info_json"] = js
            log(f"Device info JSON: {js}")
        for name in ["get_control_source", "get_control_mode", "get_enable_state", "get_speed_coeff", "get_current_coeff"]:
            avail, ret = try_call(hand, name)
            if avail:
                val = ret[1] if isinstance(ret, tuple) and len(ret) > 1 else ret
                report[name] = str(val)
                log(f"  {name:<22} {val}")
        avail, faults = try_call(hand, "get_fault_code")
        report["faults"] = str(faults)
        known = avail and isinstance(faults, dict)
        n_faults = len(faults) if known else 0
        log(f"Fault codes: {faults if n_faults else 'none'}" if known else f"Fault codes: UNKNOWN ({faults})")

        q_now = read_angles_deg(hand)
        report["angles_deg_at_start"] = q_now
        print_angles(q_now, "Current joint angles (0 deg everywhere = calibrated neutral pose):")
        far = [JOINTS[i] for i, x in enumerate(q_now) if abs(x) > 10]
        if far:
            log(f"Note: {len(far)} joint(s) are > 10 deg from zero: {far}")

        # 4. motion (opt-in) -----------------------------------------------------------------
        if not args.move:
            log("\nRead-only run complete. Add --move for the gentle per-finger test.")
            return 0
        if (n_faults or not known) and not args.ignore_faults:
            raise RuntimeError("Fault codes present or unreadable: check them in Sharpa Pilot first (or pass --ignore-faults).")
        if not (args.mock or args.yes):
            log(f"\n*** The hand will MOVE: ramp to zero pose, then flex {args.joints} by {args.amp:.0f} deg, one at a time,")
            log(f"*** speed {args.speed}, current {args.current}. Sharpa Pilot must be closed. Keep fingers/objects clear.")
            if input("*** Type 'yes' to continue: ").strip().lower() != "yes":
                log("Aborted.")
                return 1

        must(hand.set_control_mode(sdk.ControlMode.POSITION), "set_control_mode(POSITION)")
        must(hand.set_speed_coeff(args.speed), f"set_speed_coeff({args.speed})")
        must(hand.set_current_coeff(args.current), f"set_current_coeff({args.current})")
        must(hand.set_control_source(sdk.ControlSource.SDK), "set_control_source(SDK)")
        have_control = True

        zero = [0.0] * N
        log("Ramping to the zero pose ...")
        ramp(hand, q_now, zero, max(args.move_time, 2.0), args.rate)
        time.sleep(args.hold_time)
        results = []
        for name in args.joints:
            j = JOINTS.index(name)
            tgt = list(zero)
            tgt[j] = args.amp
            ramp(hand, zero, tgt, args.move_time, args.rate)
            time.sleep(args.hold_time)
            q = read_angles_deg(hand)
            e_j = q[j] - tgt[j]
            e_other = max(abs(q[i] - tgt[i]) for i in range(N) if i != j)
            ramp(hand, tgt, zero, args.move_time, args.rate)
            time.sleep(args.hold_time * 0.5)
            results.append({"joint": name, "target_deg": args.amp, "measured_deg": round(q[j], 2),
                            "error_deg": round(e_j, 2), "max_other_joint_error_deg": round(e_other, 2)})
            log(f"  {name:<14} target {args.amp:5.1f}  measured {q[j]:6.2f}  error {e_j:+6.2f} deg"
                f"   (other joints max |err| {e_other:.2f})")
        report["motion_results"] = results
        worst = max(abs(r["error_deg"]) for r in results)
        log(f"\nMotion test done. Worst tracking error {worst:.2f} deg "
            f"({'OK' if worst < 5 else 'LARGE: check calibration / faults'}).")
        return 0
    except KeyboardInterrupt:
        log("\nCtrl-C")
        return 130
    finally:
        try:
            if have_control:
                log("Returning to the zero pose ...")
                ramp(hand, read_angles_deg(hand), [0.0] * N, 1.5, args.rate)
                time.sleep(0.5)
            hand.stop()
        finally:
            mgr.disconnect_all()
            log("Disconnected.")
            LOG_DIR.mkdir(exist_ok=True)
            out = LOG_DIR / f"first_move_{'mock_' if args.mock else ''}{dt.datetime.now():%Y%m%d_%H%M%S}.json"
            out.write_text(json.dumps(report, indent=1, default=str))
            log(f"Report: {out}")


if __name__ == "__main__":
    raise SystemExit(main())
