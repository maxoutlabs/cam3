"""Live camera preview with draggable model position marker."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from PIL import Image, ImageDraw, ImageTk

from model_state import ModelState
from preview_feed import PreviewFeed, PreviewSnapshot

_BG = "#121316"
_MARKER = "#5ad4ff"
_MARKER_RING = "#ffffff"


class CameraViewport(tk.Frame):
    """Rectangle showing the feed; drag the marker to move the model on screen."""

    def __init__(
        self,
        parent: tk.Widget,
        model: ModelState,
        feed: PreviewFeed,
        width: int = 384,
        height: int = 216,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._model = model
        self._feed = feed
        self._w = width
        self._h = height
        self._photo: ImageTk.PhotoImage | None = None
        self._dragging = False
        self._on_change: Callable[[], None] | None = None

        tk.Label(
            self,
            text="Camera view — drag the dot to move the model",
            bg=_BG,
            fg="#aaa",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W)

        body = tk.Frame(self, bg=_BG)
        body.pack()

        self._canvas = tk.Canvas(
            body,
            width=width,
            height=height,
            bg="#0a0a0c",
            highlightthickness=1,
            highlightbackground="#444",
        )
        self._canvas.pack(side=tk.LEFT)

        self._depth = tk.Scale(
            body,
            from_=0,
            to=100,
            orient=tk.VERTICAL,
            label="Depth",
            length=height - 10,
            command=self._on_depth,
            bg=_BG,
            fg="#ccc",
            troughcolor="#333",
            highlightthickness=0,
        )
        self._depth.set(50)
        self._depth.pack(side=tk.LEFT, padx=(6, 0))

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

    def set_on_change(self, cb: Callable[[], None]) -> None:
        self._on_change = cb

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()

    def _on_depth(self, value: str) -> None:
        self._model.set_depth_norm(float(value) / 100.0)
        self._notify()

    def refresh(self, snap: PreviewSnapshot | None = None) -> None:
        if snap is None:
            snap = self._feed.get()
        self._canvas.delete("all")

        if snap.rgb is not None:
            img = Image.fromarray(snap.rgb)
            draw = ImageDraw.Draw(img)
            if snap.has_model:
                if snap.model_px:
                    mx, my = snap.model_px
                else:
                    nx, ny = self._model.screen_norm_from_position()
                    mx, my = nx * snap.preview_w, ny * snap.preview_h
                r = 10
                draw.ellipse(
                    (mx - r, my - r, mx + r, my + r),
                    outline=_MARKER_RING,
                    width=2,
                )
                draw.ellipse(
                    (mx - 5, my - 5, mx + 5, my + 5),
                    fill=_MARKER,
                    outline=_MARKER_RING,
                )
            self._photo = ImageTk.PhotoImage(img)
            self._canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)
        else:
            self._canvas.create_text(
                self._w // 2,
                self._h // 2,
                text="Waiting for camera…",
                fill="#666",
                font=("Segoe UI", 10),
            )

        if not self._dragging:
            self._depth.set(int(self._model.depth_norm() * 100))

    def _event_to_norm(self, event: tk.Event) -> tuple[float, float]:
        nx = max(0.0, min(1.0, event.x / self._w))
        ny = max(0.0, min(1.0, event.y / self._h))
        return nx, ny

    def _on_press(self, event: tk.Event) -> None:
        self._dragging = True
        self._model.set_screen_norm(*self._event_to_norm(event))
        self._notify()

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        self._model.set_screen_norm(*self._event_to_norm(event))
        self._notify()

    def _on_release(self, _event: tk.Event) -> None:
        self._dragging = False
