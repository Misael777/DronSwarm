#!/usr/bin/env python3
"""S05-04 · Misión de inspección: levantamiento fotogramétrico en grilla + órbita de talud.

Planificador (independiente del simulador) + ejecución vía MAVSDK/PX4 (portable a SITL, HITL y dron real).

- Grilla: altura calculada para el GSD pedido con la cámara del DS-I; separación de líneas y de fotos por traslape.
- Captura: en SITL no hay disparo de cámara real, así que se registra la posición real del dron en el punto más
  cercano a cada foto planificada (geoetiqueta) y se mide el error.
- Órbita: un giro completo dentro del tajo, bajo el borde, mirando al centro (vista de los taludes opuestos).

    python control/missions/inspection.py --out resultados/inspeccion.json
"""

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "sitl"))
from demo_formation import connect, first, offset  # noqa: E402

EARTH_R = 6_378_137.0


@dataclass(frozen=True)
class Camera:
    """Cámara de inspección del DS-I (supuesto del PRD: sensor 1", 20 MP)."""
    sensor_w_mm: float = 13.2
    sensor_h_mm: float = 8.8
    focal_mm: float = 8.8
    px_w: int = 5472
    px_h: int = 3648

    def gsd_m(self, height_m: float) -> float:
        return height_m * self.sensor_w_mm / (self.focal_mm * self.px_w)

    def height_for_gsd(self, gsd_m: float) -> float:
        return gsd_m * self.focal_mm * self.px_w / self.sensor_w_mm

    def footprint(self, height_m: float) -> tuple[float, float]:
        """(ancho transversal, largo en el sentido de vuelo) de una foto [m]."""
        g = self.gsd_m(height_m)
        return self.px_w * g, self.px_h * g


@dataclass(frozen=True)
class SurveyPlan:
    height_m: float
    gsd_cm: float
    line_spacing_m: float
    photo_spacing_m: float
    lines: list            # [[(x0, y0), (x1, y1)], ...] en metros ENU desde la base
    photos: list           # [(x, y), ...]
    path_length_m: float


def plan_grid(area: tuple[float, float, float, float], cam: Camera, gsd_m: float,
              front: float = 0.75, side: float = 0.65) -> SurveyPlan:
    """Grilla tipo "cortadora de césped" con líneas norte-sur sobre el rectángulo (xmin, xmax, ymin, ymax)."""
    xmin, xmax, ymin, ymax = area
    h = cam.height_for_gsd(gsd_m)
    across, along = cam.footprint(h)
    spacing = across * (1 - side)
    step = along * (1 - front)
    n_lines = max(2, math.ceil((xmax - xmin) / spacing) + 1)
    xs = [xmin + i * (xmax - xmin) / (n_lines - 1) for i in range(n_lines)]
    y0, y1 = ymin - along / 2, ymax + along / 2          # extender media foto para cubrir el borde
    lines, photos, length = [], [], 0.0
    for i, x in enumerate(xs):
        a, b = ((x, y0), (x, y1)) if i % 2 == 0 else ((x, y1), (x, y0))
        lines.append([a, b])
        n_ph = max(2, math.ceil((y1 - y0) / step) + 1)
        photos += [(x, a[1] + (b[1] - a[1]) * k / (n_ph - 1)) for k in range(n_ph)]
        length += abs(y1 - y0) + (spacing if i < n_lines - 1 else 0)
    return SurveyPlan(h, 100 * gsd_m, spacing, step, lines, photos, length)


def enu_to_latlon(home, x: float, y: float) -> tuple[float, float]:
    return offset(home.latitude_deg, home.longitude_deg, y, x)


def latlon_to_enu(home, lat: float, lon: float) -> tuple[float, float]:
    north = math.radians(lat - home.latitude_deg) * EARTH_R
    east = math.radians(lon - home.longitude_deg) * EARTH_R * math.cos(math.radians(home.latitude_deg))
    return east, north


async def fly(plan: SurveyPlan, pit: dict, speed: float, orbit_r: float, orbit_depth: float) -> dict:
    from mavsdk_grpc.action import OrbitYawBehavior
    from mavsdk_grpc.mission import MissionItem, MissionPlan

    d = await connect(0)
    home = await anext(d.telemetry.home())
    items = []
    for a, b in plan.lines:
        for x, y in (a, b):
            lat, lon = enu_to_latlon(home, x, y)
            items.append(MissionItem(lat, lon, plan.height_m, speed, True, float("nan"), float("nan"),
                                     MissionItem.CameraAction.NONE, float("nan"), float("nan"), 3.0, float("nan"),
                                     float("nan"), MissionItem.VehicleAction.NONE))
    await d.mission.set_return_to_launch_after_mission(False)
    await d.mission.upload_mission(MissionPlan(items))
    for attempt in range(30):
        try:
            await d.action.arm()
            break
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(2)
    t0 = time.monotonic()
    track: list = []
    print(f"→ grilla: {len(plan.lines)} líneas a {plan.height_m:.0f} m (GSD {plan.gsd_cm:.1f} cm/px), {len(plan.photos)} fotos", flush=True)
    await d.mission.start_mission()

    async def record():
        last = -1.0
        async for p in d.telemetry.position():        # leer cada mensaje (pausar aquí acumula retraso)
            now = time.monotonic() - t0
            if now - last >= 0.2:
                track.append((now, *latlon_to_enu(home, p.latitude_deg, p.longitude_deg), p.relative_altitude_m))
                last = now

    rec = asyncio.create_task(record())
    await first(d.mission.mission_progress(), lambda m: m.total > 0 and m.current >= m.total, 900)
    t_grid = time.monotonic() - t0
    print(f"✔ grilla completa en {t_grid:.0f} s", flush=True)

    cx, cy = pit["center"]
    lat, lon = enu_to_latlon(home, cx, cy)
    orbit_alt = home.absolute_altitude_m - orbit_depth
    print(f"→ órbita de talud: radio {orbit_r:.0f} m, {orbit_depth:.0f} m bajo el borde del tajo", flush=True)
    await d.action.do_orbit(orbit_r, 5.0, OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER, lat, lon, orbit_alt)
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m <= -orbit_depth + 3, 240)
    t_orbit0 = time.monotonic()
    await asyncio.sleep(2 * math.pi * orbit_r / 5.0 + 5)
    print(f"✔ órbita completa ({time.monotonic() - t_orbit0:.0f} s)", flush=True)

    print("↩ regreso a la base y aterrizaje", flush=True)
    await d.action.goto_location(home.latitude_deg, home.longitude_deg, home.absolute_altitude_m + 40, float("nan"))
    await first(d.telemetry.position(), lambda p: math.hypot(*latlon_to_enu(home, p.latitude_deg, p.longitude_deg)) < 3, 300)
    await d.action.land()
    await first(d.telemetry.armed(), lambda a: not a, 180)
    rec.cancel()

    # Geoetiquetas: posición real más cercana a cada foto planificada (solo el tramo de la grilla)
    grid_track = [p for p in track if p[0] <= t_grid]
    errors, tags = [], []
    for px, py in plan.photos:
        best = min(grid_track, key=lambda p: (p[1] - px) ** 2 + (p[2] - py) ** 2)
        err = math.hypot(best[1] - px, best[2] - py)
        errors.append(err)
        tags.append({"plan": [round(px, 1), round(py, 1)], "real": [round(best[1], 1), round(best[2], 1)], "alt_m": round(best[3], 1)})
    orbit_track = [p for p in track if p[0] > t_grid]
    min_alt = min((p[3] for p in orbit_track), default=None)
    return {"n": 1, "ok": 1, "plan": {k: v for k, v in asdict(plan).items() if k not in ("lines", "photos")},
            "photos": len(plan.photos), "photo_error_mean_m": round(sum(errors) / len(errors), 2),
            "photo_error_max_m": round(max(errors), 2), "grid_time_s": round(t_grid), "orbit_min_alt_m": min_alt,
            "duration_s": round(time.monotonic() - t0), "geotags": tags,
            "track": [[round(v, 1) for v in p] for p in track[::5]], "lines": plan.lines,
            "passed": max(errors) < 10 and (min_alt is not None and min_alt < -orbit_depth + 5)}


def plot(result: dict, layout: dict, png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse

    pit = layout["pit"]
    fig, ax = plt.subplots(figsize=(9, 7), dpi=130)
    face = pit["bench_h_m"] / math.tan(math.radians(pit["face_angle_deg"]))
    r = 30.0
    for _ in range(pit["benches"] + 1):
        ax.add_patch(Ellipse(pit["center"], 2 * r, 2 * r * pit["aspect"], fill=False, color="#a08060", lw=0.8))
        r += face + pit["berm_m"]
    c = layout["conveyor"]
    ax.plot([c["start"][0], c["end"][0]], [c["start"][1], c["end"][1]], color="#c9a227", lw=3, label="faja transportadora")
    for a, b in result["lines"]:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#a0aec0", lw=1, ls="--")
    tr = result["track"]
    ax.plot([p[1] for p in tr], [p[2] for p in tr], color="#2c5282", lw=1.2, label="recorrido real")
    g = result["geotags"]
    ax.scatter([t["real"][0] for t in g], [t["real"][1] for t in g], s=10, color="#c05621", zorder=3, label="fotos (geoetiqueta)")
    ax.scatter([0], [0], marker="^", s=80, color="black", label="base")
    ax.set_aspect("equal")
    ax.set_xlabel("Este [m]")
    ax.set_ylabel("Norte [m]")
    p = result["plan"]
    ax.set_title(f"Inspección del tajo: {result['photos']} fotos a {p['height_m']:.0f} m (GSD {p['gsd_cm']:.1f} cm/px), "
                 f"error de posición medio {result['photo_error_mean_m']} m", fontsize=9)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gsd", type=float, default=0.03, help="GSD objetivo [m/px] (PRD: ≤ 3 cm)")
    ap.add_argument("--speed", type=float, default=10.0)
    ap.add_argument("--orbit-radius", type=float, default=45.0)
    ap.add_argument("--orbit-depth", type=float, default=15.0, help="metros bajo el borde del tajo")
    ap.add_argument("--n", type=int, default=1, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    layout = json.loads((ROOT / "simulation/xtdrone/worlds/mine_layout.json").read_text())
    pit = layout["pit"]
    half_x = 98.0
    area = (pit["center"][0] - half_x, pit["center"][0] + half_x,
            pit["center"][1] - half_x * pit["aspect"], pit["center"][1] + half_x * pit["aspect"])
    plan = plan_grid(area, Camera(), a.gsd)
    res = asyncio.run(fly(plan, pit, a.speed, a.orbit_radius, a.orbit_depth))
    summary = {k: v for k, v in res.items() if k not in ("geotags", "track", "lines")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        (a.out.parent / "geotags.json").write_text(json.dumps(res["geotags"], indent=1) + "\n")
        plot(res, layout, a.out.parent / "inspeccion.png")
    raise SystemExit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
