"""Webcam capture, 3D overlay, and virtual camera output."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import cv2
import pyvirtualcam

import platform_support
from model_state import ModelState
from renderer import Renderer

logger = logging.getLogger(__name__)

_JOIN_TIMEOUT_S = 4.0


class CameraStreamer:
    """Reads the physical webcam, composites 3D overlay, streams to virtual cam."""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        model_path: str | Path | None = None,
        virtual_camera: str | None = None,
        vcam_device: str | None = None,
        start_with_cube: bool = True,
    ) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.virtual_camera = virtual_camera
        self.vcam_device = vcam_device
        self.start_with_cube = start_with_cube
        self.model = ModelState()

        self._current_model: Path | None = None
        self._startup_model = Path(model_path).resolve() if model_path else None

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._renderer: Renderer | None = None
        self._cap: cv2.VideoCapture | None = None
        self._vcam: pyvirtualcam.Camera | None = None
        self._lock = threading.Lock()
        self._shutting_down = False

    @property
    def current_model(self) -> Path | None:
        return self._current_model

    @property
    def has_overlay(self) -> bool:
        if self._shutting_down:
            return False
        with self._lock:
            return self._renderer is not None and self._renderer.has_model

    @property
    def is_cube_mode(self) -> bool:
        if self._shutting_down:
            return False
        with self._lock:
            return (
                self._renderer is not None
                and self._renderer.has_model
                and self._renderer._is_cube
            )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._shutting_down = False
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="CameraStreamer", daemon=False
        )
        self._thread.start()

    def _release_capture(self) -> None:
        with self._lock:
            cap = self._cap
            self._cap = None
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    def _release_renderer(self) -> None:
        with self._lock:
            renderer = self._renderer
            self._renderer = None
        if renderer is not None:
            try:
                renderer.close()
            except Exception:
                logger.debug("Renderer close failed", exc_info=True)

    def stop(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._stop.set()
        self._release_capture()

        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=_JOIN_TIMEOUT_S)

        if thread and thread.is_alive():
            logger.warning("Camera thread still running; releasing GL resources")
            self._release_renderer()
        else:
            self._release_renderer()

        self._thread = None
        self._vcam = None

    def is_locked(self) -> bool:
        return self.model.locked

    def toggle_lock(self) -> bool:
        return self.model.toggle_locked()

    def reset_model(self) -> None:
        self.model.reset()

    def load_model(self, path: str | Path) -> None:
        path = Path(path).resolve()
        with self._lock:
            if self._renderer is None:
                self._current_model = path
                return
            self._renderer.set_model(path)
            self._current_model = path
            self.model.reset()
            logger.info("Loaded model: %s", path.name)

    def load_default_cube(self) -> None:
        with self._lock:
            if self._renderer:
                self._renderer.load_default_cube()
            self._current_model = None
            self.model.reset()
            logger.info("Showing default wireframe cube")

    def clear_model(self) -> None:
        with self._lock:
            if self._renderer:
                self._renderer.clear_model()
            self._current_model = None
            self.model.reset()
            logger.info("Model cleared (camera only)")

    def _open_capture(self) -> cv2.VideoCapture:
        cap = platform_support.create_video_capture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        if platform_support.current_os() == platform_support.OS.WINDOWS:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(
                f"Could not open webcam index {self.camera_index}. "
                "Try --list-cameras or another --camera index."
            )
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.width = actual_w if actual_w > 0 else self.width
        self.height = actual_h if actual_h > 0 else self.height
        return cap

    def _open_virtual_camera(self) -> pyvirtualcam.Camera:
        kwargs = platform_support.build_virtual_camera_kwargs(
            self.width,
            self.height,
            self.fps,
            backend=self.virtual_camera,
            device=self.vcam_device,
        )
        try:
            return pyvirtualcam.Camera(**kwargs)
        except Exception as exc:
            hint = platform_support.platform_info().virtual_camera_hint
            raise RuntimeError(
                f"Could not open virtual camera: {exc}\n{hint}"
            ) from exc

    def _run(self) -> None:
        try:
            if self._stop.is_set():
                return
            self._cap = self._open_capture()
            with self._lock:
                self._renderer = Renderer(self.width, self.height)
                if self._startup_model and self._startup_model.is_file():
                    try:
                        self._renderer.set_model(self._startup_model)
                        self._current_model = self._startup_model
                    except Exception:
                        logger.exception("Startup model failed, using cube")
                        self._renderer.load_default_cube()
                elif self.start_with_cube:
                    self._renderer.load_default_cube()

            with self._open_virtual_camera() as cam:
                self._vcam = cam
                logger.info(
                    "Virtual camera: %s (%sx%s @ %sfps)",
                    cam.device,
                    cam.width,
                    cam.height,
                    cam.fps,
                )

                last_t = time.perf_counter()

                while not self._stop.is_set():
                    with self._lock:
                        cap = self._cap
                    if cap is None:
                        break
                    ok, frame = cap.read()
                    if self._stop.is_set():
                        break
                    if not ok or frame is None:
                        time.sleep(0.002 if self._stop.is_set() else 0.005)
                        continue

                    now = time.perf_counter()
                    dt = min(now - last_t, 0.1)
                    last_t = now
                    self.model.tick(dt)

                    gen = self.model.generation
                    snap = self.model.snapshot()
                    with self._lock:
                        renderer = self._renderer
                        if renderer is None or self._stop.is_set():
                            break

                        fh, fw = frame.shape[:2]
                        if fw != renderer.width or fh != renderer.height:
                            renderer.resize(fw, fh)

                        composed = renderer.render_overlay(
                            frame,
                            snap.position,
                            snap.rotation,
                            snap.scale,
                            gen,
                        )

                    rgb = cv2.cvtColor(composed, cv2.COLOR_BGR2RGB)
                    cam.send(rgb)
                    cam.sleep_until_next_frame()
        except Exception:
            if not self._stop.is_set():
                logger.exception("Camera stream failed")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        self._release_capture()
        self._release_renderer()
        self._vcam = None
