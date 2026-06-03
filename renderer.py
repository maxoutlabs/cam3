"""Headless off-screen 3D rendering and alpha compositing over the camera feed."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyrender
import trimesh
from pyrender.constants import RenderFlags


def _quat_to_matrix(quat_xyzw: np.ndarray) -> np.ndarray:
    x, y, z, w = quat_xyzw
    mat = np.eye(4, dtype=np.float64)
    mat[:3, :3] = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
    return mat


def _model_matrix(position: np.ndarray, rotation_quat: np.ndarray, scale: float) -> np.ndarray:
    m = _quat_to_matrix(rotation_quat)
    m[:3, 3] = position
    m[:3, :3] *= float(scale)
    return m


def _load_mesh_file(path: str | Path) -> trimesh.Trimesh:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Model not found: {path}")

    loaded = trimesh.load(str(p), force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"No mesh geometry in {path}")
        loaded = trimesh.util.concatenate(meshes)
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError(f"Unsupported model type: {path}")

    loaded.apply_translation(-loaded.centroid)
    extent = float(np.max(loaded.extents))
    if extent > 1e-6:
        loaded.apply_scale(1.0 / extent)
    return loaded


class Renderer:
    """Renders an optional mesh with pyrender and composites over BGR frames."""

    _YFOV = np.pi / 4.0
    _CAM_Z = 0.01

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._model_path: Path | None = None
        self._node: pyrender.Node | None = None

        self._scene = pyrender.Scene(
            bg_color=[0.0, 0.0, 0.0, 0.0],
            ambient_light=[0.55, 0.55, 0.55],
        )

        self._aspect = width / height
        cam = pyrender.PerspectiveCamera(yfov=self._YFOV, aspectRatio=self._aspect)
        cam_pose = np.eye(4)
        cam_pose[2, 3] = self._CAM_Z
        self._cam_node = self._scene.add(cam, pose=cam_pose)

        light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.8)
        light_pose = np.eye(4)
        light_pose[:3, 3] = [1.0, 2.0, 2.5]
        self._scene.add(light, pose=light_pose)

        self._renderer = pyrender.OffscreenRenderer(width, height)

    @property
    def has_model(self) -> bool:
        return self._node is not None

    @property
    def model_path(self) -> Path | None:
        return self._model_path

    def clear_model(self) -> None:
        if self._node is not None:
            self._scene.remove_node(self._node)
            self._node = None
        self._model_path = None

    def set_model(self, path: str | Path) -> None:
        """Replace any current model with the file at path."""
        self.clear_model()
        mesh = _load_mesh_file(path)
        pr_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=True)
        self._node = pyrender.Node(mesh=pr_mesh, matrix=np.eye(4))
        self._scene.add_node(self._node)
        self._model_path = Path(path).resolve()

    def project_model_center(
        self,
        position: np.ndarray,
        rotation_quat: np.ndarray,
        scale: float,
    ) -> tuple[float, float] | None:
        """Project model origin to pixel coords (x right, y down)."""
        world = _model_matrix(position, rotation_quat, scale)[:3, 3]
        cam_pose = np.eye(4)
        cam_pose[2, 3] = self._CAM_Z
        cam_from_world = np.linalg.inv(cam_pose)
        p = cam_from_world @ np.append(world, 1.0)
        p = p[:3]
        depth = -p[2]
        if depth < 0.05:
            return None

        tan_half = np.tan(self._YFOV * 0.5)
        x_ndc = p[0] / depth / (tan_half * self._aspect)
        y_ndc = p[1] / depth / tan_half
        u = (x_ndc * 0.5 + 0.5) * self.width
        v = (1.0 - (y_ndc * 0.5 + 0.5)) * self.height
        return float(u), float(v)

    def resize(self, width: int, height: int) -> None:
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self._aspect = width / height
        self._renderer.delete()
        self._renderer = pyrender.OffscreenRenderer(width, height)
        cam = pyrender.PerspectiveCamera(yfov=self._YFOV, aspectRatio=self._aspect)
        self._scene.remove_node(self._cam_node)
        cam_pose = np.eye(4)
        cam_pose[2, 3] = self._CAM_Z
        self._cam_node = self._scene.add(cam, pose=cam_pose)

    def render_overlay(
        self,
        frame_bgr: np.ndarray,
        position: np.ndarray,
        rotation_quat: np.ndarray,
        scale: float,
    ) -> np.ndarray:
        if not self.has_model:
            return frame_bgr

        model = _model_matrix(position, rotation_quat, scale)
        self._scene.set_pose(self._node, model)

        color_rgba, _depth = self._renderer.render(
            self._scene, flags=RenderFlags.RGBA
        )

        alpha = color_rgba[:, :, 3:4].astype(np.float32) / 255.0
        rgb = color_rgba[:, :, :3].astype(np.float32)

        bg = frame_bgr.astype(np.float32)
        comp_bgr = bg * (1.0 - alpha) + rgb[:, :, ::-1] * alpha
        return np.clip(comp_bgr, 0, 255).astype(np.uint8)

    def close(self) -> None:
        self.clear_model()
        self._renderer.delete()
