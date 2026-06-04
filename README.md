<div align="center">

<img src="hero.png" width="100%" alt="cam3" />

# cam3

**GLB on your webcam. Virtual camera out to Meet and Zoom.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/Windows-✓-555?style=flat-square)]()
[![macOS](https://img.shields.io/badge/macOS-✓-555?style=flat-square)]()
[![Linux](https://img.shields.io/badge/Linux-✓-555?style=flat-square)]()
[![MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)

</div>

Tray app. Webcam in, `.glb` composited with [pyrender](https://github.com/mmatl/pyrender), [pyvirtualcam](https://github.com/letmaik/pyvirtualcam) out. **Left-click** the tray icon for move / rotate / scale. No gizmo on the video feed.

---

## Virtual camera

| OS | Setup once |
|----|------------|
| **Windows** | [OBS](https://obsproject.com/) 28+: Start Virtual Camera, stop, close OBS. Pick **OBS Virtual Camera** in Meet. |
| **macOS** | Same (OBS 30+ on macOS 13+). |
| **Linux** | `sudo apt install v4l2loopback-dkms` then `sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=cam3` or run `scripts/setup-linux-vcam.sh`. Pick the loopback device in Meet. |

`CAM3_MIRROR=0` if drag-left on the pad does not match the feed.

---

## Install

```bash
git clone https://github.com/aadi-joshi/cam3.git
cd cam3
python -m venv .venv
```

**Windows:** `.\.venv\Scripts\Activate.ps1`  
**macOS / Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
python main.py --check
python main.py
```

```bash
python main.py --model models/foo.glb
python main.py --list-cameras
python main.py --camera 1
python main.py --vcam-device /dev/video10   # Linux
```

Headless Linux 3D: `export CAM3_GL=egl` or `CAM3_GL=osmesa`.

---

## Tray

| | |
|--|--|
| **Transform controls** | Panel |
| **Load model** | `.glb` / `.gltf` in `models/` (refresh list after adding files) |
| **Wireframe cube** | Default at startup |
| **None** | Webcam only |
| **Lock / Reset** | Freeze or center |
| **Exit** | Quit |

---

## License

[MIT](LICENSE) © [Aadi Joshi](https://github.com/aadi-joshi)
