"""Animate tab: motion presets + draggable waveform graph."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from animation_engine import (
    PERIOD_MAX,
    PERIOD_MIN,
    SPIN_PERIOD_MAX,
    SPIN_PERIOD_MIN,
    STRENGTH_MAX,
    STRENGTH_MIN,
    AnimationPreset,
    CustomChannel,
    preset_label,
    preset_strength_label,
    sample_curve,
)
from drag_controls import _LabeledScale
from model_state import ModelState

_BG = "#2b2d30"
_FG = "#e8e8e8"
_ACCENT = "#5ad4ff"
_GRID = "#3a3f48"
_CURVE = "#6ecf6e"
_POINT = "#ffd166"
_ZERO = "#666a72"


class WaveformCanvas(tk.Canvas):
    """One-cycle motion curve. Drag points up/down; x positions are fixed."""

    def __init__(
        self,
        parent: tk.Widget,
        model: ModelState,
        width: int = 340,
        height: int = 120,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#16181c",
            highlightthickness=1,
            highlightbackground="#4a4f58",
            cursor="hand2",
            **kwargs,
        )
        self._model = model
        self._w = width
        self._h = height
        self._pad_x = 14
        self._pad_y = 12
        self._drag_idx: int | None = None
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.redraw()

    def _plot_rect(self) -> tuple[int, int, int, int]:
        return (
            self._pad_x,
            self._pad_y,
            self._w - self._pad_x,
            self._h - self._pad_y,
        )

    def _idx_at(self, event: tk.Event) -> int | None:
        cfg = self._model.animation_config()
        curve = cfg.custom_curve
        x0, y0, x1, y1 = self._plot_rect()
        plot_w = x1 - x0
        best: int | None = None
        best_d = 18.0
        for i in range(len(curve)):
            px = x0 + (i / max(len(curve) - 1, 1)) * plot_w
            py = self._value_to_y(float(curve[i]), y0, y1)
            d = ((event.x - px) ** 2 + (event.y - py) ** 2) ** 0.5
            if d < best_d:
                best_d = d
                best = i
        return best

    def _value_to_y(self, value: float, y0: int, y1: int) -> float:
        mid = (y0 + y1) * 0.5
        half = (y1 - y0) * 0.42
        return mid - value * half

    def _y_to_value(self, y: float, y0: int, y1: int) -> float:
        mid = (y0 + y1) * 0.5
        half = (y1 - y0) * 0.42
        if half < 1e-6:
            return 0.0
        return (mid - y) / half

    def _on_press(self, event: tk.Event) -> None:
        self._drag_idx = self._idx_at(event)
        if self._drag_idx is not None:
            self._apply_drag(event)

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_idx is not None:
            self._apply_drag(event)

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_idx = None

    def _apply_drag(self, event: tk.Event) -> None:
        if self._drag_idx is None:
            return
        _, y0, _, y1 = self._plot_rect()
        value = self._y_to_value(float(event.y), y0, y1)
        self._model.set_animation_curve_point(self._drag_idx, value)
        self.redraw()

    def redraw(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        self.delete("all")
        x0, y0, x1, y1 = self._plot_rect()
        plot_w = x1 - x0
        mid_y = (y0 + y1) * 0.5

        self.create_rectangle(x0, y0, x1, y1, outline=_GRID, fill="#1a1c22")
        self.create_line(x0, mid_y, x1, mid_y, fill=_ZERO, dash=(4, 4))
        self.create_text(x0 + 4, y0 + 4, text="+", fill="#555", anchor=tk.NW, font=("Segoe UI", 7))
        self.create_text(x0 + 4, y1 - 4, text="−", fill="#555", anchor=tk.SW, font=("Segoe UI", 7))
        self.create_text(x1 - 4, y1 + 2, text="1 cycle →", fill="#666", anchor=tk.NE, font=("Segoe UI", 7))

        cfg = self._model.animation_config()
        curve = cfg.custom_curve
        if len(curve) < 2:
            return

        pts: list[float] = []
        steps = max(plot_w, 80)
        for s in range(steps + 1):
            phase = s / steps
            val = sample_curve(curve, phase)
            px = x0 + phase * plot_w
            py = self._value_to_y(val, y0, y1)
            pts.extend((px, py))

        if len(pts) >= 4:
            self.create_line(*pts, fill=_CURVE, width=2, smooth=True)

        for i, val in enumerate(curve):
            px = x0 + (i / max(len(curve) - 1, 1)) * plot_w
            py = self._value_to_y(float(val), y0, y1)
            r = 5 if i == self._drag_idx else 4
            self.create_oval(px - r, py - r, px + r, py + r, fill=_POINT, outline="#fff", width=1)


class AnimationControls(tk.Frame):
    _PRESETS = (
        AnimationPreset.SPIN,
        AnimationPreset.WIGGLE,
        AnimationPreset.BOB,
        AnimationPreset.ORBIT,
        AnimationPreset.BREATHE,
        AnimationPreset.FLOAT,
        AnimationPreset.CUSTOM,
    )

    _CHANNELS = (
        (CustomChannel.ROT_Y, "Turn Y"),
        (CustomChannel.ROT_X, "Tilt X"),
        (CustomChannel.ROT_Z, "Roll Z"),
        (CustomChannel.POS_Y, "Move up/down"),
        (CustomChannel.POS_X, "Move left/right"),
        (CustomChannel.SCALE, "Size pulse"),
    )

    def __init__(self, parent: tk.Widget, model: ModelState, **kwargs) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        self._silent = False
        cfg = model.animation_config()

        tk.Label(
            self,
            text="Looping motion on top of your current pose",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 6))

        play_row = tk.Frame(self, bg=_BG)
        play_row.pack(fill=tk.X, pady=(0, 8))
        self._play_var = tk.BooleanVar(value=cfg.enabled)
        self._play_btn = tk.Checkbutton(
            play_row,
            text="Play motion",
            variable=self._play_var,
            command=self._on_play_toggle,
            bg=_BG,
            fg=_FG,
            selectcolor="#404550",
            activebackground=_BG,
            activeforeground=_FG,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self._play_btn.pack(side=tk.LEFT)
        tk.Button(
            play_row,
            text="Anchor pose",
            command=self._on_anchor,
            bg="#404550",
            fg=_FG,
            relief=tk.FLAT,
            padx=8,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        preset_row = tk.Frame(self, bg=_BG)
        preset_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(preset_row, text="Style", bg=_BG, fg=_FG, font=("Segoe UI", 9)).pack(
            side=tk.LEFT
        )
        self._preset_var = tk.StringVar(value=preset_label(cfg.preset))
        preset_labels = [preset_label(p) for p in self._PRESETS]
        self._preset_menu = ttk.Combobox(
            preset_row,
            textvariable=self._preset_var,
            values=preset_labels,
            state="readonly",
            width=20,
        )
        self._preset_menu.pack(side=tk.RIGHT)
        self._preset_menu.bind("<<ComboboxSelected>>", self._on_preset)

        self._hint = tk.Label(
            self,
            text="",
            bg=_BG,
            fg="#888",
            font=("Segoe UI", 8),
            wraplength=340,
            justify=tk.LEFT,
        )
        self._hint.pack(anchor=tk.W, pady=(2, 6))

        self._axis_frame = tk.Frame(self, bg=_BG)
        self._axis_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(self._axis_frame, text="Axis", bg=_BG, fg=_FG, font=("Segoe UI", 9)).pack(
            side=tk.LEFT
        )
        self._axis_var = tk.StringVar(value=cfg.axis)
        for ax, label in (("x", "X"), ("y", "Y"), ("z", "Z")):
            tk.Radiobutton(
                self._axis_frame,
                text=label,
                value=ax,
                variable=self._axis_var,
                command=self._on_axis,
                bg=_BG,
                fg=_FG,
                selectcolor="#404550",
                activebackground=_BG,
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=4)

        self._channel_frame = tk.Frame(self, bg=_BG)
        tk.Label(
            self._channel_frame,
            text="Drives",
            bg=_BG,
            fg=_FG,
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W)
        self._channel_var = tk.StringVar(value=cfg.custom_channel.value)
        channel_row = tk.Frame(self._channel_frame, bg=_BG)
        channel_row.pack(fill=tk.X, pady=(2, 0))
        for i, (ch, label) in enumerate(self._CHANNELS):
            tk.Radiobutton(
                channel_row,
                text=label,
                value=ch.value,
                variable=self._channel_var,
                command=self._on_channel,
                bg=_BG,
                fg=_FG,
                selectcolor="#404550",
                activebackground=_BG,
                font=("Segoe UI", 8),
                cursor="hand2",
            ).grid(row=i // 2, column=i % 2, sticky=tk.W, padx=2)

        self._period = _LabeledScale(
            self,
            "Cycle length (sec)",
            PERIOD_MIN,
            PERIOD_MAX,
            cfg.period_sec,
            self._on_period,
            length=320,
            color=_ACCENT,
        )
        self._period.pack(fill=tk.X)

        self._strength = _LabeledScale(
            self,
            preset_strength_label(cfg.preset),
            int(STRENGTH_MIN * 100),
            int(STRENGTH_MAX * 100),
            cfg.strength * 100.0,
            self._on_strength,
            length=320,
            color="#6ecf6e",
        )
        self._strength.pack(fill=tk.X)

        self._wave_frame = tk.Frame(self, bg=_BG)
        tk.Label(
            self._wave_frame,
            text="Drag the wave — one loop = one cycle",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(8, 4))
        wave_tools = tk.Frame(self._wave_frame, bg=_BG)
        wave_tools.pack(fill=tk.X, pady=(0, 4))
        tk.Button(
            wave_tools,
            text="Reset wave",
            command=self._on_reset_wave,
            bg="#404550",
            fg=_FG,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.LEFT)
        self._wave = WaveformCanvas(self._wave_frame, model)
        self._wave.pack()

        self._refresh_preset_ui(cfg.preset)

    def _preset_from_var(self) -> AnimationPreset:
        label = self._preset_var.get()
        for p in self._PRESETS:
            if preset_label(p) == label:
                return p
        try:
            return AnimationPreset(label)
        except ValueError:
            return AnimationPreset.SPIN

    def _on_play_toggle(self) -> None:
        if self._silent:
            return
        self._model.set_animation_enabled(self._play_var.get())

    def _on_anchor(self) -> None:
        self._model.capture_animation_base()

    def _on_preset(self, _event=None) -> None:
        if self._silent:
            return
        preset = self._preset_from_var()
        self._model.set_animation_preset(preset)
        if preset != AnimationPreset.OFF:
            self._silent = True
            self._play_var.set(True)
            self._model.set_animation_enabled(True)
            self._silent = False
        self._refresh_preset_ui(preset)

    def _on_axis(self) -> None:
        if self._silent:
            return
        self._model.set_animation_axis(self._axis_var.get())

    def _on_channel(self) -> None:
        if self._silent:
            return
        try:
            ch = CustomChannel(self._channel_var.get())
        except ValueError:
            return
        self._model.set_animation_custom_channel(ch)

    def _on_period(self, value: float) -> None:
        if self._silent:
            return
        self._model.set_animation_period(value)

    def _on_strength(self, value: float) -> None:
        if self._silent:
            return
        self._model.set_animation_strength(value / 100.0)

    def _on_reset_wave(self) -> None:
        self._model.reset_animation_curve()
        self._wave.redraw()

    def _refresh_preset_ui(self, preset: AnimationPreset) -> None:
        hints = {
            AnimationPreset.SPIN: "Full 360° turn on the chosen axis, every cycle.",
            AnimationPreset.WIGGLE: "Gentle back-and-forth tilt. Good for idle life.",
            AnimationPreset.BOB: "Float up and down in place.",
            AnimationPreset.ORBIT: "Circle around the spot where you anchored.",
            AnimationPreset.BREATHE: "Slow size pulse, like breathing.",
            AnimationPreset.FLOAT: "Soft bob + drift combined.",
            AnimationPreset.CUSTOM: "Draw your own loop on the graph below.",
        }
        self._hint.config(text=hints.get(preset, ""))

        show_axis = preset in (AnimationPreset.SPIN, AnimationPreset.WIGGLE)
        if show_axis:
            self._axis_frame.pack(fill=tk.X, pady=(0, 4), before=self._period)
        else:
            self._axis_frame.pack_forget()

        if preset == AnimationPreset.CUSTOM:
            self._channel_frame.pack(fill=tk.X, pady=(0, 4), before=self._period)
            self._wave_frame.pack(fill=tk.X, pady=(4, 0))
        else:
            self._channel_frame.pack_forget()
            self._wave_frame.pack_forget()

        lo = SPIN_PERIOD_MIN if preset == AnimationPreset.SPIN else PERIOD_MIN
        hi = SPIN_PERIOD_MAX if preset == AnimationPreset.SPIN else PERIOD_MAX
        cfg = self._model.animation_config()
        self._silent = True
        self._period._scale.config(from_=lo, to=hi)
        self._period.set(cfg.period_sec)
        self._strength.set_title(preset_strength_label(preset))
        self._strength.set(cfg.strength * 100.0)
        self._silent = False

        # Friendly labels in combobox
        self._preset_menu.config(values=[preset_label(p) for p in self._PRESETS])
        self._preset_var.set(preset_label(preset))

    def sync(self) -> None:
        cfg = self._model.animation_config()
        self._silent = True
        self._play_var.set(cfg.enabled)
        self._preset_var.set(preset_label(cfg.preset))
        self._axis_var.set(cfg.axis)
        self._channel_var.set(cfg.custom_channel.value)
        self._refresh_preset_ui(cfg.preset)
        self._silent = False
        if cfg.preset == AnimationPreset.CUSTOM:
            self._wave.redraw()
