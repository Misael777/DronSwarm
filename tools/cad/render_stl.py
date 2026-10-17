#!/usr/bin/env python3
"""Renderiza un STL a PNG con matplotlib (sin OpenGL), para informes.

    python tools/cad/render_stl.py cad/exports/motor_mount.stl docs/evidencias/s01/motor_mount.png
"""

import argparse
import struct
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402


def load_stl(path: Path) -> np.ndarray:
    """Devuelve un arreglo (n, 3, 3) con los triángulos; acepta STL ASCII o binario."""
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        verts = [list(map(float, line.split()[1:4])) for line in data.decode().splitlines() if line.strip().startswith("vertex")]
        return np.array(verts).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return rec["v"].reshape(-1, 3, 3).astype(float)


def render(stl: Path, png: Path, elev: float, azim: float, title: str | None):
    tris = load_stl(stl)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    light = np.array([0.4, -0.5, 0.8])
    shade = 0.35 + 0.65 * np.clip(normals @ (light / np.linalg.norm(light)), 0, 1)
    base = np.array([0.17, 0.32, 0.51])
    colors = np.clip(base[None, :] * shade[:, None] + 0.15 * shade[:, None], 0, 1)

    fig = plt.figure(figsize=(8, 6), dpi=150)
    ax = fig.add_subplot(projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo)
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")
    ax.set_zlabel("Z [mm]")
    if title:
        ax.set_title(title)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, bbox_inches="tight")
    print(f"PNG: {png} ({len(tris)} triángulos)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stl", type=Path)
    ap.add_argument("png", type=Path)
    ap.add_argument("--elev", type=float, default=28)
    ap.add_argument("--azim", type=float, default=-55)
    ap.add_argument("--title")
    a = ap.parse_args()
    render(a.stl, a.png, a.elev, a.azim, a.title)


if __name__ == "__main__":
    main()
