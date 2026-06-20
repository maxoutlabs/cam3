"""Thread-safe 3D transform with screen-aligned move and euler rotation."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from enum import Enum

import numpy as np

from animation_engine import (
    AnimationBase,
    AnimationConfig,
    AnimationPreset,
    CustomChannel,
    clamp_curve_value,
    clamp_period,
    clamp_strength,
    copy_config,
    default_custom_curve,
    evaluate_animation,
)

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
    ANIMATE = "animate"


def _slerp_quat(q0: np.ndarray, q1: np.ndarray, t: float) -> np.ndarray:
    q0 = q0.astype(np.float64)
    q1 = q1.astype(np.float64)
    q0 /= max(np.linalg.norm(q0), 1e-12)
    q1 /= max(np.linalg.norm(q1), 1e-12)
    dot = float(np.clip(np.dot(q0, q1), -1.0, 1.0))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    if dot > 0.9995:
        out = q0 + t * (q1 - q0)
        return out / max(np.linalg.norm(out), 1e-12)
    theta = math.acos(dot)
    s = math.sin(theta)
    w0 = math.sin((1.0 - t) * theta) / s
    w1 = math.sin(t * theta) / s
    return w0 * q0 + w1 * q1


def normalize_euler_deg(euler_deg: np.ndarray) -> np.ndarray:
    out = euler_deg.astype(np.float64).copy()
    for i in range(3):
        out[i] = ((out[i] + 180.0) % 360.0) - 180.0
    return out


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

    SCALE_MIN = 0.2
    SCALE_MAX = 4.0

    # Display follows target each frame (see tick) for smooth motion on the feed.
    _SMOOTH_RATE = 22.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._target_position = DEFAULT_POSITION.copy()
        self._position = DEFAULT_POSITION.copy()
        self._target_euler = DEFAULT_EULER_DEG.copy()
        self._target_quat = euler_xyz_deg_to_quat(self._target_euler)
        self._display_quat = self._target_quat.copy()
        self._target_scale = DEFAULT_SCALE
        self._scale = DEFAULT_SCALE
        self._locked = False
        self._mode = ControlMode.MOVE
        self._generation = 0
        self._animation = AnimationConfig()
        self._anim_base = AnimationBase()

    def _touch(self) -> None:
        self._generation += 1

    def _pause_animation_from_manual_edit(self) -> None:
        if not self._animation.enabled:
            return
        self._animation.enabled = False
        self._animation.time_sec = 0.0
        self._target_euler = normalize_euler_deg(self._target_euler)
        self._target_quat = euler_xyz_deg_to_quat(self._target_euler)

    def tick(self, dt: float) -> bool:
        """Interpolate display transform toward targets. Returns True if display moved."""
        if dt <= 0:
            return False
        alpha = 1.0 - math.exp(-self._SMOOTH_RATE * dt)
        changed = False
        with self._lock:
            animating = self._animation.enabled and not self._locked
            if animating:
                self._animation.time_sec += dt
                if self._animation.time_sec > 86400.0:
                    self._animation.time_sec %= 3600.0
                out = evaluate_animation(
                    self._animation,
                    self._anim_base,
                    self.SCALE_MIN,
                    self.SCALE_MAX,
                )
                self._target_position = out.position.copy()
                self._target_euler = out.euler_deg.copy()
                self._target_quat = euler_xyz_deg_to_quat(self._target_euler)
                self._target_scale = out.scale
                self._position = self._target_position.copy()
                self._display_quat = self._target_quat.copy()
                self._scale = self._target_scale
                changed = True
            else:
                new_pos = self._position + (self._target_position - self._position) * alpha
                if float(np.linalg.norm(new_pos - self._position)) > 1e-5:
                    self._position = new_pos
                    changed = True

                new_quat = _slerp_quat(self._display_quat, self._target_quat, alpha)
                if float(np.linalg.norm(new_quat - self._display_quat)) > 1e-5:
                    self._display_quat = new_quat
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

    def reset(self) -> None:
        with self._lock:
            self._target_position = DEFAULT_POSITION.copy()
            self._position = DEFAULT_POSITION.copy()
            self._target_euler = DEFAULT_EULER_DEG.copy()
            self._target_quat = euler_xyz_deg_to_quat(self._target_euler)
            self._display_quat = self._target_quat.copy()
            self._target_scale = DEFAULT_SCALE
            self._scale = DEFAULT_SCALE
            self._animation = AnimationConfig()
            self._anim_base = AnimationBase()
            self._touch()

    def capture_animation_base(self) -> None:
        """Anchor animation to the current manual pose."""
        with self._lock:
            if self._locked:
                return
            self._anim_base = AnimationBase(
                position=self._target_position.copy(),
                euler_deg=normalize_euler_deg(self._target_euler),
                scale=self._target_scale,
            )
            self._animation.time_sec = 0.0
            self._touch()

    def animation_config(self) -> AnimationConfig:
        with self._lock:
            return copy_config(self._animation)

    def set_animation_enabled(self, enabled: bool) -> bool:
        with self._lock:
            if self._locked:
                return False
            if enabled and not self._animation.enabled:
                self._anim_base = AnimationBase(
                    position=self._target_position.copy(),
                    euler_deg=normalize_euler_deg(self._target_euler),
                    scale=self._target_scale,
                )
                self._animation.time_sec = 0.0
            self._animation.enabled = enabled
            self._touch()
            return True

    def set_animation_preset(self, preset: AnimationPreset) -> None:
        with self._lock:
            if self._locked:
                return
            self._animation.preset = preset
            self._animation.period_sec = clamp_period(
                self._animation.period_sec, preset
            )
            if preset == AnimationPreset.OFF:
                self._animation.enabled = False
            self._touch()

    def set_animation_axis(self, axis: str) -> None:
        with self._lock:
            if self._locked:
                return
            if axis in ("x", "y", "z"):
                self._animation.axis = axis
                self._touch()

    def set_animation_period(self, seconds: float) -> None:
        with self._lock:
            if self._locked:
                return
            self._animation.period_sec = clamp_period(
                seconds, self._animation.preset
            )
            self._touch()

    def set_animation_strength(self, strength: float) -> None:
        with self._lock:
            if self._locked:
                return
            self._animation.strength = clamp_strength(strength)
            self._touch()

    def set_animation_custom_channel(self, channel: CustomChannel) -> None:
        with self._lock:
            if self._locked:
                return
            self._animation.custom_channel = channel
            self._touch()

    def set_animation_curve_point(self, index: int, value: float) -> None:
        with self._lock:
            if self._locked:
                return
            if 0 <= index < len(self._animation.custom_curve):
                self._animation.custom_curve[index] = clamp_curve_value(value)
                self._touch()

    def reset_animation_curve(self) -> None:
        with self._lock:
            if self._locked:
                return
            self._animation.custom_curve = default_custom_curve()
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
            self._target_quat = euler_xyz_deg_to_quat(self._target_euler)
            self._pause_animation_from_manual_edit()
            self._touch()

    def set_scale(self, value: float) -> None:
        with self._lock:
            if self._locked:
                return
            self._target_scale = float(np.clip(value, self.SCALE_MIN, self.SCALE_MAX))
            self._pause_animation_from_manual_edit()
            self._touch()

    def snapshot(self) -> TransformSnapshot:
        with self._lock:
            return TransformSnapshot(
                position=self._position.copy(),
                rotation=self._display_quat.copy(),
                scale=self._scale,
                mode=self._mode,
                locked=self._locked,
            )

    def set_screen_norm(self, nx: float, ny: float) -> None:
        """Place model on screen at normalized coords (drag on screen pad)."""
        with self._lock:
            if self._locked:
                return
            self._target_position[0] = (nx - 0.5) * _SCREEN_X_SPAN
            self._target_position[1] = (0.5 - ny) * _SCREEN_Y_SPAN
            self._pause_animation_from_manual_edit()
            self._touch()

    def set_depth_norm(self, nz: float) -> None:
        """nz: 0 = far, 1 = near (same as depth / Z)."""
        with self._lock:
            if self._locked:
                return
            nz = float(np.clip(nz, 0.0, 1.0))
            self._target_position[2] = _DEPTH_MIN + nz * (_DEPTH_MAX - _DEPTH_MIN)
            self._pause_animation_from_manual_edit()
            self._touch()

    def depth_norm(self) -> float:
        with self._lock:
            return float(
                (self._target_position[2] - _DEPTH_MIN) / (_DEPTH_MAX - _DEPTH_MIN)
            )
