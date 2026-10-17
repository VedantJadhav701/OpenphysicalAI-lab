"""MuJoCo world: 5-DOF arm (yaw, shoulder, elbow, wrist pitch, roll) + 2-finger gripper,
table, cubes, open-top container, optional conveyor motion. Analytic IK, Cartesian skills.

All physics is real MuJoCo. Controller commands are joint position targets."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import mujoco
import numpy as np

BASE_XY = (-0.20, 0.0)
H_SHOULDER = 0.15
L1, L2 = 0.34, 0.34
L_TOOL = 0.11          # wrist pivot -> finger pad centre
FINGER_OPEN = 0.0
FINGER_CLOSED = 0.045   # commanded closing (beyond contact => grip force)
WORKSPACE = {"x": (0.10, 0.36), "y": (-0.26, 0.26)}
CONTAINER_HALF_IN = 0.075
WALL_H = 0.05

COLORS = {
    "red": (0.85, 0.15, 0.15), "green": (0.15, 0.7, 0.25), "yellow": (0.92, 0.8, 0.1),
    "blue": (0.15, 0.3, 0.85), "orange": (0.95, 0.5, 0.1),
}


@dataclass
class ObjSpec:
    oid: str
    color: str
    half: float
    pos: Tuple[float, float]
    yaw: float = 0.0
    velocity: Tuple[float, float] = (0.0, 0.0)   # conveyor drift (m/s)


@dataclass
class SceneSpec:
    objects: List[ObjSpec]
    container_pos: Tuple[float, float]


def _mjcf(spec: SceneSpec) -> str:
    cx, cy = spec.container_pos
    t = CONTAINER_HALF_IN
    w = 0.01
    walls = f"""
    <body name="container" pos="{cx} {cy} 0">
      <geom name="c_floor" type="box" size="{t+w} {t+w} 0.005" pos="0 0 0.005" rgba="0.15 0.3 0.85 1" friction="1 0.01 0.001"/>
      <geom name="c_w1" type="box" size="{w} {t+w} {WALL_H/2}" pos="{t+w} 0 {WALL_H/2}" rgba="0.1 0.2 0.7 1"/>
      <geom name="c_w2" type="box" size="{w} {t+w} {WALL_H/2}" pos="{-(t+w)} 0 {WALL_H/2}" rgba="0.1 0.2 0.7 1"/>
      <geom name="c_w3" type="box" size="{t+w} {w} {WALL_H/2}" pos="0 {t+w} {WALL_H/2}" rgba="0.1 0.2 0.7 1"/>
      <geom name="c_w4" type="box" size="{t+w} {w} {WALL_H/2}" pos="0 {-(t+w)} {WALL_H/2}" rgba="0.1 0.2 0.7 1"/>
    </body>"""
    objs = ""
    for o in spec.objects:
        r, g, b = COLORS[o.color]
        objs += f"""
    <body name="{o.oid}" pos="{o.pos[0]} {o.pos[1]} {o.half+0.001}" euler="0 0 {o.yaw}">
      <freejoint name="{o.oid}_j"/>
      <geom name="{o.oid}_g" type="box" size="{o.half} {o.half} {o.half}" rgba="{r} {g} {b} 1" mass="0.05"
            friction="1.6 0.02 0.002" condim="4" solref="0.004 1" solimp="0.95 0.99 0.001"/>
    </body>"""
    bx, by = BASE_XY
    return f"""
<mujoco model="opai">
  <compiler angle="radian"/>
  <option timestep="0.002" gravity="0 0 -9.81" cone="elliptic" impratio="10" integrator="implicitfast"/>
  <default>
    <joint damping="2" armature="0.05"/>
    <position kp="600" kv="40"/>
    <geom contype="1" conaffinity="1"/>
  </default>
  <visual>
    <headlight diffuse="0.75 0.75 0.75" specular="0.25 0.25 0.25" ambient="0.4 0.4 0.4"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global offwidth="640" offheight="480"/>
  </visual>
  <worldbody>
    <light directional="true" pos="-0.3 -0.3 1.6" dir="0.3 0.3 -1" diffuse="0.85 0.85 0.85" specular="0.3 0.3 0.3" castshadow="true"/>
    <light directional="true" pos="0.5 0.4 1.5" dir="-0.3 -0.2 -1" diffuse="0.5 0.5 0.5" specular="0.1 0.1 0.1"/>
    <geom name="table" type="plane" size="1 1 0.1" rgba="0.75 0.75 0.75 1" friction="1 0.01 0.001"/>
    <body name="base" pos="{bx} {by} 0" gravcomp="1">
      <geom type="cylinder" size="0.06 0.05" pos="0 0 0.05" rgba="0.3 0.3 0.3 1" contype="0" conaffinity="0"/>
      <body name="turret" pos="0 0 0.1" gravcomp="1">
        <joint name="j1" axis="0 0 1" range="-3.14 3.14"/>
        <geom type="cylinder" size="0.04 0.025" pos="0 0 0.025" rgba="0.5 0.5 0.55 1" contype="0" conaffinity="0"/>
        <body name="shoulder" pos="0 0 0.05" gravcomp="1">
          <joint name="j2" axis="0 1 0" range="-1.9 1.9"/>
          <geom type="capsule" fromto="0 0 0 0 0 {L1}" size="0.025" rgba="0.8 0.8 0.85 1" contype="0" conaffinity="0"/>
          <body name="elbow" pos="0 0 {L1}" gravcomp="1">
            <joint name="j3" axis="0 1 0" range="-2.7 2.7"/>
            <geom type="capsule" fromto="0 0 0 0 0 {L2}" size="0.022" rgba="0.7 0.7 0.75 1" contype="0" conaffinity="0"/>
            <body name="wrist" pos="0 0 {L2}" gravcomp="1">
              <joint name="j4" axis="0 1 0" range="-3.6 3.6"/>
              <geom type="sphere" size="0.025" rgba="0.4 0.4 0.45 1" contype="0" conaffinity="0"/>
              <body name="tool" pos="0 0 0.05" gravcomp="1">
                <joint name="j5" axis="0 0 1" range="-3.3 3.3"/>
                <geom type="box" size="0.045 0.07 0.01" pos="0 0 0.005" rgba="0.2 0.2 0.2 1" contype="0" conaffinity="0"/>
                <site name="tip" pos="0 0 {L_TOOL}" size="0.006"/>
                <body name="fa" pos="0 0.06 {L_TOOL}" gravcomp="1">
                  <joint name="fa_j" type="slide" axis="0 -1 0" range="0 0.058" damping="8"/>
                  <geom name="fa_g" type="box" size="0.012 0.008 0.032" rgba="0.1 0.1 0.1 1" mass="0.02"
                        friction="2.2 0.05 0.005" condim="4" solref="0.004 1" solimp="0.95 0.99 0.001"/>
                </body>
                <body name="fb" pos="0 -0.06 {L_TOOL}" gravcomp="1">
                  <joint name="fb_j" type="slide" axis="0 1 0" range="0 0.058" damping="8"/>
                  <geom name="fb_g" type="box" size="0.012 0.008 0.032" rgba="0.1 0.1 0.1 1" mass="0.02"
                        friction="2.2 0.05 0.005" condim="4" solref="0.004 1" solimp="0.95 0.99 0.001"/>
                </body>
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
    {walls}
    {objs}
  </worldbody>
  <actuator>
    <position name="a1" joint="j1" kp="800" kv="60" ctrlrange="-3.14 3.14"/>
    <position name="a2" joint="j2" kp="800" kv="60" ctrlrange="-1.9 1.9"/>
    <position name="a3" joint="j3" kp="800" kv="60" ctrlrange="-2.7 2.7"/>
    <position name="a4" joint="j4" kp="400" kv="30" ctrlrange="-3.6 3.6"/>
    <position name="a5" joint="j5" kp="200" kv="20" ctrlrange="-3.3 3.3"/>
    <position name="afa" joint="fa_j" kp="900" kv="30" ctrlrange="0 0.058" forcerange="-60 60"/>
    <position name="afb" joint="fb_j" kp="900" kv="30" ctrlrange="0 0.058" forcerange="-60 60"/>
  </actuator>
</mujoco>"""


class IKError(Exception):
    pass


def ik(x: float, y: float, z: float, yaw_world: float = 0.0) -> np.ndarray:
    """Analytic IK for tip position (world) with tool pointing straight down.
    Returns [q1..q5]. q5 rotates the gripper so fingers align with yaw_world."""
    dx, dy = x - BASE_XY[0], y - BASE_XY[1]
    r = math.hypot(dx, dy)
    q1 = math.atan2(dy, dx)
    wx = r
    wz = z + L_TOOL + 0.05 - (0.10 + 0.05)   # wrist pivot height rel. shoulder; tool offset 0.05 below wrist
    d2 = wx * wx + wz * wz
    c = (d2 - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(c) > 1.0:
        raise IKError(f"unreachable ({x:.3f},{y:.3f},{z:.3f})")
    q3 = math.acos(c)
    q2 = math.atan2(wx, wz) - math.atan2(L2 * math.sin(q3), L1 + L2 * math.cos(q3))
    q4 = math.pi - q2 - q3
    # fingers separate along tool local y; align with cube faces: rotate about tool axis
    q5 = _wrap_half_pi(q1 - yaw_world)
    return np.array([q1, q2, q3, q4, q5])


def _wrap_half_pi(a: float) -> float:
    """Cube is symmetric under 90 deg: wrap to [-pi/4, pi/4]."""
    return (a + math.pi / 4) % (math.pi / 2) - math.pi / 4


class World:
    def __init__(self, spec: SceneSpec):
        self.spec = spec
        self.model = mujoco.MjModel.from_xml_string(_mjcf(spec))
        self.data = mujoco.MjData(self.model)
        m = self.model
        self.jid = [m.joint(n).qposadr[0] for n in ("j1", "j2", "j3", "j4", "j5")]
        self.fa = m.joint("fa_j").qposadr[0]
        self.fb = m.joint("fb_j").qposadr[0]
        self.tip_id = m.site("tip").id
        self.obj_qadr = {o.oid: m.joint(f"{o.oid}_j").qposadr[0] for o in spec.objects}
        self.obj_vadr = {o.oid: m.joint(f"{o.oid}_j").dofadr[0] for o in spec.objects}
        self.vel = {o.oid: np.array(o.velocity) for o in spec.objects}
        self.ctrl = np.zeros(m.nu)
        self.time0 = 0.0
        self.hold_g = 0.0
        self.conveyor_on = False
        self.sim_steps = 0
        # initial pose: hover above centre
        self._set_joints(ik(0.25, 0.0, 0.20))
        self.ctrl[:5] = ik(0.25, 0.0, 0.20)
        for i, q in enumerate(self.ctrl[:5]):
            self.data.qpos[self.jid[i]] = q
        mujoco.mj_forward(m, self.data)
        self.step(200)
        self.sim_steps = 0
        self.conveyor_on = True

    def _set_joints(self, q):
        self.ctrl[:5] = q

    @property
    def time(self) -> float:
        return float(self.data.time)

    def step(self, n: int = 1):
        for _ in range(n):
            if self.conveyor_on:
                self._conveyor()
            self.data.ctrl[:] = self.ctrl
            mujoco.mj_step(self.model, self.data, nstep=1)
            self.sim_steps += 1

    def step_n(self, n: int = 1):
        self.step(n)

    def _conveyor(self):
        tip = self.tip()
        for oid, v in self.vel.items():
            if not v.any():
                continue
            p = self.obj_pos(oid)
            near_gripper = np.linalg.norm(p[:2] - tip[:2]) < 0.09 and p[2] < 0.15 and tip[2] < 0.12
            if p[2] < 0.04 and not near_gripper and not self._in_container(p):
                qa, va = self.obj_qadr[oid], self.obj_vadr[oid]
                dt = self.model.opt.timestep
                self.data.qpos[qa] += v[0] * dt          # kinematic belt: exact, friction-independent
                self.data.qpos[qa + 1] += v[1] * dt
                self.data.qvel[va:va + 3] = 0.0

    # ---- state ----
    def tip(self) -> np.ndarray:
        return self.data.site_xpos[self.tip_id].copy()

    def finger_closure(self) -> float:
        return float(0.5 * (self.data.qpos[self.fa] + self.data.qpos[self.fb]))

    def obj_pos(self, oid: str) -> np.ndarray:
        a = self.obj_qadr[oid]
        return self.data.qpos[a:a + 3].copy()

    def obj_yaw(self, oid: str) -> float:
        a = self.obj_qadr[oid]
        w, x, y, z = self.data.qpos[a + 3:a + 7]
        return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))

    def teleport(self, oid: str, dx: float, dy: float):
        a = self.obj_qadr[oid]
        self.data.qpos[a] += dx
        self.data.qpos[a + 1] += dy
        self.data.qvel[self.obj_vadr[oid]:self.obj_vadr[oid] + 6] = 0
        mujoco.mj_forward(self.model, self.data)

    def _in_container(self, p) -> bool:
        cx, cy = self.spec.container_pos
        return abs(p[0] - cx) < CONTAINER_HALF_IN and abs(p[1] - cy) < CONTAINER_HALF_IN and p[2] < WALL_H + 0.03

    def in_container(self, oid: str) -> bool:
        return self._in_container(self.obj_pos(oid))

    def arm_points(self) -> List[Tuple[float, float, float]]:
        d = self.data
        names = ["turret", "shoulder", "elbow", "wrist", "tool"]
        pts = [d.xpos[self.model.body(n).id].copy() for n in names]
        pts.append(self.tip())
        return [tuple(float(v) for v in p) for p in pts]

    # ---- motion primitives ----
    def set_gripper(self, closure: float):
        self.ctrl[5] = closure
        self.ctrl[6] = closure

    def settle(self, seconds: float):
        self.step(int(seconds / self.model.opt.timestep))

    def move_to(self, x: float, y: float, z: float, yaw: float = 0.0, speed: float = 0.30,
                tol: float = 0.006, on_tick=None) -> float:
        """Straight-line Cartesian move. Returns final tip error (m)."""
        start = self.tip()
        goal = np.array([x, y, z])
        dist = float(np.linalg.norm(goal - start))
        dur = max(0.4, dist / speed)
        n = max(1, int(dur / 0.02))
        q_prev = self.ctrl[:5].copy()
        for i in range(1, n + 1):
            s = i / n
            s = s * s * (3 - 2 * s)  # smoothstep
            p = start + (goal - start) * s
            q = ik(p[0], p[1], p[2], yaw)
            # unwrap roll continuity
            q[4] = q_prev[4] + ((q[4] - q_prev[4] + math.pi / 4) % (math.pi / 2) - math.pi / 4) if abs(q[4] - q_prev[4]) > 0.8 else q[4]
            self.ctrl[:5] = q
            q_prev = q
            self.step(10)
            if on_tick:
                on_tick()
        self.settle(0.25)
        return float(np.linalg.norm(self.tip() - goal))

    def hold(self, seconds: float, on_tick=None):
        """Advance the world with the arm holding its last command (used while a model is 'thinking')."""
        n = int(seconds / 0.02)
        for _ in range(n):
            self.step(10)
            if on_tick:
                on_tick()
        rem = seconds - n * 0.02
        if rem > 0:
            self.step(int(rem / self.model.opt.timestep))
