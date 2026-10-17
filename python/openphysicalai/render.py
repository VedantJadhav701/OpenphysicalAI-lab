"""Software top-down camera (numpy). Draws the real simulator state (object poses, container,
arm links) to an RGB image. Used for the live view and for VisionPerception. This is NOT
MuJoCo's OpenGL renderer; it works on any machine with no GL driver."""
from __future__ import annotations

import base64
import math
import struct
import zlib
from typing import Optional

import numpy as np

from .sim import CONTAINER_HALF_IN, WALL_H, World

X_MAX, X_MIN = 0.50, -0.30     # image rows: top = X_MAX
Y_MAX, Y_MIN = 0.30, -0.30     # image cols: left = +y
SIZE = 256
RES_X = (X_MAX - X_MIN) / SIZE
RES_Y = (Y_MAX - Y_MIN) / SIZE
TABLE = np.array([196, 196, 196], np.uint8)
PALETTE = {"red": (217, 38, 38), "green": (38, 179, 64), "yellow": (235, 204, 26), "orange": (242, 128, 26), "blue": (38, 77, 217)}


def world_to_px(x: float, y: float):
    return (X_MAX - x) / RES_X, (Y_MAX - y) / RES_Y   # row, col


def px_to_world(row: float, col: float):
    return X_MAX - row * RES_X, Y_MAX - col * RES_Y


def _fill_square(img, cx, cy, half, yaw, color):
    r, c = world_to_px(cx, cy)
    rad = half * math.sqrt(2) / min(RES_X, RES_Y) + 2
    r0, r1 = int(max(0, r - rad)), int(min(SIZE, r + rad + 1))
    c0, c1 = int(max(0, c - rad)), int(min(SIZE, c + rad + 1))
    if r0 >= r1 or c0 >= c1:
        return
    rr, cc = np.mgrid[r0:r1, c0:c1]
    wx = X_MAX - (rr + 0.5) * RES_X - cx
    wy = Y_MAX - (cc + 0.5) * RES_Y - cy
    ca, sa = math.cos(yaw), math.sin(yaw)
    u = wx * ca + wy * sa
    v = -wx * sa + wy * ca
    m = (np.abs(u) <= half) & (np.abs(v) <= half)
    img[r0:r1, c0:c1][m] = color


def _line(img, p0, p1, color, width=2):
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
    for t in np.linspace(0, 1, n):
        r = int(p0[0] + (p1[0] - p0[0]) * t)
        c = int(p0[1] + (p1[1] - p0[1]) * t)
        img[max(0, r - width):min(SIZE, r + width + 1), max(0, c - width):min(SIZE, c + width + 1)] = color


def render(world: World, draw_arm: bool = True, rng: Optional[np.random.Generator] = None, noise: float = 0.0) -> np.ndarray:
    img = np.empty((SIZE, SIZE, 3), np.uint8)
    img[:] = TABLE
    cx, cy = world.spec.container_pos
    t = CONTAINER_HALF_IN + 0.01
    _fill_square(img, cx, cy, t + 0.01, 0.0, (20, 40, 150))
    _fill_square(img, cx, cy, CONTAINER_HALF_IN, 0.0, PALETTE["blue"])
    for o in sorted(world.spec.objects, key=lambda o: world.obj_pos(o.oid)[2]):
        p = world.obj_pos(o.oid)
        _fill_square(img, p[0], p[1], o.half, world.obj_yaw(o.oid), PALETTE[o.color])
    if draw_arm:
        pts = [world_to_px(p[0], p[1]) for p in world.arm_points()]
        for a, b in zip(pts[:-1], pts[1:]):
            _line(img, a, b, (70, 70, 80), 1)
        tip = world.tip()
        r, c = world_to_px(tip[0], tip[1])
        img[max(0, int(r) - 3):int(r) + 4, max(0, int(c) - 3):int(c) + 4] = (30, 30, 30)
    if noise > 0 and rng is not None:
        n = rng.normal(0, noise, img.shape)
        img = np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)
    return img


def png_b64(img: np.ndarray) -> str:
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 3)) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()
