"""Draggable tk.Scale bars for depth, rotation, and scale."""

from __future__ import annotations

import tkinter as tk

from model_state import ModelState

_BG = "#2b2d30"
_FG = "#e8e8e8"
_RED = "#e05a5a"
_GREEN = "#6ecf6e"
_BLUE = "#5a9ee0"


class _LabeledScale(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        from_: float,
        to: float,
        value: float,
        command,
        length: int = 300,
        color: str = _FG,
    ) -> None:
        super().__init__(parent, bg=_BG)
        tk.Label(self, text=label, bg=_BG, fg=color, font=("Segoe UI", 9)).pack(
            anchor=tk.W
        )
        self._var = tk.DoubleVar(value=value)
        self._scale = tk.Scale(
            self,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            length=length,
            resolution=max((to - from_) / 200.0, 0.01),
            variable=self._var,
            command=command,
            bg=_BG,
            fg=_FG,
            troughcolor="#40444b",
            highlightthickness=0,
            sliderrelief=tk.RAISED,
            cursor="hand2",
        )
        self._scale.pack(fill=tk.X, pady=(2, 8))

    def set(self, value: float) -> None:
        self._var.set(value)


class MoveDepthControl(tk.Frame):
    """Depth = toward/away from camera (same as Z axis). One slider, no duplicate gizmo Z."""

    def __init__(self, parent: tk.Widget, model: ModelState, **kwargs) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        tk.Label(
            self,
            text="Depth — near ◄──────► far  (toward / away from camera)",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(4, 0))
        self._depth = _LabeledScale(
            self,
            "Distance",
            0,
            100,
            model.depth_norm() * 100.0,
            self._on_depth,
            color=_BLUE,
        )

    def _on_depth(self, value: str) -> None:
        self._model.set_depth_norm(float(value) / 100.0)

    def sync(self) -> None:
        self._depth.set(self._model.depth_norm() * 100.0)


class RotateControls(tk.Frame):
    def __init__(self, parent: tk.Widget, model: ModelState, **kwargs) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        tk.Label(
            self,
            text="Drag a bar to rotate",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 4))

        self._sx = _LabeledScale(
            self, "Tilt X", -180, 180, model.euler_deg[0], self._on_x, color=_RED
        )
        self._sy = _LabeledScale(
            self, "Turn Y", -180, 180, model.euler_deg[1], self._on_y, color=_GREEN
        )
        self._sz = _LabeledScale(
            self, "Roll Z", -180, 180, model.euler_deg[2], self._on_z, color=_BLUE
        )

    def _on_x(self, v: str) -> None:
        self._model.set_euler_axis("x", float(v))

    def _on_y(self, v: str) -> None:
        self._model.set_euler_axis("y", float(v))

    def _on_z(self, v: str) -> None:
        self._model.set_euler_axis("z", float(v))

    def sync(self) -> None:
        e = self._model.euler_deg
        self._sx.set(e[0])
        self._sy.set(e[1])
        self._sz.set(e[2])


class ScaleControls(tk.Frame):
    def __init__(self, parent: tk.Widget, model: ModelState, **kwargs) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        tk.Label(
            self,
            text="Drag to resize",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 4))
        self._scale = _LabeledScale(
            self,
            "Size",
            int(ModelState.SCALE_MIN * 100),
            int(ModelState.SCALE_MAX * 100),
            model.scale * 100.0,
            self._on_scale,
            color=_BLUE,
        )

    def _on_scale(self, v: str) -> None:
        self._model.set_scale(float(v) / 100.0)

    def sync(self) -> None:
        self._scale.set(self._model.scale * 100.0)
