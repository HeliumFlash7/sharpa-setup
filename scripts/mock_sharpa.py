"""Minimal stand-in for the `sharpa` Python module of Sharpa Wave SDK 5.0.x, for `--mock` runs.

It mirrors only the calls used by first_move.py, with the call shapes documented in the official
W01 manual (Development > Python SDK Guide) and in the SDK 5.0.11 sample
`/opt/sharpa-wave-sdk/sample/python/sharpa_wave_example.py`:

    mgr = SharpaWaveManager.get_instance(); mgr.get_all_device_sn(); mgr.get_all_devices()
    wave = mgr.connect(sn); wave.start() -> bool; wave.is_hand_ready() -> bool
    wave.set_control_source(ControlSource.SDK) -> Error; wave.set_control_mode(ControlMode.POSITION) -> Error
    wave.set_speed_coeff(x) / set_current_coeff(x) -> Error; get_*_coeff() -> (Error, float)
    wave.set_joint_position(list22_rad, enable_interp) -> Error; set_joint_position_degree(list22_deg) -> Error
    wave.get_joint_position_degree() -> (Error, list22); wave.get_states().angles (rad)
    wave.get_fault_code() -> {FaultCode: [indices]}; wave.stop(); mgr.disconnect_all()

Not the real thing: no network, no tactile, joints follow targets with a first-order lag.
"""
from __future__ import annotations

import enum
import json
import math
import threading
import time

IS_MOCK = True
_N = 22


class ControlMode(enum.Enum):
    ZERO_FORCE = 0
    POSITION = 1
    ADMITTANCE = 2
    MIT = 3


class ControlSource(enum.Enum):
    IDLE = 0
    APP = 1
    SDK = 2
    GLOVE = 3


class HandSide(enum.Enum):
    LEFT = 0
    RIGHT = 1


class Error:
    def __init__(self, code: int = 0, message: str = "OK"):
        self.code, self.message = code, message

    def __repr__(self):
        return f"Error(code={self.code}, message={self.message!r})"


class _DeviceInfo:
    def __init__(self, sn, side):
        self.sn = sn
        self.hand_side = side
        self.firmware_version = "mock-3.0.11"
        self.ip = "192.168.10.20" if side == HandSide.RIGHT else "192.168.10.10"


class _States:
    def __init__(self, angles):
        self.angles = angles


class SharpaWave:
    def __init__(self, sn, side):
        self._info = _DeviceInfo(sn, side)
        self._q = [0.0] * _N           # rad
        self._target = [0.0] * _N
        self._speed, self._current = 0.3, 0.6
        self._mode, self._source = ControlMode.POSITION, ControlSource.APP
        self._t_start = None
        self._lock = threading.Lock()
        self._alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._alive:
            with self._lock:
                if self._mode == ControlMode.POSITION:
                    a = min(1.0, 0.08 * self._speed / 0.3)
                    self._q = [q + a * (t - q) for q, t in zip(self._q, self._target)]
            time.sleep(0.002)

    # lifecycle
    def start(self):
        self._t_start = time.time()
        return True

    def stop(self):
        self._t_start = None
        return True

    def is_hand_ready(self):
        return self._t_start is not None and time.time() - self._t_start > 0.5

    # info
    def get_device_info(self):
        return self._info

    def get_device_info_json(self):
        i = self._info
        return json.dumps({"sn": i.sn, "hand_side": i.hand_side.name, "firmware_version": i.firmware_version, "ip": i.ip})

    def get_fault_code(self):
        return {}

    # configuration
    def set_control_source(self, src):
        self._source = src
        return Error()

    def get_control_source(self):
        return Error(), self._source

    def set_control_mode(self, mode):
        self._mode = mode
        return Error()

    def get_control_mode(self):
        return Error(), self._mode

    def get_enable_state(self):
        return Error(), True

    def set_speed_coeff(self, c):
        if not 0.0 < c <= 1.0:
            return Error(1, "speed coeff must be in (0, 1]")
        self._speed = c
        return Error()

    def get_speed_coeff(self):
        return Error(), self._speed

    def set_current_coeff(self, c):
        if not 0.0 < c <= 1.0:
            return Error(1, "current coeff must be in (0, 1]")
        self._current = c
        return Error()

    def get_current_coeff(self):
        return Error(), self._current

    # motion
    def set_joint_position(self, angles_rad, enable_interp=True):
        if len(angles_rad) != _N:
            return Error(1, f"expected {_N} angles, got {len(angles_rad)}")
        if self._source != ControlSource.SDK:
            return Error(2, "control source is not SDK")
        with self._lock:
            self._target = [float(a) for a in angles_rad]
        return Error()

    def set_joint_position_degree(self, angles_deg):
        return self.set_joint_position([math.radians(a) for a in angles_deg])

    def get_joint_position_degree(self):
        with self._lock:
            return Error(), [math.degrees(q) for q in self._q]

    def get_states(self):
        with self._lock:
            return _States(list(self._q))


class SharpaWaveManager:
    _inst = None

    def __init__(self):
        self._hands = {}

    @classmethod
    def get_instance(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def get_all_device_sn(self):
        return ["MOCK-W01-RIGHT"]

    def get_all_devices(self):
        return [_DeviceInfo("MOCK-W01-RIGHT", HandSide.RIGHT)]

    def connect(self, sn):
        self._hands[sn] = SharpaWave(sn, HandSide.LEFT if "LEFT" in sn else HandSide.RIGHT)
        return self._hands[sn]

    def disconnect_all(self):
        for h in self._hands.values():
            h._alive = False
        self._hands.clear()
