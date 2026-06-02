"""Transform panel: camera viewport + Blender-style draggable gizmo."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

from gizmo_widget import TransformGizmo
from model_state import ControlMode, ModelState
from preview_feed import PreviewFeed
from viewport_widget import CameraViewport

if TYPE_CHECKING:
    from camera_streamer import CameraStreamer

_BG = "#2b2d30"
_FG = "#e8e8e8"


class ControlsWindow:
    def __init__(
        self,
        streamer: "CameraStreamer",
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._streamer = streamer
        self._model: ModelState = streamer.model
        self._feed: PreviewFeed = streamer.preview
        self._on_close = on_close
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._viewport: CameraViewport | None = None
        self._gizmo: TransformGizmo | None = None
        self._tick_id: str | None = None

    @property
    def is_open(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def open(self) -> None:
        if self.is_open:
            self._root.after(0, self._lift)  # type: ignore[union-attr]
            return
        self._thread = threading.Thread(target=self._run, name="ControlsUI", daemon=True)
        self._thread.start()

    def close(self) -> None:
        if self._root:
            try:
                self._root.after(0, self._destroy)
            except Exception:
                pass

    def _lift(self) -> None:
        if self._root:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()

    def _destroy(self) -> None:
        if self._tick_id and self._root:
            self._root.after_cancel(self._tick_id)
        self._tick_id = None
        self._model.set_show_gizmo(False)
        if self._root:
            self._root.destroy()
            self._root = None
        if self._on_close:
            self._on_close()

    def _tick(self) -> None:
        if self._viewport:
            self._viewport.refresh()
        if self._root:
            self._tick_id = self._root.after(66, self._tick)

    def _run(self) -> None:
        self._model.set_show_gizmo(True)
        self._root = tk.Tk()
        self._root.title("Cam3 — Transform")
        self._root.configure(bg=_BG)
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)
        self._root.protocol("WM_DELETE_WINDOW", self._destroy)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=_BG)
        style.configure("TLabel", background=_BG, foreground=_FG, font=("Segoe UI", 9))

        outer = ttk.Frame(self._root, padding=10)
        outer.pack()

        ttk.Label(outer, text="Transform", font=("Segoe UI", 11, "bold")).pack(
            anchor=tk.W, pady=(0, 6)
        )

        mode_row = ttk.Frame(outer)
        mode_row.pack(fill=tk.X, pady=(0, 8))
        self._mode_var = tk.StringVar(value=ControlMode.MOVE.value)

        for label, mode in (
            ("G  Move", ControlMode.MOVE),
            ("R  Rotate", ControlMode.ROTATE),
            ("S  Scale", ControlMode.SCALE),
        ):
            ttk.Button(
                mode_row,
                text=label,
                command=lambda m=mode: self._set_mode(m),
                width=9,
            ).pack(side=tk.LEFT, padx=2)

        content = ttk.Frame(outer)
        content.pack()

        left = ttk.Frame(content)
        left.pack(side=tk.LEFT, padx=(0, 10))
        self._viewport = CameraViewport(left, self._model, self._feed)
        self._viewport.pack()

        right = ttk.Frame(content)
        right.pack(side=tk.LEFT)
        ttk.Label(right, text="Gizmo", foreground="#aaa").pack()
        self._gizmo = TransformGizmo(right, self._model, size=220)
        self._gizmo.pack()

        step_row = ttk.Frame(outer)
        step_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(step_row, text="Sensitivity").pack(side=tk.LEFT)
        self._step_var = tk.StringVar(value="normal")
        for name in ("fine", "normal", "coarse"):
            ttk.Radiobutton(
                step_row,
                text=name.capitalize(),
                value=name,
                variable=self._step_var,
                command=lambda: self._model.set_step(self._step_var.get()),
            ).pack(side=tk.LEFT, padx=6)

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Reset", command=self._model.reset).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Hide", command=self._destroy).pack(side=tk.RIGHT)

        self._set_mode(ControlMode.MOVE)
        self._tick()
        self._root.mainloop()

    def _set_mode(self, mode: ControlMode) -> None:
        self._mode_var.set(mode.value)
        self._model.set_mode(mode)
        if self._gizmo:
            self._gizmo.set_mode(mode)
