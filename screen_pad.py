"""Simple screen rectangle — drag the dot to place the model (no webcam preview)."""

from __future__ import annotations

import tkinter as tk

from model_state import ModelState

_BG = "#121316"
_FRAME = "#2a2d34"
_BORDER = "#4a4f58"
_DOT = "#5ad4ff"
_DOT_RING = "#ffffff"
_GRID = "#333840"


class ScreenPad(tk.Frame):
    """
    Abstract 16:9 screen. Drag the dot for left/right and up/down.
    mirror_x=True matches a horizontally flipped webcam (common with OBS).
    """

    def __init__(
        self,
        parent: tk.Widget,
        model: ModelState,
        width: int = 360,
        height: int = 202,
        mirror_x: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        self._pw = width
        self._ph = height
        self._mirror_x = mirror_x
        self._dragging = False

        tk.Label(
            self,
            text="Screen — drag the dot to position the model",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 4))

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=_FRAME,
            highlightthickness=1,
            highlightbackground=_BORDER,
            cursor="hand2",
        )
        self._canvas.pack()

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        self.redraw()

    def redraw(self) -> None:
        c = self._canvas
        try:
            if not c.winfo_exists():
                return
        except tk.TclError:
            return
        c.delete("all")
        w, h = self._pw, self._ph

        for i in range(1, 4):
            x = w * i // 4
            y = h * i // 4
            c.create_line(x, 0, x, h, fill=_GRID)
            c.create_line(0, y, w, y, fill=_GRID)

        c.create_text(8, 10, text="L", fill="#666", font=("Segoe UI", 7))
        c.create_text(w - 8, 10, text="R", fill="#666", font=("Segoe UI", 7))
        c.create_text(w // 2, 10, text="top", fill="#666", font=("Segoe UI", 7))

        nx, ny = self._model.screen_norm_from_target()
        if self._mirror_x:
            nx = 1.0 - nx
        px, py = nx * w, ny * h

        c.create_oval(px - 11, py - 11, px + 11, py + 11, outline=_DOT_RING, width=2)
        c.create_oval(px - 6, py - 6, px + 6, py + 6, fill=_DOT, outline=_DOT_RING)

    def _apply(self, event: tk.Event) -> None:
        nx = max(0.0, min(1.0, event.x / self._pw))
        ny = max(0.0, min(1.0, event.y / self._ph))
        if self._mirror_x:
            nx = 1.0 - nx
        self._model.set_screen_norm(nx, ny)
        self.redraw()

    def _on_press(self, event: tk.Event) -> None:
        self._dragging = True
        self._apply(event)

    def _on_drag(self, event: tk.Event) -> None:
        if self._dragging:
            self._apply(event)

    def _on_release(self, _event: tk.Event) -> None:
        self._dragging = False
