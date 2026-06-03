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

# Screen-normalized (0–1) ↔ world position (approximate inverse of projection)
_SCREEN_X_SPAN = 3.2
_SCREEN_Y_SPAN = 2.4
_DEPTH_MIN = -3.8
_DEPTH_MAX = -0.6


class ControlMode(str, Enum):
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"


def euler_xyz_deg_to_quat(euler_deg: np.ndarray) -> np.ndarray:
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
    locked: bool


class ModelState:
    """Axes match the webcam feed: X = left/right, Y = up/down, Z = depth."""

    MOVE_STEP = {"fine": 0.04, "normal": 0.12, "coarse": 0.28}
    ROT_STEP = {"fine": 3.0, "normal": 8.0, "coarse": 18.0}
    SCALE_STEP = {"fine": 0.03, "normal": 0.08, "coarse": 0.18}
    SCALE_MIN = 0.2
    SCALE_MAX = 4.0
    ROT_DRAG_SENS = 0.45
    SCALE_DRAG_SENS = 0.004

    # Display follows target each frame (see tick) for smooth motion on the feed.
    _SMOOTH_RATE = 22.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._target_position = DEFAULT_POSITION.copy()
        self._position = DEFAULT_POSITION.copy()
        self._target_euler = DEFAULT_EULER_DEG.copy()
        self._euler_deg = DEFAULT_EULER_DEG.copy()
        self._target_scale = DEFAULT_SCALE
        self._scale = DEFAULT_SCALE
        self._locked = False
        self._mode = ControlMode.MOVE
        self._step = "normal"
        self._generation = 0

    def _touch(self) -> None:
        self._generation += 1

    def tick(self, dt: float) -> bool:
        """Interpolate display transform toward targets. Returns True if display moved."""
        if dt <= 0:
            return False
        alpha = 1.0 - math.exp(-self._SMOOTH_RATE * dt)
        changed = False
        with self._lock:
            new_pos = self._position + (self._target_position - self._position) * alpha
            if float(np.linalg.norm(new_pos - self._position)) > 1e-5:
                self._position = new_pos
                changed = True

            new_euler = self._euler_deg + (self._target_euler - self._euler_deg) * alpha
            if float(np.linalg.norm(new_euler - self._euler_deg)) > 0.05:
                self._euler_deg = new_euler
                changed = True

            if abs(self._scale - self._target_scale) > 1e-4:
                self._scale += (self._target_scale - self._scale) * alpha
                changed = True

        if changed:
            self._touch()
        return changed

    def screen_norm_from_target(self) -> tuple[float, float]:
        """Pad dot follows drag target immediately."""
        with self._lock:
            nx = 0.5 + self._target_position[0] / _SCREEN_X_SPAN
            ny = 0.5 - self._target_position[1] / _SCREEN_Y_SPAN
            return float(np.clip(nx, 0.0, 1.0)), float(np.clip(ny, 0.0, 1.0))

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

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

    def set_step(self, step: str) -> None:
        if step in self.MOVE_STEP:
            with self._lock:
                self._step = step

    def reset(self) -> None:
        with self._lock:
            self._target_position = DEFAULT_POSITION.copy()
            self._position = DEFAULT_POSITION.copy()
            self._target_euler = DEFAULT_EULER_DEG.copy()
            self._euler_deg = DEFAULT_EULER_DEG.copy()
            self._target_scale = DEFAULT_SCALE
            self._scale = DEFAULT_SCALE
            self._touch()

    @property
    def euler_deg(self) -> np.ndarray:
        """Target euler (matches sliders)."""
        with self._lock:
            return self._target_euler.copy()

    @property
    def scale(self) -> float:
        with self._lock:
            return self._target_scale

    def set_euler_axis(self, axis: str, degrees: float) -> None:
        with self._lock:
            if self._locked:
                return
            idx = {"x": 0, "y": 1, "z": 2}[axis]
            self._target_euler[idx] = float(degrees)
            self._touch()

    def set_scale(self, value: float) -> None:
        with self._lock:
            if self._locked:
                return
            self._target_scale = float(np.clip(value, self.SCALE_MIN, self.SCALE_MAX))
            self._touch()

    def snapshot(self) -> TransformSnapshot:
        with self._lock:
            return TransformSnapshot(
                position=self._position.copy(),
                rotation=euler_xyz_deg_to_quat(self._euler_deg),
                scale=self._scale,
                mode=self._mode,
                locked=self._locked,
            )

    def screen_norm_from_position(self) -> tuple[float, float]:
        """Approximate normalized screen position (0–1) of model center."""
        with self._lock:
            nx = 0.5 + self._position[0] / _SCREEN_X_SPAN
            ny = 0.5 - self._position[1] / _SCREEN_Y_SPAN
            return float(np.clip(nx, 0.0, 1.0)), float(np.clip(ny, 0.0, 1.0))

    def set_screen_norm(self, nx: float, ny: float) -> None:
        """Place model on screen at normalized coords (drag on screen pad)."""
        with self._lock:
            if self._locked:
                return
            self._target_position[0] = (nx - 0.5) * _SCREEN_X_SPAN
            self._target_position[1] = (0.5 - ny) * _SCREEN_Y_SPAN
            self._touch()

    def set_depth_norm(self, nz: float) -> None:
        """nz: 0 = far, 1 = near (same as depth / Z)."""
        with self._lock:
            if self._locked:
                return
            nz = float(np.clip(nz, 0.0, 1.0))
            self._target_position[2] = _DEPTH_MIN + nz * (_DEPTH_MAX - _DEPTH_MIN)
            self._touch()

    def depth_norm(self) -> float:
        with self._lock:
            return float(
                (self._target_position[2] - _DEPTH_MIN) / (_DEPTH_MAX - _DEPTH_MIN)
            )

    def nudge_move_screen(self, dx: int, dy: int, dz: int) -> None:
        with self._lock:
            if self._locked:
                return
            s = self.MOVE_STEP[self._step]
            self._target_position[0] += dx * s
            self._target_position[1] += dy * s
            self._target_position[2] += dz * s
            self._touch()

    def drag_move_axis(self, axis: str, delta_px: float, scale: float = 1.0) -> None:
        with self._lock:
            if self._locked:
                return
            s = self.MOVE_STEP[self._step] * (delta_px / 40.0) * scale
            if axis == "x":
                self._target_position[0] += s
            elif axis == "y":
                self._target_position[1] += s
            elif axis == "z":
                self._target_position[2] += s
            self._touch()

    def drag_rotate_axis(self, axis: str, delta_px: float) -> None:
        with self._lock:
            if self._locked:
                return
            s = self.ROT_STEP[self._step] * delta_px * self.ROT_DRAG_SENS
            idx = {"x": 0, "y": 1, "z": 2}[axis]
            self._target_euler[idx] += s
            self._touch()

    def drag_scale(self, delta_px: float) -> None:
        with self._lock:
            if self._locked:
                return
            self._target_scale = float(
                np.clip(
                    self._target_scale + delta_px * self.SCALE_DRAG_SENS,
                    self.SCALE_MIN,
                    self.SCALE_MAX,
                )
            )
            self._touch()
