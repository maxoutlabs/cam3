"""Thread-safe 3D transform with screen-aligned move and euler rotation."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from enum import Enum

import numpy as np

DEFAULT_POSITION = np.array([0.0, 0.0, -2.0], dtype=np.float64)
DEFAULT_EULER_DEG = np.array([0.0, 0.0, 0.0], dtype=np.float64)
DEFAULT_SCALE = 1.0


class ControlMode(str, Enum):
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"


def euler_xyz_deg_to_quat(euler_deg: np.ndarray) -> np.ndarray:
    """XYZ euler in degrees -> quaternion [x, y, z, w]."""
    ex, ey, ez = np.radians(euler_deg.astype(np.float64))
    cx, sx = math.cos(ex * 0.5), math.sin(ex * 0.5)
    cy, sy = math.cos(ey * 0.5), math.sin(ey * 0.5)
    cz, sz = math.cos(ez * 0.5), math.sin(ez * 0.5)
    x = sx * cy * cz + cx * sy * sz
    y = cx * sy * cz - sx * cy * sz
    z = cx * cy * sz + sx * sy * cz
    w = cx * cy * cz - sx * sy * sz
    q = np.array([x, y, z, w], dtype=np.float64)
    n = np.linalg.norm(q)
    return q / n if n > 1e-8 else np.array([0.0, 0.0, 0.0, 1.0])


@dataclass
class TransformSnapshot:
    position: np.ndarray
    rotation: np.ndarray
    scale: float
    mode: ControlMode
    show_gizmo: bool
    locked: bool


class ModelState:
    """
    Axes match what you see on the webcam feed:
      X = left / right on screen
      Y = up / down on screen
      Z = toward / away from camera (depth)
    """

    MOVE_STEP = {"fine": 0.04, "normal": 0.12, "coarse": 0.28}
    ROT_STEP = {"fine": 3.0, "normal": 8.0, "coarse": 18.0}
    SCALE_STEP = {"fine": 0.03, "normal": 0.08, "coarse": 0.18}
    SCALE_MIN = 0.2
    SCALE_MAX = 4.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._position = DEFAULT_POSITION.copy()
        self._euler_deg = DEFAULT_EULER_DEG.copy()
        self._scale = DEFAULT_SCALE
        self._locked = False
        self._mode = ControlMode.MOVE
        self._show_gizmo = False
        self._step = "normal"

    @property
    def locked(self) -> bool:
        with self._lock:
            return self._locked

    def set_locked(self, locked: bool) -> None:
        with self._lock:
            self._locked = locked

    def toggle_locked(self) -> bool:
        with self._lock:
            self._locked = not self._locked
            return self._locked

    def set_mode(self, mode: ControlMode) -> None:
        with self._lock:
            self._mode = mode

    def set_show_gizmo(self, show: bool) -> None:
        with self._lock:
            self._show_gizmo = show

    def set_step(self, step: str) -> None:
        if step in self.MOVE_STEP:
            with self._lock:
                self._step = step

    def reset(self) -> None:
        with self._lock:
            self._position = DEFAULT_POSITION.copy()
            self._euler_deg = DEFAULT_EULER_DEG.copy()
            self._scale = DEFAULT_SCALE

    def snapshot(self) -> TransformSnapshot:
        with self._lock:
            return TransformSnapshot(
                position=self._position.copy(),
                rotation=euler_xyz_deg_to_quat(self._euler_deg),
                scale=self._scale,
                mode=self._mode,
                show_gizmo=self._show_gizmo,
                locked=self._locked,
            )

    def _step_key(self) -> str:
        return self._step

    def nudge_move_screen(self, dx: int, dy: int, dz: int) -> None:
        """dx/dy/dz are -1, 0, or +1 in screen space."""
        with self._lock:
            if self._locked:
                return
            s = self.MOVE_STEP[self._step]
            # +X world = right on screen; +Y world = up on screen
            self._position[0] += dx * s
            self._position[1] += dy * s
            self._position[2] += dz * s

    def nudge_rotate(self, axis: str, direction: int) -> None:
        with self._lock:
            if self._locked:
                return
            s = self.ROT_STEP[self._step] * direction
            idx = {"x": 0, "y": 1, "z": 2}[axis]
            self._euler_deg[idx] += s

    def nudge_scale_uniform(self, direction: int) -> None:
        with self._lock:
            if self._locked:
                return
            s = self.SCALE_STEP[self._step] * direction
            self._scale = float(
                np.clip(self._scale + s, self.SCALE_MIN, self.SCALE_MAX)
            )

    def nudge_scale_axis(self, axis: str, direction: int) -> None:
        """Per-axis scale uses uniform for wireframe (no non-uniform mesh)."""
        self.nudge_scale_uniform(direction)
