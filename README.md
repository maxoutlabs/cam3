# cam3

Tray app for Windows: composite a 3D model over your webcam and stream it through **OBS Virtual Camera** (Google Meet, Zoom, etc.).

Pick a model from the tray, then position it with a **screen pad** and **drag sliders**. Clean output — no debug overlays on the video.

## Features

- Starts with a **wireframe cube**; load `.glb` / `.gltf` from the tray
- **Screen pad** — simple rectangle; drag the dot (not a second camera preview)
- **Drag sliders** for depth, rotation, and scale
- Lightweight OpenGL overlay via [pyrender](https://github.com/mmatl/pyrender)
- System tray UI ([pystray](https://github.com/moses-palmer/pystray))

## Requirements

- Windows 10/11
- Python 3.10+
- Webcam
- [OBS Studio](https://obsproject.com/) 28+ (built-in virtual camera)

### One-time OBS setup

1. Install OBS Studio.
2. Open OBS → **Start Virtual Camera** → **Stop Virtual Camera** → close OBS.
3. In your meeting app, select **OBS Virtual Camera**.

If your OBS scene flips the camera horizontally, the screen pad uses the same flip so **drag left = model moves left** on your feed.

## Install

```bash
git clone https://github.com/aadi-joshi/cam3.git
cd cam3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Usage

| Tray action | Effect |
|-------------|--------|
| **Wireframe cube** | Default cyan wireframe box |
| **Load model** | Choose a `.glb` from `models/` (refresh list after adding files) |
| **None (camera only)** | Webcam only, no 3D overlay |
| **Transform controls** (left-click icon) | Open the control panel |
| **Lock model** | Freeze transform |
| **Reset position** | Center the model |
| **Exit** | Quit |

Drop models in the [`models/`](models/) folder, then **Load model → Refresh list**.

### Transform panel

| Tab | Controls |
|-----|----------|
| **Move** | **Screen pad** — drag the dot for left/right and up/down. **Depth slider** — near ↔ far (this is the same as moving toward/away from the camera; there is no separate Z gizmo). |
| **Rotate** | Drag **Tilt X / Turn Y / Roll Z** bars |
| **Scale** | Drag the **Size** bar |

**Sensitivity:** Fine / Normal / Coarse

## Project layout

```
cam3/
├── main.py
├── camera_streamer.py
├── renderer.py
├── model_state.py
├── model_catalog.py
├── controls_window.py
├── screen_pad.py
├── drag_controls.py
├── models/
└── requirements.txt
```

## License

[MIT](LICENSE) © Aadi Joshi
