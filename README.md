<div align="center">

<!-- Replace hero.png with your 16:9 banner -->
<img src="hero.png" width="100%" alt="cam3" />

# cam3

**3D on your webcam. Out through OBS Virtual Camera.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-555?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

Load a `.glb`, drag it where you want on a simple screen pad, tune depth and rotation with sliders. Meet and Zoom see it on **OBS Virtual Camera**. No browser extension, no game engine open in the background.

The feed stays clean. No gizmo drawn on the video itself.

---

## What you need

- Windows 10/11, Python 3.10+, a webcam
- [OBS Studio](https://obsproject.com/) 28+ (virtual camera)

**OBS once:** install OBS, **Start Virtual Camera**, **Stop Virtual Camera**, close OBS. In Meet or Zoom, pick **OBS Virtual Camera**.

If OBS mirrors your camera, the screen pad mirrors too so drag-left still means left on the feed.

---

## Install

```bash
git clone https://github.com/aadi-joshi/cam3.git
cd cam3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Icon sits in the tray. Left-click opens transform controls.

---

## Tray

| Action | What it does |
|--------|----------------|
| **Transform controls** | Move / rotate / scale panel |
| **Wireframe cube** | Default cyan box (startup) |
| **Load model** | Pick `.glb` / `.gltf` from `models/` or project root |
| **None** | Webcam only |
| **Lock model** | Freeze transform |
| **Reset position** | Back to center |
| **Exit** | Quit |

Add files under [`models/`](models/), then **Load model → Refresh list**.

---

## Transform panel

| Tab | Controls |
|-----|----------|
| **Move** | Screen pad (dot = position). Depth slider = near/far, same as Z toward the camera. |
| **Rotate** | Tilt X, Turn Y, Roll Z bars |
| **Scale** | Size bar |

---

## Layout

```
cam3/
├── main.py              tray + entry
├── camera_streamer.py   webcam loop, virtual cam
├── renderer.py          pyrender overlay
├── controls_window.py   transform UI
├── screen_pad.py
├── drag_controls.py
├── models/              drop .glb here
└── requirements.txt
```

Stack: OpenCV capture, [pyrender](https://github.com/mmatl/pyrender) off-screen render, [pyvirtualcam](https://github.com/letmaik/pyvirtualcam) out, [pystray](https://github.com/moses-palmer/pystray) for the tray.

---

## License

[MIT](LICENSE) © Aadi Joshi
