# cam3

Tray app for Windows: composite a 3D model over your webcam and stream it through **OBS Virtual Camera** (Google Meet, Zoom, etc.).

No hand tracking — pick a model from the tray, then drag it on a **live camera preview** or use a **Blender-style gizmo**.

## Features

- Webcam-only by default; load `.glb` / `.gltf` from the tray
- One active model at a time (switching replaces the previous)
- Screen-aligned move controls (left is left on your feed)
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
| **Load model** | Choose a file from `models/` (or refresh after adding files) |
| **None (camera only)** | Remove the 3D overlay |
| **Transform controls** (left-click icon) | **Camera preview** (drag dot to move) + **Blender-style gizmo** (drag axes) |
| **Lock model** | Freeze transform |
| **Reset position** | Center the model |
| **Exit** | Quit |

Drop models in the [`models/`](models/) folder, then **Load model → Refresh list**.

### Transform panel (left-click tray icon)

| Control | Action |
|---------|--------|
| **Camera preview** | Drag the cyan dot to move the model on your feed |
| **Depth slider** | Move model nearer or farther |
| **G** | Drag red / green / blue arrows on the gizmo |
| **R** | Drag rotation rings |
| **S** | Drag scale handles |
| **Sensitivity** | Fine / Normal / Coarse |

Optional startup load:

```bash
python main.py --model path\to\model.glb
```

## Project layout

```
cam3/
├── main.py              # Entry + tray
├── camera_streamer.py   # Webcam → composite → virtual cam
├── renderer.py          # Off-screen 3D render
├── model_state.py       # Transform state
├── model_catalog.py     # Discover models/
├── controls_window.py   # Transform panel
├── viewport_widget.py   # Draggable camera preview
├── gizmo_widget.py      # Draggable Blender-style gizmo
├── preview_feed.py      # Live preview for the panel
├── gizmo_overlay.py     # On-feed gizmo hint
├── models/              # Your .glb files (not in git)
└── requirements.txt
```

## License

[MIT](LICENSE) © Aadi Joshi
