"""Small tray-opened control panel: Move / Rotate / Scale (gizmo-style)."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from model_state import ControlMode, ModelState

logger = logging.getLogger(__name__)

_BG = "#2b2d30"
_PANEL = "#35373b"
_FG = "#e8e8e8"
_RED = "#e05a5a"
_GREEN = "#6ecf6e"
_BLUE = "#5a9ee0"
_ACCENT = "#4a8fd4"


class ControlsWindow:
    """Floating panel; safe to open from pystray callback (own thread + Tk root)."""

    def __init__(self, model: ModelState, on_close: Callable[[], None] | None = None) -> None:
        self._model = model
        self._on_close = on_close
        self._root: tk.Tk | None = None
        self._repeat_id: str | None = None
        self._repeat_action: Callable[[], None] | None = None
        self._thread: threading.Thread | None = None

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
        self._cancel_repeat()
        self._model.set_show_gizmo(False)
        if self._root:
            self._root.destroy()
            self._root = None
        if self._on_close:
            self._on_close()

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
        style.configure("TButton", font=("Segoe UI", 9), padding=4)
        style.configure("Mode.TButton", font=("Segoe UI", 9, "bold"), padding=6)
        style.map(
            "Mode.TButton",
            background=[("active", _PANEL)],
            foreground=[("active", _FG)],
        )

        outer = ttk.Frame(self._root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="3D Transform", font=("Segoe UI", 11, "bold")).pack(
            anchor=tk.W, pady=(0, 8)
        )

        mode_row = ttk.Frame(outer)
        mode_row.pack(fill=tk.X, pady=(0, 10))
        self._mode_var = tk.StringVar(value=ControlMode.MOVE.value)

        for label, mode in (("Move", ControlMode.MOVE), ("Rotate", ControlMode.ROTATE), ("Scale", ControlMode.SCALE)):
            ttk.Button(
                mode_row,
                text=label,
                style="Mode.TButton",
                command=lambda m=mode: self._set_mode(m),
                width=8,
            ).pack(side=tk.LEFT, padx=2)

        self._body = ttk.Frame(outer)
        self._body.pack(fill=tk.BOTH, expand=True)

        step_row = ttk.Frame(outer)
        step_row.pack(fill=tk.X, pady=10)
        ttk.Label(step_row, text="Step").pack(side=tk.LEFT)
        self._step_var = tk.StringVar(value="normal")
        for name in ("fine", "normal", "coarse"):
            ttk.Radiobutton(
                step_row,
                text=name.capitalize(),
                value=name,
                variable=self._step_var,
                command=self._on_step,
            ).pack(side=tk.LEFT, padx=6)

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Reset", command=self._model.reset).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Hide", command=self._destroy).pack(side=tk.RIGHT)

        self._rebuild_body()
        self._set_mode(ControlMode.MOVE)
        self._root.mainloop()

    def _set_mode(self, mode: ControlMode) -> None:
        self._mode_var.set(mode.value)
        self._model.set_mode(mode)
        self._rebuild_body()

    def _on_step(self) -> None:
        self._model.set_step(self._step_var.get())

    def _rebuild_body(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()
        mode = ControlMode(self._mode_var.get())
        if mode == ControlMode.MOVE:
            self._build_move()
        elif mode == ControlMode.ROTATE:
            self._build_rotate()
        else:
            self._build_scale()

    def _bind_hold(self, widget: tk.Widget, action: Callable[[], None]) -> None:
        def on_press(_e: tk.Event) -> None:
            action()
            self._start_repeat(action)

        def on_release(_e: tk.Event) -> None:
            self._cancel_repeat()

        widget.bind("<ButtonPress-1>", on_press)
        widget.bind("<ButtonRelease-1>", on_release)
        widget.bind("<Leave>", on_release)

    def _start_repeat(self, action: Callable[[], None]) -> None:
        self._cancel_repeat()
        self._repeat_action = action

        def tick() -> None:
            if self._repeat_action:
                self._repeat_action()
                self._repeat_id = self._root.after(80, tick)  # type: ignore[union-attr]

        self._repeat_id = self._root.after(350, tick)  # type: ignore[union-attr]

    def _cancel_repeat(self) -> None:
        if self._root and self._repeat_id:
            self._root.after_cancel(self._repeat_id)
        self._repeat_id = None
        self._repeat_action = None

    def _axis_btn(self, parent: tk.Widget, text: str, color: str, action: Callable[[], None]) -> tk.Button:
        b = tk.Button(
            parent,
            text=text,
            fg="white",
            bg=color,
            activebackground=color,
            activeforeground="white",
            relief=tk.FLAT,
            width=5,
            height=1,
            cursor="hand2",
        )
        b.pack(pady=2)
        self._bind_hold(b, action)
        return b

    def _build_move(self) -> None:
        f = ttk.Frame(self._body)
        f.pack()
        ttk.Label(f, text="Screen axes (matches your webcam)", foreground="#aaa").pack(
            pady=(0, 6)
        )
        col = tk.Frame(f, bg=_BG)
        col.pack()
        self._axis_btn(col, "▲ Up", _GREEN, lambda: self._model.nudge_move_screen(0, 1, 0))
        mid = tk.Frame(col, bg=_BG)
        mid.pack()
        self._axis_btn(mid, "◀ Left", _RED, lambda: self._model.nudge_move_screen(-1, 0, 0))
        self._axis_btn(mid, "Right ▶", _RED, lambda: self._model.nudge_move_screen(1, 0, 0))
        self._axis_btn(col, "▼ Down", _GREEN, lambda: self._model.nudge_move_screen(0, -1, 0))
        depth = tk.Frame(f, bg=_BG)
        depth.pack(pady=8)
        self._axis_btn(depth, "Toward you", _BLUE, lambda: self._model.nudge_move_screen(0, 0, 1))
        self._axis_btn(depth, "Away", _BLUE, lambda: self._model.nudge_move_screen(0, 0, -1))

    def _build_rotate(self) -> None:
        f = ttk.Frame(self._body)
        f.pack()
        ttk.Label(f, text="Hold to spin around axis", foreground="#aaa").pack(pady=(0, 6))
        for axis, color, label in (
            ("x", _RED, "X (tilt)"),
            ("y", _GREEN, "Y (pan)"),
            ("z", _BLUE, "Z (roll)"),
        ):
            row = tk.Frame(f, bg=_BG)
            row.pack(pady=3)
            ttk.Label(row, text=label, width=10).pack(side=tk.LEFT)
            pair = tk.Frame(row, bg=_BG)
            pair.pack(side=tk.LEFT)
            self._axis_btn(pair, "−", color, lambda a=axis: self._model.nudge_rotate(a, -1))
            self._axis_btn(pair, "+", color, lambda a=axis: self._model.nudge_rotate(a, 1))

    def _build_scale(self) -> None:
        f = ttk.Frame(self._body)
        f.pack()
        ttk.Label(f, text="Uniform size", foreground="#aaa").pack(pady=(0, 8))
        row = tk.Frame(f, bg=_BG)
        row.pack()
        self._axis_btn(row, "Smaller", _BLUE, lambda: self._model.nudge_scale_uniform(-1))
        self._axis_btn(row, "Bigger", _BLUE, lambda: self._model.nudge_scale_uniform(1))
