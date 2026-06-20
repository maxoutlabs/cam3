"""Transform panel: screen pad + drag sliders (no live webcam, no feed overlay)."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

import platform_support

from animation_controls import AnimationControls
from drag_controls import MoveDepthControl, RotateControls, ScaleControls
from model_state import ControlMode, ModelState
from screen_pad import ScreenPad

if TYPE_CHECKING:
    from camera_streamer import CameraStreamer

logger = logging.getLogger(__name__)

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
        self._on_close = on_close
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._done = threading.Event()
        self._done.set()
        self._body: ttk.Frame | None = None
        self._mode_var: tk.StringVar | None = None
        self._pad: ScreenPad | None = None
        self._move_extra: MoveDepthControl | None = None
        self._rotate: RotateControls | None = None
        self._scale: ScaleControls | None = None
        self._animate: AnimationControls | None = None

    @property
    def is_open(self) -> bool:
        return self._root is not None

    def open(self) -> None:
        if self._root is not None:
            try:
                self._root.after(0, self._lift)
            except (RuntimeError, tk.TclError):
                self._root = None
            else:
                return
        if self._thread and self._thread.is_alive():
            return
        self._done.clear()
        self._thread = threading.Thread(target=self._run, name="ControlsUI", daemon=True)
        self._thread.start()

    def shutdown(self, wait: bool = True, timeout: float = 2.5) -> None:
        """Quit Tk mainloop and tear down the UI thread."""
        root = self._root
        if root is not None:
            try:
                root.after(0, self._quit_on_main)
            except (RuntimeError, tk.TclError):
                pass
        if wait and self._thread and self._thread.is_alive():
            self._done.wait(timeout=timeout)
            self._thread.join(timeout=timeout)

    def _quit_on_main(self) -> None:
        self._clear_mode_widgets()
        root = self._root
        if root is None:
            return
        try:
            root.quit()
        except tk.TclError:
            pass
        self._destroy()

    def _lift(self) -> None:
        if self._root:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()

    def _clear_mode_widgets(self) -> None:
        self._pad = None
        self._move_extra = None
        self._rotate = None
        self._scale = None
        self._animate = None

    def _destroy(self) -> None:
        self._clear_mode_widgets()
        root = self._root
        self._root = None
        self._body = None
        self._mode_var = None
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
        if self._on_close:
            self._on_close()

    def _run(self) -> None:
        try:
            self._root = tk.Tk()
            self._root.title("Cam3 — Transform")
            self._root.configure(bg=_BG)
            self._root.resizable(True, False)
            self._root.minsize(400, 220)
            if platform_support.current_os() != platform_support.OS.MACOS:
                self._root.attributes("-topmost", True)
            self._root.protocol("WM_DELETE_WINDOW", self._quit_on_main)

            style = ttk.Style(self._root)
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
                ("Move", ControlMode.MOVE),
                ("Rotate", ControlMode.ROTATE),
                ("Scale", ControlMode.SCALE),
                ("Animate", ControlMode.ANIMATE),
            ):
                ttk.Button(
                    mode_row,
                    text=label,
                    command=lambda m=mode: self._show_mode(m),
                    width=8,
                ).pack(side=tk.LEFT, padx=2)

            self._body = ttk.Frame(outer)
            self._body.pack(fill=tk.BOTH)

            btn_row = ttk.Frame(outer)
            btn_row.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(btn_row, text="Reset", command=self._on_reset).pack(side=tk.LEFT)
            ttk.Button(btn_row, text="Hide", command=self._quit_on_main).pack(side=tk.RIGHT)

            self._show_mode(ControlMode.MOVE)
            self._root.mainloop()
        except Exception:
            logger.exception("Transform panel failed")
        finally:
            self._destroy()
            self._thread = None
            self._done.set()

    def _on_reset(self) -> None:
        self._model.reset()
        if self._mode_var is not None:
            self._show_mode(ControlMode(self._mode_var.get()))

    def _show_mode(self, mode: ControlMode) -> None:
        if self._mode_var is not None:
            self._mode_var.set(mode.value)
        self._model.set_mode(mode)
        if self._body is None:
            return
        self._clear_mode_widgets()
        for w in self._body.winfo_children():
            w.destroy()

        if mode == ControlMode.MOVE:
            self._pad = ScreenPad(
                self._body,
                self._model,
                mirror_x=platform_support.default_screen_mirror(),
            )
            self._pad.pack()
            self._move_extra = MoveDepthControl(self._body, self._model)
            self._move_extra.pack(fill=tk.X)
        elif mode == ControlMode.ROTATE:
            self._rotate = RotateControls(self._body, self._model)
            self._rotate.pack(fill=tk.X)
        elif mode == ControlMode.SCALE:
            self._scale = ScaleControls(self._body, self._model)
            self._scale.pack(fill=tk.X)
        else:
            self._animate = AnimationControls(self._body, self._model)
            self._animate.pack(fill=tk.X)
