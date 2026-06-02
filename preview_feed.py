"""Thread-safe latest frame + model screen position for the control panel."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np


@dataclass
class PreviewSnapshot:
    """Small RGB preview and where the model sits on it (pixel coords)."""

    rgb: np.ndarray | None
    preview_w: int
    preview_h: int
    model_px: tuple[float, float] | None
    source_w: int
    source_h: int
    has_model: bool


class PreviewFeed:
    def __init__(self, preview_width: int = 384, preview_height: int = 216) -> None:
        self.preview_width = preview_width
        self.preview_height = preview_height
        self._lock = threading.Lock()
        self._snap = PreviewSnapshot(
            None, preview_width, preview_height, None, 0, 0, False
        )

    def update(
        self,
        frame_bgr: np.ndarray,
        model_screen: tuple[float, float] | None,
        has_model: bool,
    ) -> None:
        import cv2

        src_h, src_w = frame_bgr.shape[:2]
        small = cv2.resize(
            frame_bgr,
            (self.preview_width, self.preview_height),
            interpolation=cv2.INTER_AREA,
        )
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        model_px = None
        if model_screen is not None and src_w > 0 and src_h > 0:
            u, v = model_screen
            sx = u / src_w * self.preview_width
            sy = v / src_h * self.preview_height
            model_px = (float(sx), float(sy))

        with self._lock:
            self._snap = PreviewSnapshot(
                rgb=rgb,
                preview_w=self.preview_width,
                preview_h=self.preview_height,
                model_px=model_px,
                source_w=src_w,
                source_h=src_h,
                has_model=has_model,
            )

    def get(self) -> PreviewSnapshot:
        with self._lock:
            s = self._snap
            return PreviewSnapshot(
                rgb=s.rgb.copy() if s.rgb is not None else None,
                preview_w=s.preview_w,
                preview_h=s.preview_h,
                model_px=s.model_px,
                source_w=s.source_w,
                source_h=s.source_h,
                has_model=s.has_model,
            )
