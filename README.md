<div align="center">

<img src="hero.png" width="100%" alt="cam3 — 3D models on your webcam via a virtual camera" />

# cam3

**Drop a GLB on your webcam. Meet and Zoom see it on a virtual camera.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/Windows-✓-555?style=flat-square)]()
[![macOS](https://img.shields.io/badge/macOS-✓-555?style=flat-square)]()
[![Linux](https://img.shields.io/badge/Linux-✓-555?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

[Install](#install) · [Virtual camera](#virtual-camera-by-os) · [How it works](#how-it-works)

</div>

---

Tray app for **Windows, macOS, and Linux**. Reads your webcam, renders a `.glb` / `.gltf` with [pyrender](https://github.com/mmatl/pyrender), outputs through a **virtual camera**. No browser extension. No Blender running in the background.

The meeting feed stays clean. Nothing is drawn on the video except your model.

---

## How it works

```
Webcam  →  OpenCV  →  pyrender overlay  →  pyvirtualcam  →  virtual cam  →  Meet / Zoom / Teams
```

**Transform panel:** screen pad (drag the dot) plus sliders for depth, rotation, and scale. No second camera preview in the panel.

---

## Virtual camera by OS

| OS | What cam3 uses | One-time setup |
|----|----------------|----------------|
| **Windows** | OBS Virtual Camera | Install [OBS](https://obsproject.com/) 28+. Start Virtual Camera, stop it, close OBS. |
| **macOS** | OBS Virtual Camera | OBS 28+ (OBS 30+ on macOS 13+). Same start/stop once, quit OBS. |
| **Linux** | [v4l2loopback](https://github.com/umlaeute/v4l2loopback) | See below. |

In your meeting app, pick the **virtual** camera (OBS Virtual Camera on Win/Mac, or the loopback device on Linux), not your physical webcam.

If the feed is mirrored, the screen pad mirrors too (`CAM3_MIRROR=0` to disable).

---

## Install

```bash
git clone https://github.com/aadi-joshi/cam3.git
cd cam3
python -m venv .venv
```

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --check
python main.py
```

**macOS / Linux**

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py --check
python main.py
```

Tray icon: **left-click** opens transform controls.

**Useful flags**

```bash
python main.py --list-cameras          # find webcam index
python main.py --camera 1              # non-default webcam
python main.py --model path/to/model.glb
python main.py --vcam-device /dev/video10   # Linux loopback path
python main.py --check                 # OS setup summary
```

---

## Linux setup

```bash
# Debian/Ubuntu helper (modprobe + apt packages)
chmod +x scripts/setup-linux-vcam.sh
./scripts/setup-linux-vcam.sh
```

Or manually:

```bash
sudo apt install v4l2loopback-dkms v4l-utils
sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=cam3
python main.py --check
```

Pick the **cam3** / loopback device in Meet or Zoom.

**OpenGL (3D render):** On a desktop session, defaults usually work. Headless or Wayland issues:

```bash
export CAM3_GL=egl      # GPU offscreen (needs EGL libs)
# or
export CAM3_GL=osmesa   # CPU offscreen (sudo apt install libosmesa6-dev)
```

---

## Tray

| Action | What it does |
|--------|----------------|
| **Transform controls** | Move / rotate / scale panel |
| **Wireframe cube** | Default cyan box at startup |
| **Load model** | `.glb` / `.gltf` from `models/` or repo root |
| **None** | Webcam only |
| **Lock model** | Freeze transform |
| **Reset position** | Center and default rotation/scale |
| **Exit** | Quit |

Add files under [`models/`](models/), then **Load model → Refresh list**.

---

## Transform panel

| Tab | Controls |
|-----|----------|
| **Move** | Screen pad + depth slider |
| **Rotate** | Tilt X, Turn Y, Roll Z |
| **Scale** | Size |

---

## Models

Multi-part GLBs keep scene transforms (no more mashed geometry). Use models you have the right to use.

---

## Layout

```
cam3/
├── main.py
├── platform_support.py   # OS webcam + virtual cam + GL
├── camera_streamer.py
├── renderer.py
├── controls_window.py
├── scripts/setup-linux-vcam.sh
└── models/
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE) © [Aadi Joshi](https://github.com/aadi-joshi)
