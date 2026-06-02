"""
3D overlay on webcam -> virtual camera.
Tray: pick a model, transform controls, lock/reset.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from camera_streamer import CameraStreamer
from controls_window import ControlsWindow
from model_catalog import discover_models, ensure_models_folder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cam3")


def _make_tray_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (24, 28, 36, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 8, size - 8, size - 8), radius=10, fill=(60, 140, 220, 255))
    draw.line((18, 44, 46, 44), fill=(230, 90, 90, 255), width=3)
    draw.line((32, 18, 32, 46), fill=(90, 220, 120, 255), width=3)
    draw.line((40, 36, 48, 44), fill=(90, 160, 240, 255), width=3)
    return img


class TrayApp:
    def __init__(self, streamer: CameraStreamer) -> None:
        self._streamer = streamer
        self._icon: Icon | None = None
        self._controls = ControlsWindow(streamer.model)
        ensure_models_folder()

    def _open_controls(self, _icon: Icon | None = None, _item=None) -> None:
        self._controls.open()

    def _on_exit(self, _icon: Icon, _item) -> None:
        self._controls.close()
        self._streamer.stop()
        if self._icon:
            self._icon.stop()

    def _on_toggle_lock(self, _icon: Icon, _item) -> None:
        self._streamer.toggle_lock()
        if self._icon:
            self._icon.update_menu()

    def _lock_checked(self, _item) -> bool:
        return self._streamer.is_locked()

    def _on_reset(self, _icon: Icon, _item) -> None:
        self._streamer.reset_model()

    def _on_clear_model(self, icon: Icon, _item) -> None:
        self._streamer.clear_model()
        icon.menu = self._build_menu()
        icon.update_menu()

    def _on_load_model(self, icon: Icon, _item, path: Path) -> None:
        try:
            self._streamer.load_model(path)
        except Exception:
            return
        icon.menu = self._build_menu()
        icon.update_menu()

    def _make_load_handler(self, path: Path):
        def handler(icon: Icon, _item) -> None:
            self._on_load_model(icon, _item, path)

        return handler

    def _none_checked(self, _item) -> bool:
        return self._streamer.current_model is None

    def _model_checked(self, path: Path):
        def checked(_item) -> bool:
            cur = self._streamer.current_model
            return cur is not None and cur.resolve() == path.resolve()

        return checked

    def _refresh_menu(self, icon: Icon, _item) -> None:
        icon.menu = self._build_menu()
        icon.update_menu()

    def _build_model_submenu(self) -> Menu:
        items: list[MenuItem] = [
            MenuItem(
                "None (camera only)",
                self._on_clear_model,
                checked=self._none_checked,
            ),
        ]
        for label, path in discover_models():
            items.append(
                MenuItem(
                    label,
                    self._make_load_handler(path),
                    checked=self._model_checked(path),
                )
            )
        items.append(Menu.SEPARATOR)
        items.append(MenuItem("Refresh list", self._refresh_menu))
        return Menu(*items)

    def _build_menu(self) -> Menu:
        return Menu(
            MenuItem("Transform controls", self._open_controls, default=True),
            MenuItem("Load model", self._build_model_submenu()),
            MenuItem(
                "Lock model",
                self._on_toggle_lock,
                checked=self._lock_checked,
            ),
            MenuItem("Reset position", self._on_reset),
            Menu.SEPARATOR,
            MenuItem("Exit", self._on_exit),
        )

    def run(self) -> None:
        self._icon = Icon(
            "cam3",
            _make_tray_icon(),
            "Cam3 — load a model from the tray menu",
            menu=self._build_menu(),
        )
        self._streamer.start()
        self._icon.run()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="3D virtual webcam with tray controls")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional: load this .glb at startup (otherwise pick from tray)",
    )
    p.add_argument("--vcam-backend", type=str, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    streamer = CameraStreamer(
        camera_index=args.camera,
        width=args.width,
        height=args.height,
        fps=args.fps,
        model_path=args.model,
        virtual_camera=args.vcam_backend,
    )
    app = TrayApp(streamer)
    try:
        app.run()
    except KeyboardInterrupt:
        streamer.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
