"""OS-specific webcam, virtual camera, and OpenGL setup."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class OS(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    OTHER = "other"


@dataclass(frozen=True)
class PlatformInfo:
    os: OS
    name: str
    virtual_camera_hint: str
    opengl_hint: str


def current_os() -> OS:
    if sys.platform == "win32":
        return OS.WINDOWS
    if sys.platform == "darwin":
        return OS.MACOS
    if sys.platform.startswith("linux"):
        return OS.LINUX
    return OS.OTHER


def platform_info() -> PlatformInfo:
    os_kind = current_os()
    if os_kind == OS.WINDOWS:
        return PlatformInfo(
            os=os_kind,
            name="Windows",
            virtual_camera_hint=(
                "Install OBS Studio 28+. Run Start Virtual Camera once, then stop it."
            ),
            opengl_hint="Uses the default OpenGL backend.",
        )
    if os_kind == OS.MACOS:
        return PlatformInfo(
            os=os_kind,
            name="macOS",
            virtual_camera_hint=(
                "Install OBS 28+ (30+ on macOS 13+). Start Virtual Camera once, "
                "then stop it, then quit OBS."
            ),
            opengl_hint="Uses the default OpenGL backend.",
        )
    if os_kind == OS.LINUX:
        return PlatformInfo(
            os=os_kind,
            name="Linux",
            virtual_camera_hint=(
                "Install v4l2loopback (e.g. sudo apt install v4l2loopback-dkms), then: "
                "sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=cam3"
            ),
            opengl_hint=(
                "Headless: export CAM3_GL=egl (GPU) or CAM3_GL=osmesa (CPU). "
                "Desktop with DISPLAY can omit CAM3_GL."
            ),
        )
    return PlatformInfo(
        os=os_kind,
        name=sys.platform,
        virtual_camera_hint="See pyvirtualcam docs for your OS.",
        opengl_hint="Set CAM3_GL if offscreen rendering fails.",
    )


def configure_opengl_environment() -> None:
    """Must run before importing pyrender or PyOpenGL."""
    if os.environ.get("PYOPENGL_PLATFORM"):
        return

    forced = os.environ.get("CAM3_GL", "").strip().lower()
    if forced in ("egl", "osmesa"):
        os.environ["PYOPENGL_PLATFORM"] = forced
        return

    if current_os() == OS.LINUX and not os.environ.get("DISPLAY"):
        os.environ["PYOPENGL_PLATFORM"] = "egl"


def create_video_capture(camera_index: int):
    """OpenCV capture with the best API for this OS."""
    import cv2

    api = 0
    if current_os() == OS.WINDOWS:
        api = cv2.CAP_DSHOW
    elif current_os() == OS.MACOS:
        api = cv2.CAP_AVFOUNDATION
    elif current_os() == OS.LINUX:
        api = cv2.CAP_V4L2

    cap = cv2.VideoCapture(camera_index, api) if api else cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(camera_index)
    return cap


def list_webcam_indices(max_probe: int = 5) -> list[int]:
    """Return indices that open and return at least one frame."""
    import cv2

    found: list[int] = []
    for index in range(max_probe):
        cap = create_video_capture(index)
        try:
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if ok and frame is not None:
                found.append(index)
        finally:
            cap.release()
    return found


def linux_v4l2_loopback_devices() -> list[str]:
    """Device paths for v4l2loopback virtual cameras."""
    devices: list[str] = []
    sysfs = Path("/sys/class/video4linux")
    if not sysfs.is_dir():
        return devices

    for entry in sorted(sysfs.iterdir()):
        if not entry.name.startswith("video"):
            continue
        name_file = entry / "name"
        dev = f"/dev/{entry.name}"
        if not name_file.is_file():
            continue
        try:
            label = name_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        except OSError:
            continue
        if "loopback" in label or label == "cam3":
            devices.append(dev)

    return devices


def resolve_virtual_camera_device(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if current_os() == OS.LINUX:
        loopbacks = linux_v4l2_loopback_devices()
        if loopbacks:
            return loopbacks[0]
    return None


def build_virtual_camera_kwargs(
    width: int,
    height: int,
    fps: int,
    *,
    backend: str | None = None,
    device: str | None = None,
) -> dict:
    """Keyword args for pyvirtualcam.Camera."""
    from pyvirtualcam import PixelFormat

    kwargs: dict = {
        "width": width,
        "height": height,
        "fps": fps,
        "fmt": PixelFormat.RGB,
    }

    os_kind = current_os()
    if backend:
        kwargs["backend"] = backend
    elif os_kind in (OS.WINDOWS, OS.MACOS):
        kwargs["backend"] = "obs"

    resolved = resolve_virtual_camera_device(device)
    if resolved:
        kwargs["device"] = resolved

    return kwargs


def default_screen_mirror() -> bool:
    """Screen pad mirrors X so drag-left matches the meeting feed."""
    return os.environ.get("CAM3_MIRROR", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def check_environment() -> list[str]:
    """Fatal setup problems (empty list = OK to try starting)."""
    issues: list[str] = []
    info = platform_info()

    if info.os == OS.OTHER:
        issues.append(f"Unsupported platform: {sys.platform}")
        return issues

    if info.os == OS.LINUX:
        if not linux_v4l2_loopback_devices():
            issues.append(
                "No v4l2loopback device found. "
                + info.virtual_camera_hint
            )

    return issues


def format_startup_help() -> str:
    info = platform_info()
    lines = [
        f"Platform: {info.name}",
        f"Virtual camera: {info.virtual_camera_hint}",
        f"OpenGL: {info.opengl_hint}",
    ]
    if info.os == OS.LINUX:
        devs = linux_v4l2_loopback_devices()
        if devs:
            lines.append(f"Loopback device(s): {', '.join(devs)}")
    return "\n".join(lines)
