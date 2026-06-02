"""Lightweight 2D gizmo hint drawn on the composited frame (no MediaPipe)."""

from __future__ import annotations

import cv2

from model_state import ControlMode, TransformSnapshot

# BGR
RED = (68, 68, 255)
GREEN = (80, 220, 100)
BLUE = (255, 160, 60)
WHITE = (240, 240, 240)
DIM = (100, 100, 100)


def _draw_arrow(
    img: np.ndarray,
    tip: tuple[int, int],
    base: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 2,
) -> None:
    cv2.arrowedLine(img, base, tip, color, thickness, tipLength=0.28)


def _draw_ring(
    img: np.ndarray,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    axis: str,
) -> None:
    if axis == "z":
        cv2.ellipse(img, center, (radius, radius), 0, 0, 360, color, 2)
    elif axis == "y":
        cv2.ellipse(img, center, (radius, radius // 3), 0, 0, 360, color, 2)
    else:
        cv2.ellipse(img, center, (radius // 3, radius), 0, 0, 360, color, 2)


def draw_gizmo(frame_bgr: np.ndarray, snap: TransformSnapshot) -> None:
    if not snap.show_gizmo:
        return

    h, w = frame_bgr.shape[:2]
    cx, cy = w - 118, h - 118
    arm = 44

    cv2.circle(frame_bgr, (cx, cy), 4, WHITE, -1, cv2.LINE_AA)

    if snap.mode == ControlMode.MOVE:
        _draw_arrow(frame_bgr, (cx + arm, cy), (cx, cy), RED)
        _draw_arrow(frame_bgr, (cx, cy - arm), (cx, cy), GREEN)
        _draw_arrow(frame_bgr, (cx, cy + arm // 2), (cx, cy), BLUE, 1)
        cv2.putText(
            frame_bgr, "MOVE", (cx - 52, cy - arm - 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA,
        )
    elif snap.mode == ControlMode.ROTATE:
        _draw_ring(frame_bgr, (cx, cy), arm, RED, "x")
        _draw_ring(frame_bgr, (cx, cy), arm - 6, GREEN, "y")
        _draw_ring(frame_bgr, (cx, cy), arm - 12, BLUE, "z")
        cv2.putText(
            frame_bgr, "ROTATE", (cx - 58, cy - arm - 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA,
        )
    else:
        for color, dx, dy in ((RED, arm, 0), (GREEN, 0, -arm), (BLUE, 0, arm // 2)):
            ex, ey = cx + dx, cy + dy
            cv2.line(frame_bgr, (cx, cy), (ex, ey), color, 2, cv2.LINE_AA)
            cv2.rectangle(
                frame_bgr, (ex - 5, ey - 5), (ex + 5, ey + 5), color, -1, cv2.LINE_AA
            )
        cv2.putText(
            frame_bgr, "SCALE", (cx - 54, cy - arm - 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA,
        )

    if snap.locked:
        cv2.putText(
            frame_bgr, "LOCKED", (cx - 38, cy + arm + 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, DIM, 1, cv2.LINE_AA,
        )
