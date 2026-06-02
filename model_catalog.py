"""Find .glb / .gltf models shipped with the app."""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
MODELS_DIR = APP_DIR / "models"
SUPPORTED_SUFFIXES = (".glb", ".gltf")


def discover_models() -> list[tuple[str, Path]]:
    """
    Scan `models/` then the app folder for models.
    Returns [(menu_label, absolute_path), ...] sorted by name.
    """
    found: dict[Path, str] = {}

    def add_from_folder(folder: Path) -> None:
        if not folder.is_dir():
            return
        for suffix in SUPPORTED_SUFFIXES:
            for path in folder.glob(f"*{suffix}"):
                if not path.is_file():
                    continue
                key = path.resolve()
                if key not in found:
                    found[key] = path.stem.replace("_", " ")

    add_from_folder(MODELS_DIR)
    add_from_folder(APP_DIR)

    return sorted(
        [(label, path.resolve()) for path, label in found.items()],
        key=lambda item: item[0].lower(),
    )


def ensure_models_folder() -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR
