"""Draggable tk.Scale bars for depth, rotation, and scale."""

from __future__ import annotations

import tkinter as tk

from model_state import ModelState

_BG = "#2b2d30"
_FG = "#e8e8e8"
_TROUGH = "#505560"
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
        on_change,
        length: int = 320,
        color: str = _FG,
    ) -> None:
        super().__init__(parent, bg=_BG)
        self._on_change = on_change
        self._silent = True
        tk.Label(self, text=label, bg=_BG, fg=color, font=("Segoe UI", 9, "bold")).pack(
            anchor=tk.W
        )
        self._var = tk.DoubleVar(value=value)
        res = max((to - from_) / 180.0, 0.1)
        self._scale = tk.Scale(
            self,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            length=length,
            resolution=res,
            variable=self._var,
            showvalue=True,
            bg=_BG,
            fg=_FG,
            troughcolor=_TROUGH,
            activebackground=color,
            highlightthickness=0,
            sliderrelief=tk.RAISED,
            sliderlength=22,
            width=22,
            cursor="hand2",
            command=self._cmd,
        )
        self._scale.pack(fill=tk.X, pady=(4, 10))
        self._silent = False

    def _cmd(self, value: str) -> None:
        if self._silent:
            return
        self._on_change(float(value))

    def set(self, value: float) -> None:
        self._silent = True
        self._var.set(value)
        self._silent = False


class MoveDepthControl(tk.Frame):
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
            lambda v: model.set_depth_norm(v / 100.0),
            color=_BLUE,
        )
        self._depth.pack(fill=tk.X)

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
            self,
            "Tilt X",
            -180,
            180,
            float(model.euler_deg[0]),
            lambda v: model.set_euler_axis("x", v),
            color=_RED,
        )
        self._sx.pack(fill=tk.X)
        self._sy = _LabeledScale(
            self,
            "Turn Y",
            -180,
            180,
            float(model.euler_deg[1]),
            lambda v: model.set_euler_axis("y", v),
            color=_GREEN,
        )
        self._sy.pack(fill=tk.X)
        self._sz = _LabeledScale(
            self,
            "Roll Z",
            -180,
            180,
            float(model.euler_deg[2]),
            lambda v: model.set_euler_axis("z", v),
            color=_BLUE,
        )
        self._sz.pack(fill=tk.X)

    def sync(self) -> None:
        e = self._model.euler_deg
        self._sx.set(float(e[0]))
        self._sy.set(float(e[1]))
        self._sz.set(float(e[2]))


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
            lambda v: model.set_scale(v / 100.0),
            color=_BLUE,
        )
        self._scale.pack(fill=tk.X)

    def sync(self) -> None:
        self._scale.set(self._model.scale * 100.0)
