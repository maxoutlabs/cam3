"""Procedural motion presets and custom waveform-driven animation."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

_DEFAULT_POSITION = np.array([0.0, 0.0, -2.0], dtype=np.float64)
_DEFAULT_EULER = np.array([0.0, 0.0, 0.0], dtype=np.float64)
_DEFAULT_SCALE = 1.0
_SCREEN_X_SPAN = 3.2
_SCREEN_Y_SPAN = 2.4
_DEPTH_MIN = -3.8
_DEPTH_MAX = -0.6

# --- Safe bounds (keep motion on-screen and stable) ---
PERIOD_MIN = 0.5
PERIOD_MAX = 45.0
STRENGTH_MIN = 0.05
STRENGTH_MAX = 1.0

SPIN_PERIOD_MIN = 1.2
SPIN_PERIOD_MAX = 40.0

WIGGLE_DEG_MAX = 55.0
BOB_WORLD_MAX = 0.42
ORBIT_RADIUS_MAX = 0.55
BREATHE_SCALE_MAX = 0.32
FLOAT_BOB_MAX = 0.28
FLOAT_SPIN_DEG_MAX = 25.0

GRAPH_POINT_COUNT = 9
CURVE_VALUE_MIN = -1.0
CURVE_VALUE_MAX = 1.0

CUSTOM_ROT_MAX = 75.0
CUSTOM_POS_X_MAX = 0.45
CUSTOM_POS_Y_MAX = 0.38
CUSTOM_SCALE_MAX = 0.28


class AnimationPreset(str, Enum):
    OFF = "off"
    SPIN = "spin"
    WIGGLE = "wiggle"
    BOB = "bob"
    ORBIT = "orbit"
    BREATHE = "breathe"
    FLOAT = "float"
    CUSTOM = "custom"


class CustomChannel(str, Enum):
    ROT_X = "rot_x"
    ROT_Y = "rot_y"
    ROT_Z = "rot_z"
    POS_X = "pos_x"
    POS_Y = "pos_y"
    SCALE = "scale"


@dataclass
class AnimationConfig:
    enabled: bool = False
    preset: AnimationPreset = AnimationPreset.SPIN
    axis: str = "y"
    period_sec: float = 4.0
    strength: float = 0.65
    custom_channel: CustomChannel = CustomChannel.ROT_Y
    custom_curve: list[float] = field(
        default_factory=lambda: _default_custom_curve()
    )
    time_sec: float = 0.0


@dataclass
class AnimationBase:
    position: np.ndarray = field(default_factory=lambda: _DEFAULT_POSITION.copy())
    euler_deg: np.ndarray = field(default_factory=lambda: _DEFAULT_EULER.copy())
    scale: float = _DEFAULT_SCALE


@dataclass
class AnimationOutput:
    position: np.ndarray
    euler_deg: np.ndarray
    scale: float


def default_custom_curve() -> list[float]:
    """One gentle sine-like cycle for the graph editor."""
    return [
        0.0,
        0.38,
        0.71,
        0.95,
        1.0,
        0.95,
        0.71,
        0.38,
        0.0,
    ]


def normalize_custom_curve(curve: list[float]) -> list[float]:
    if len(curve) == GRAPH_POINT_COUNT:
        return [clamp_curve_value(float(v)) for v in curve]
    return default_custom_curve()


def _default_custom_curve() -> list[float]:
    return default_custom_curve()


def clamp_period(value: float, preset: AnimationPreset) -> float:
    lo = SPIN_PERIOD_MIN if preset == AnimationPreset.SPIN else PERIOD_MIN
    hi = SPIN_PERIOD_MAX if preset == AnimationPreset.SPIN else PERIOD_MAX
    return float(np.clip(value, lo, hi))


def clamp_strength(value: float) -> float:
    return float(np.clip(value, STRENGTH_MIN, STRENGTH_MAX))


def clamp_curve_value(value: float) -> float:
    return float(np.clip(value, CURVE_VALUE_MIN, CURVE_VALUE_MAX))


def sample_curve(curve: list[float], phase: float) -> float:
    """Sample a periodic curve; phase in [0, 1)."""
    n = len(curve)
    if n < 2:
        return 0.0
    phase = phase % 1.0
    x = phase * (n - 1)
    i0 = int(math.floor(x))
    i1 = min(i0 + 1, n - 1)
    t = x - i0
    # Smoothstep between control points
    t = t * t * (3.0 - 2.0 * t)
    v0 = clamp_curve_value(float(curve[i0]))
    v1 = clamp_curve_value(float(curve[i1]))
    return v0 + (v1 - v0) * t


def _axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}.get(axis, 1)


def _clamp_position(pos: np.ndarray) -> np.ndarray:
    out = pos.copy()
    out[0] = float(np.clip(out[0], -_SCREEN_X_SPAN * 0.48, _SCREEN_X_SPAN * 0.48))
    out[1] = float(np.clip(out[1], -_SCREEN_Y_SPAN * 0.48, _SCREEN_Y_SPAN * 0.48))
    out[2] = float(np.clip(out[2], _DEPTH_MIN, _DEPTH_MAX))
    return out


def _clamp_scale(scale: float, scale_min: float, scale_max: float) -> float:
    return float(np.clip(scale, scale_min, scale_max))


def evaluate_animation(
    config: AnimationConfig,
    base: AnimationBase,
    scale_min: float,
    scale_max: float,
) -> AnimationOutput:
    """Compute animated pose from base + preset at config.time_sec."""
    pos = base.position.copy()
    euler = base.euler_deg.copy()
    scale = base.scale

    if not config.enabled or config.preset == AnimationPreset.OFF:
        return AnimationOutput(pos, euler, scale)

    t = config.time_sec
    period = clamp_period(config.period_sec, config.preset)
    strength = clamp_strength(config.strength)
    phase = (t / period) % 1.0 if period > 1e-6 else 0.0
    wave = math.sin(2.0 * math.pi * phase)

    preset = config.preset
    axis = _axis_index(config.axis)

    if preset == AnimationPreset.SPIN:
        turns = t / period
        spin_deg = turns * 360.0
        euler[axis] = base.euler_deg[axis] + spin_deg

    elif preset == AnimationPreset.WIGGLE:
        amp = WIGGLE_DEG_MAX * strength
        euler[axis] = base.euler_deg[axis] + amp * wave

    elif preset == AnimationPreset.BOB:
        amp = BOB_WORLD_MAX * strength
        pos[1] = base.position[1] + amp * wave

    elif preset == AnimationPreset.ORBIT:
        radius = ORBIT_RADIUS_MAX * strength
        angle = 2.0 * math.pi * phase
        pos[0] = base.position[0] + radius * math.cos(angle)
        pos[1] = base.position[1] + radius * math.sin(angle)

    elif preset == AnimationPreset.BREATHE:
        amp = BREATHE_SCALE_MAX * strength
        scale = base.scale * (1.0 + amp * wave)

    elif preset == AnimationPreset.FLOAT:
        bob = FLOAT_BOB_MAX * strength * math.sin(2.0 * math.pi * phase)
        drift = FLOAT_SPIN_DEG_MAX * strength * math.sin(
            2.0 * math.pi * (phase * 0.5 + 0.25)
        )
        pos[1] = base.position[1] + bob
        euler[1] = base.euler_deg[1] + drift

    elif preset == AnimationPreset.CUSTOM:
        curve = normalize_custom_curve(config.custom_curve)
        sample = sample_curve(curve, phase) * strength
        ch = config.custom_channel
        if ch == CustomChannel.ROT_X:
            euler[0] = base.euler_deg[0] + CUSTOM_ROT_MAX * sample
        elif ch == CustomChannel.ROT_Y:
            euler[1] = base.euler_deg[1] + CUSTOM_ROT_MAX * sample
        elif ch == CustomChannel.ROT_Z:
            euler[2] = base.euler_deg[2] + CUSTOM_ROT_MAX * sample
        elif ch == CustomChannel.POS_X:
            pos[0] = base.position[0] + CUSTOM_POS_X_MAX * sample
        elif ch == CustomChannel.POS_Y:
            pos[1] = base.position[1] + CUSTOM_POS_Y_MAX * sample
        elif ch == CustomChannel.SCALE:
            scale = base.scale * (1.0 + CUSTOM_SCALE_MAX * sample)

    pos = _clamp_position(pos)
    scale = _clamp_scale(scale, scale_min, scale_max)
    return AnimationOutput(pos, euler, scale)


def preset_label(preset: AnimationPreset) -> str:
    return {
        AnimationPreset.OFF: "Off",
        AnimationPreset.SPIN: "Spin 360°",
        AnimationPreset.WIGGLE: "Wiggle",
        AnimationPreset.BOB: "Bob up/down",
        AnimationPreset.ORBIT: "Orbit",
        AnimationPreset.BREATHE: "Breathe (scale)",
        AnimationPreset.FLOAT: "Float",
        AnimationPreset.CUSTOM: "Custom wave",
    }.get(preset, preset.value)


def preset_strength_label(preset: AnimationPreset) -> str:
    return {
        AnimationPreset.SPIN: "Speed",
        AnimationPreset.WIGGLE: "Tilt amount",
        AnimationPreset.BOB: "Height",
        AnimationPreset.ORBIT: "Radius",
        AnimationPreset.BREATHE: "Pulse size",
        AnimationPreset.FLOAT: "Intensity",
        AnimationPreset.CUSTOM: "Wave height",
    }.get(preset, "Strength")


def copy_config(config: AnimationConfig) -> AnimationConfig:
    return AnimationConfig(
        enabled=config.enabled,
        preset=config.preset,
        axis=config.axis,
        period_sec=config.period_sec,
        strength=config.strength,
        custom_channel=config.custom_channel,
        custom_curve=deepcopy(normalize_custom_curve(config.custom_curve)),
        time_sec=config.time_sec,
    )
