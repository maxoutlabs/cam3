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

---

## Run it (30 seconds)

```bash
git clone https://github.com/aadi-joshi/cam3.git
cd cam3
```

| OS | Command |
|----|---------|
| **Windows** | Double-click `run.bat` or `.\run.bat` in PowerShell |
| **macOS / Linux** | `chmod +x run.sh && ./run.sh` |

First run creates `.venv` and installs deps. Tray icon appears. **Left-click** for transform controls.

**Before that (once per machine):**

| OS | Virtual camera |
|----|----------------|
| Windows / macOS | Install [OBS](https://obsproject.com/). Start **Virtual Camera**, stop, quit OBS. |
| Linux | `./scripts/setup-linux-vcam.sh` |

In Meet or Zoom, select the **virtual** camera (OBS Virtual Camera or the `cam3` loopback device), not your normal webcam.

---

## What it does

Webcam → OpenCV → pyrender (`.glb` overlay) → pyvirtualcam → virtual cam.

Drop models in `models/`. Tray → **Load model → Refresh list**.

```bash
# manual run (same as run.sh / run.bat)
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --check
python main.py
```

**Flags:** `--list-cameras` `--camera 1` `--model path/to/file.glb` `--vcam-device /dev/video10` (Linux)

Linux headless 3D: `export CAM3_GL=egl` or `CAM3_GL=osmesa`

`CAM3_MIRROR=0` if the screen pad feels flipped.

---

## Tray

| | |
|--|--|
| Transform controls | Move / rotate / scale panel |
| Load model | `.glb` in `models/` |
| Wireframe cube | Default on startup |
| None | Webcam only |
| Lock / Reset / Exit | |

---

## Demo Video
https://github.com/user-attachments/assets/ed5ec5f0-992d-4e70-b9b9-8d303d619f63

###### _Demo model: V1 from ULTRAKILL on Sketchfab (CC BY). Character by Hakita / New Blood Interactive. Not included in the repo.<br>https://sketchfab.com/3d-models/v1-ultrakill-d951a08a8f50412d84e262bad887b285_
---

## License

[MIT](LICENSE) © [Aadi Joshi](https://github.com/aadi-joshi)
