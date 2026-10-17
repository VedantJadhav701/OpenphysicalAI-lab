"""Scripted skills (assistance level A3). A skill receives target coordinates from the AGENT's
world estimate (not simulator truth) and executes through real MuJoCo physics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .sim import FINGER_CLOSED, FINGER_OPEN, IKError, World

SAFE_Z = 0.18


@dataclass
class SkillResult:
    ok: bool
    reason: str = ""


def pick(w: World, x: float, y: float, half: float, yaw: float, on_tick: Optional[Callable] = None,
         drop_hook: Optional[Callable] = None) -> SkillResult:
    gz = max(0.034, half + 0.014)
    try:
        w.set_gripper(max(0.0, 0.04 - half))      # pre-shape: open just wide enough (keeps pads clear of walls)
        w.move_to(x, y, SAFE_Z, yaw, speed=0.45, on_tick=on_tick)
        w.move_to(x, y, gz, yaw, speed=0.20, on_tick=on_tick)
        w.set_gripper(FINGER_CLOSED)
        w.settle(0.5)
        if drop_hook:
            drop_hook()   # failure injection point (grasp slips)
        w.move_to(x, y, SAFE_Z, yaw, speed=0.25, on_tick=on_tick)
    except IKError as e:
        return SkillResult(False, f"controller_fail: {e}")
    return SkillResult(True)


def place(w: World, x: float, y: float, on_tick: Optional[Callable] = None) -> SkillResult:
    try:
        w.move_to(x, y, SAFE_Z, 0.0, speed=0.35, on_tick=on_tick)
        w.move_to(x, y, 0.12, 0.0, speed=0.20, on_tick=on_tick)
        w.set_gripper(FINGER_OPEN)
        w.settle(0.5)
        w.move_to(x, y, SAFE_Z, 0.0, speed=0.35, on_tick=on_tick)
    except IKError as e:
        return SkillResult(False, f"controller_fail: {e}")
    return SkillResult(True)


def go_home(w: World, on_tick: Optional[Callable] = None):
    w.set_gripper(FINGER_OPEN)
    w.move_to(0.20, 0.0, 0.22, 0.0, speed=0.5, on_tick=on_tick)
