# Contributing

Thanks for looking at cam3.

## Setup

Same as the README: venv, `pip install -r requirements.txt`, `python main.py`. OBS Virtual Camera must be set up once on Windows.

## Pull requests

- One logical change per PR when you can.
- Match existing style (minimal deps, no extra frameworks).
- Test on Windows with a real webcam and OBS Virtual Camera before opening.

## Issues

Include OS version, Python version, and what you expected vs what happened. For model bugs, say which `.glb` (or a similar public sample) and whether it looks wrong on load or only when rotating.

## Scope

cam3 is intentionally small. Features that add heavy runtimes, always-on network calls, or a full 3D editor belong in other tools, not here.
