"""Headless off-screen 3D rendering and alpha compositing over the camera feed."""

from __future__ import annotations

from pathlib import Path

import platform_support

platform_support.configure_opengl_environment()

import cv2
import numpy as np
import pyrender
import trimesh
from pyrender.constants import RenderFlags

# Off-screen render scale (lower = faster)
_RENDER_SCALE = 0.48

_BOX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


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
    s = float(scale)
    r = _quat_to_matrix(rotation_quat)
    t = np.eye(4, dtype=np.float64)
    t[:3, :3] = r[:3, :3] * s
    t[:3, 3] = position
    return t


def _wireframe_box(size: float = 0.65, edge_radius: float = 0.012) -> trimesh.Trimesh:
    h = size * 0.5
    corners = np.array(
        [
            [-h, -h, -h], [h, -h, -h], [h, h, -h], [-h, h, -h],
            [-h, -h, h], [h, -h, h], [h, h, h], [-h, h, h],
        ],
        dtype=np.float64,
    )
    parts: list[trimesh.Trimesh] = []
    for i, j in _BOX_EDGES:
        p0, p1 = corners[i], corners[j]
        seg = p1 - p0
        length = float(np.linalg.norm(seg))
        if length < 1e-8:
            continue
        cyl = trimesh.creation.cylinder(radius=edge_radius, height=length, sections=5)
        direction = seg / length
        tf = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], direction)
        cyl.apply_transform(tf)
        cyl.apply_translation((p0 + p1) * 0.5)
        parts.append(cyl)
    return trimesh.util.concatenate(parts)


def _prepare_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Center and uniform-scale to unit size. Proportions stay intact."""
    mesh = mesh.copy()
    mesh.apply_translation(-mesh.centroid)
    extent = float(np.max(mesh.extents))
    if extent > 1e-6:
        mesh.apply_scale(1.0 / extent)
    if mesh.vertex_normals is None or len(mesh.vertex_normals) != len(mesh.vertices):
        mesh.fix_normals()
    return mesh


def _load_mesh_file(path: str | Path) -> trimesh.Trimesh:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Model not found: {path}")

    try:
        loaded = trimesh.load(str(p), force="scene")
    except Exception:
        loaded = trimesh.load(str(p))

    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.to_geometry()
        if mesh is None or not isinstance(mesh, trimesh.Trimesh):
            raise ValueError(f"No mesh in {path}")
        return _prepare_mesh(mesh)

    if isinstance(loaded, trimesh.Trimesh):
        return _prepare_mesh(loaded)

    raise ValueError(f"Unsupported file: {path}")


class Renderer:
    """Renders mesh with pyrender; caches overlay when transform is unchanged."""

    _YFOV = np.pi / 4.0
    _CAM_Z = 0.01

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._model_path: Path | None = None
        self._is_cube = False
        self._nodes: list[pyrender.Node] = []

        self._scene = pyrender.Scene(
            bg_color=[0.0, 0.0, 0.0, 0.0],
            ambient_light=[0.6, 0.6, 0.6],
        )

        self._aspect = width / height
        self._add_camera()
        light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.5)
        lp = np.eye(4)
        lp[:3, 3] = [1.0, 2.0, 2.5]
        self._scene.add(light, pose=lp)

        rw = max(64, int(width * _RENDER_SCALE))
        rh = max(64, int(height * _RENDER_SCALE))
        self._render_w = rw
        self._render_h = rh
        self._renderer = self._create_offscreen_renderer(rw, rh)

        self._cache_key: tuple | None = None
        self._cache_bgr: np.ndarray | None = None
        self._cache_alpha: np.ndarray | None = None

    @staticmethod
    def _create_offscreen_renderer(width: int, height: int) -> pyrender.OffscreenRenderer:
        try:
            return pyrender.OffscreenRenderer(width, height)
        except Exception as exc:
            hint = platform_support.platform_info().opengl_hint
            raise RuntimeError(
                f"Could not create OpenGL renderer ({exc}). {hint}"
            ) from exc

    def _add_camera(self) -> None:
        cam = pyrender.PerspectiveCamera(yfov=self._YFOV, aspectRatio=self._aspect)
        cam_pose = np.eye(4)
        cam_pose[2, 3] = self._CAM_Z
        if hasattr(self, "_cam_node"):
            self._scene.remove_node(self._cam_node)
        self._cam_node = self._scene.add(cam, pose=cam_pose)

    def _clear_nodes(self) -> None:
        for node in self._nodes:
            self._scene.remove_node(node)
        self._nodes.clear()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        self._cache_key = None
        self._cache_bgr = None
        self._cache_alpha = None

    @property
    def has_model(self) -> bool:
        return len(self._nodes) > 0

    @property
    def model_path(self) -> Path | None:
        return self._model_path

    def load_default_cube(self) -> None:
        self._clear_nodes()
        mesh = _wireframe_box()
        pr = pyrender.Mesh.from_trimesh(
            mesh,
            smooth=False,
            material=pyrender.MetallicRoughnessMaterial(
                baseColorFactor=[0.35, 0.92, 1.0, 1.0],
                metallicFactor=0.05,
                roughnessFactor=0.4,
            ),
        )
        node = pyrender.Node(mesh=pr, matrix=np.eye(4))
        self._scene.add_node(node)
        self._nodes.append(node)
        self._model_path = None
        self._is_cube = True
        self._invalidate_cache()

    def clear_model(self) -> None:
        self._clear_nodes()
        self._model_path = None
        self._is_cube = False

    def set_model(self, path: str | Path) -> None:
        self._clear_nodes()
        mesh = _load_mesh_file(path)
        pr = pyrender.Mesh.from_trimesh(mesh, smooth=not mesh.is_watertight)
        node = pyrender.Node(mesh=pr, matrix=np.eye(4))
        self._scene.add_node(node)
        self._nodes.append(node)
        self._model_path = Path(path).resolve()
        self._is_cube = False
        self._invalidate_cache()

    def resize(self, width: int, height: int) -> None:
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self._aspect = width / height
        self._render_w = max(64, int(width * _RENDER_SCALE))
        self._render_h = max(64, int(height * _RENDER_SCALE))
        self._renderer.delete()
        self._renderer = self._create_offscreen_renderer(self._render_w, self._render_h)
        self._add_camera()
        self._invalidate_cache()

    def _render_layer(
        self,
        position: np.ndarray,
        rotation_quat: np.ndarray,
        scale: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        pose = _model_matrix(position, rotation_quat, scale)
        for node in self._nodes:
            self._scene.set_pose(node, pose)

        color_rgba, _ = self._renderer.render(self._scene, flags=RenderFlags.RGBA)
        rgb = cv2.resize(
            color_rgba[:, :, :3], (self.width, self.height), interpolation=cv2.INTER_LINEAR
        )
        alpha = cv2.resize(
            color_rgba[:, :, 3], (self.width, self.height), interpolation=cv2.INTER_LINEAR
        )
        bgr = rgb[:, :, ::-1].astype(np.float32)
        a = (alpha.astype(np.float32) / 255.0)[:, :, np.newaxis]
        return bgr, a

    def render_overlay(
        self,
        frame_bgr: np.ndarray,
        position: np.ndarray,
        rotation_quat: np.ndarray,
        scale: float,
        generation: int,
    ) -> np.ndarray:
        if not self.has_model:
            return frame_bgr

        key = (
            generation,
            self.width,
            self.height,
            round(float(position[0]), 4),
            round(float(position[1]), 4),
            round(float(position[2]), 4),
            round(float(rotation_quat[0]), 4),
            round(float(rotation_quat[1]), 4),
            round(float(rotation_quat[2]), 4),
            round(float(rotation_quat[3]), 4),
            round(float(scale), 4),
            str(self._model_path),
        )
        if key != self._cache_key:
            self._cache_bgr, self._cache_alpha = self._render_layer(
                position, rotation_quat, scale
            )
            self._cache_key = key

        a = self._cache_alpha
        bgr = self._cache_bgr
        # In-place blend when frame is writable (avoids extra full-frame alloc).
        if frame_bgr.flags.writeable:
            out = frame_bgr
            out[:] = np.clip(
                out.astype(np.float32) * (1.0 - a) + bgr * a, 0, 255
            ).astype(np.uint8)
            return out
        bg = frame_bgr.astype(np.float32)
        return np.clip(bg * (1.0 - a) + bgr * a, 0, 255).astype(np.uint8)

    def close(self) -> None:
        self._clear_nodes()
        self._renderer.delete()
