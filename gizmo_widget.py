"""Blender-style draggable transform gizmo on a tkinter Canvas."""

from __future__ import annotations

import math
import tkinter as tk

from model_state import ControlMode, ModelState

RED = "#e05a5a"
GREEN = "#6ecf6e"
BLUE = "#5a9ee0"
CENTER = "#f0f0f0"
BG = "#1e1f22"
HIT = 14


class TransformGizmo(tk.Canvas):
    """Drag arrows (move), rings (rotate), or handles (scale)."""

    def __init__(
        self,
        parent: tk.Widget,
        model: ModelState,
        size: int = 220,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=BG,
            highlightthickness=0,
            **kwargs,
        )
        self._model = model
        self._size = size
        self._cx = size // 2
        self._cy = size // 2
        self._arm = int(size * 0.36)
        self._drag_axis: str | None = None
        self._last_x = 0
        self._last_y = 0
        self._press_angle = 0.0
        self._mode = ControlMode.MOVE

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Leave>", self._on_release)

    def set_mode(self, mode: ControlMode) -> None:
        self._mode = mode
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        cx, cy, arm = self._cx, self._cy, self._arm

        if self._mode == ControlMode.MOVE:
            self._arrow(cx, cy, cx + arm, cy, RED, "x")
            self._arrow(cx, cy, cx, cy - arm, GREEN, "y")
            self._arrow(cx, cy, cx + arm * 0.55, cy + arm * 0.55, BLUE, "z")
            self.create_text(cx, 12, text="Drag an axis", fill="#888", font=("Segoe UI", 8))
        elif self._mode == ControlMode.ROTATE:
            self.create_oval(
                cx - arm, cy - arm // 3, cx + arm, cy + arm // 3,
                outline=RED, width=2, tags="axis_x",
            )
            self.create_oval(
                cx - arm // 3, cy - arm, cx + arm // 3, cy + arm,
                outline=GREEN, width=2, tags="axis_y",
            )
            self.create_oval(
                cx - arm, cy - arm, cx + arm, cy + arm,
                outline=BLUE, width=2, tags="axis_z",
            )
            self.create_text(cx, 12, text="Drag a ring", fill="#888", font=("Segoe UI", 8))
        else:
            self._scale_handle(cx, cy, cx + arm, cy, RED, "x")
            self._scale_handle(cx, cy, cx, cy - arm, GREEN, "y")
            self._scale_handle(cx, cy, cx + arm * 0.55, cy + arm * 0.55, BLUE, "z")
            self.create_text(cx, 12, text="Drag a handle", fill="#888", font=("Segoe UI", 8))

        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=CENTER, outline="#666")

    def _arrow(
        self, x0: int, y0: int, x1: int, y1: int, color: str, tag: str
    ) -> None:
        self.create_line(x0, y0, x1, y1, fill=color, width=3, tags=tag, arrow=tk.LAST)

    def _scale_handle(
        self, x0: int, y0: int, x1: int, y1: int, color: str, tag: str
    ) -> None:
        self.create_line(x0, y0, x1, y1, fill=color, width=2, tags=tag)
        self.create_rectangle(
            x1 - 5, y1 - 5, x1 + 5, y1 + 5, fill=color, outline="", tags=tag
        )

    def _axis_vectors(self) -> dict[str, tuple[float, float]]:
        arm = self._arm
        return {
            "x": (1.0, 0.0),
            "y": (0.0, -1.0),
            "z": (0.707, 0.707),
        }

    def _pick_axis(self, x: int, y: int) -> str | None:
        cx, cy = self._cx, self._cy
        best: str | None = None
        best_d = HIT * HIT
        for axis, (vx, vy) in self._axis_vectors().items():
            if self._mode == ControlMode.ROTATE:
                # Distance to ellipse approximation
                if axis == "x":
                    d = abs((y - cy) / max(arm / 3, 1))
                elif axis == "y":
                    d = abs((x - cx) / max(arm / 3, 1))
                else:
                    d = abs(math.hypot(x - cx, y - cy) - arm) / arm
                score = d
            else:
                hx, hy = cx + vx * arm, cy + vy * arm
                score = math.hypot(x - hx, y - hy)
            if score < best_d:
                best_d = score
                best = axis
        return best

    def _on_press(self, event: tk.Event) -> None:
        self._drag_axis = self._pick_axis(event.x, event.y)
        self._last_x = event.x
        self._last_y = event.y
        if self._mode == ControlMode.ROTATE:
            self._press_angle = math.atan2(
                event.y - self._cy, event.x - self._cx
            )

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_axis is None:
            return

        if self._mode == ControlMode.ROTATE:
            angle = math.atan2(event.y - self._cy, event.x - self._cx)
            delta_deg = math.degrees(angle - self._press_angle)
            self._press_angle = angle
            self._model.drag_rotate_axis(self._drag_axis, delta_deg)
        else:
            dx = event.x - self._last_x
            dy = event.y - self._last_y
            self._last_x = event.x
            self._last_y = event.y
            vx, vy = self._axis_vectors()[self._drag_axis]
            along = dx * vx + dy * vy
            if self._mode == ControlMode.MOVE:
                self._model.drag_move_axis(self._drag_axis, along)
            else:
                self._model.drag_scale(along * 2.5)

        self._redraw()

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_axis = None
