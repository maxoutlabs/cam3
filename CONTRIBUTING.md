# Contributing

Thanks for looking at cam3.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --check
python main.py
```

Virtual camera must work on your OS before testing (OBS on Windows/macOS, v4l2loopback on Linux).

## Pull requests

- One logical change per PR when you can.
- Test on the OS you changed (webcam + virtual cam + load a small `.glb`).
- Keep dependencies minimal.

## Issues

Include OS, Python version, output of `python main.py --check`, and whether the bug is on load or when moving the model.

## Scope

Small tray tool. No full editor, cloud accounts, or heavy ML stacks in core.
