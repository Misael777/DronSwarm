#!/usr/bin/env python3
"""S06-04 · Inyección de fallas en vuelo y verificación de la reacción (failsafe) de PX4.

El dron despega, sube a 20 m, se aleja 50 m al este y ahí se le inyecta una falla:

  motor    muere un motor: en Gazebo deja de empujar (plugin simulation/plugins/safety) y a la vez se corta la
           telemetría de su ESC (inyector de fallas de PX4). PX4 debe detectarlo, retirarlo de la asignación
           (CA_FAILURE_MODE = 1) y aterrizar solo (COM_ACT_FAIL_ACT = 2). Requiere el parche de ESC con telemetría
           (simulation/px4/patches/0001-gz-esc-telemetria.patch).
  motor_sin_deteccion   solo muere el motor; PX4 no se entera (un dron real sin telemetría de ESC): sigue contando
           con el motor muerto. Se le ordena aterrizar a los 15 s.
  gps      se pierde el GNSS (SIM_GPS_USED=0, sin fix). Se espera que PX4 aterrice sin irse lejos.
  battery  batería crítica (el simulador de batería baja a 6 %). Se espera retorno a casa (RTL) y aterrizaje.
  link     se pierde el enlace con la estación (se apaga el servidor MAVSDK). Se espera RTL por pérdida de enlace.
  geofence (HU-10) geocerca de 70 × 70 m alrededor de la base: una misión que la cruza debe ser rechazada, y una orden
           de ir 60 m al este debe terminar con el dron detenido antes del límite y de regreso en casa.

La verificación usa la posición REAL de Gazebo (monitor del mundo swarm), no la de PX4: con GNSS caído, PX4 no sabe
dónde está, y con el enlace caído, nosotros tampoco.

    SCENE=swarm MODEL=ds_d MISSION=fault MISSION_ARGS="--case motor" bash tools/sitl/run_gz_multi.sh 1 carpeta
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "sitl"))
from demo_formation import connect, first, offset  # noqa: E402
from mavsdk_grpc import System  # noqa: E402

AWAY_EAST_M = 50.0
ALT = 20.0


def ground_truth(csv_path: Path, name: str) -> list[tuple[float, float, float, float]]:
    """Serie (t, x, y, z) real del dron desde el monitor."""
    out = []
    if not csv_path.exists():
        return out
    with open(csv_path) as f:
        for line in f:
            p = line.rstrip().split(",")
            if len(p) == 5 and p[1] == name:
                out.append((float(p[0]), float(p[2]), float(p[3]), float(p[4])))
    return out


async def wait_gt(csv_path: Path, name: str, pred, timeout: float) -> tuple[float, float, float, float] | None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        gt = ground_truth(csv_path, name)
        if gt and pred(gt[-1]):
            return gt[-1]
        await asyncio.sleep(1.0)
    return None


class Recorder:
    """Modos de vuelo, inclinación máxima y altura mientras haya enlace."""

    def __init__(self, d):
        self.d = d
        self.modes: list[tuple[float, str]] = []
        self.max_tilt = 0.0
        self.t0 = time.monotonic()
        self.armed = True

    async def run(self):
        async def _modes():
            async for m in self.d.telemetry.flight_mode():
                if not self.modes or self.modes[-1][1] != m.name:
                    self.modes.append((round(time.monotonic() - self.t0, 1), m.name))
                    print(f"   modo PX4: {m.name}", flush=True)

        async def _att():
            async for a in self.d.telemetry.attitude_euler():
                if self.armed:
                    c = math.cos(math.radians(a.roll_deg)) * math.cos(math.radians(a.pitch_deg))
                    self.max_tilt = max(self.max_tilt, math.degrees(math.acos(max(-1.0, min(1.0, c)))))

        async def _arm():
            async for a in self.d.telemetry.armed():
                self.armed = a

        await asyncio.gather(_modes(), _att(), _arm(), return_exceptions=True)


async def setup_flight(d, params: dict, away_m: float = AWAY_EAST_M) -> tuple:
    for k, v in params.items():
        (await d.param.set_param_int(k, v)) if isinstance(v, int) else (await d.param.set_param_float(k, v))
    home = await anext(d.telemetry.home())
    await asyncio.sleep(8)
    await first(d.telemetry.health(), lambda h: h.is_armable and h.is_local_position_ok, 180)
    for attempt in range(30):
        try:
            await d.action.arm()
            break
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(2)
    await d.action.takeoff()
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= 2.0, 120)
    alt_abs = home.absolute_altitude_m + ALT
    await d.action.goto_location(home.latitude_deg, home.longitude_deg, alt_abs, float("nan"))
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= ALT - 1, 120)
    lat, lon = offset(home.latitude_deg, home.longitude_deg, 0.0, away_m)
    print(f"→ a {away_m:.0f} m al este, {ALT:.0f} m de altura", flush=True)
    await d.action.goto_location(lat, lon, alt_abs, float("nan"))
    await asyncio.sleep(away_m / 4 + 8)
    await d.action.hold()
    await asyncio.sleep(4)
    return home


FENCE_HALF_M = 35.0


async def geofence_case(d, home, monitor: Path, name: str, home_xy) -> dict:
    """HU-10: geocerca cuadrada de 70 m alrededor de la base. 1) Una misión que la cruza debe ser rechazada.
    2) Una orden de ir 60 m al este debe terminar detenida antes del límite y con retorno a casa (GF_ACTION = RTL)."""
    from mavsdk_grpc.geofence import FenceType, GeofenceData, Point, Polygon
    from mavsdk_grpc.mission import MissionItem, MissionPlan

    corners = [offset(home.latitude_deg, home.longitude_deg, n * FENCE_HALF_M, e * FENCE_HALF_M)
               for n, e in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
    await d.geofence.upload_geofence(GeofenceData([Polygon([Point(la, lo) for la, lo in corners], FenceType.INCLUSION)], []))
    print("   geocerca de 70 × 70 m cargada", flush=True)
    out = {"fence_half_m": FENCE_HALF_M}
    lat, lon = offset(home.latitude_deg, home.longitude_deg, 0.0, 60.0)
    alt = ALT
    wp = MissionItem(lat, lon, alt, 5.0, True, float("nan"), float("nan"), MissionItem.CameraAction.NONE, float("nan"),
                     float("nan"), 2.0, float("nan"), float("nan"), MissionItem.VehicleAction.NONE)
    try:
        await d.mission.upload_mission(MissionPlan([wp]))
        await d.mission.start_mission()
        await asyncio.sleep(4)
        mode = (await anext(d.telemetry.flight_mode())).name
        out["mission_rejected"] = mode != "MISSION"
        out["mission_note"] = f"modo tras iniciar: {mode}"
        if mode == "MISSION":
            await d.action.hold()
    except Exception as e:                              # rechazo explícito de PX4 (misión fuera de la geocerca)
        out["mission_rejected"] = True
        out["mission_note"] = str(e)[:160]
    print(f"   misión que cruza la geocerca: {'rechazada' if out['mission_rejected'] else 'ACEPTADA'}", flush=True)
    await asyncio.sleep(3)
    print("→ orden de ir 60 m al este (fuera de la geocerca)", flush=True)
    try:
        await d.action.goto_location(lat, lon, home.absolute_altitude_m + ALT, float("nan"))
        await first(d.telemetry.armed(), lambda a: not a, 90)      # la geocerca lo frena y lo trae (RTL)
        out["goto_outcome"] = "frenado en el límite + RTL automático"
    except Exception as e:                             # PX4 rechazó la orden o quedó detenido adentro: volver a casa
        out["goto_outcome"] = f"orden rechazada o detenido dentro ({type(e).__name__}); RTL ordenado"
        await d.action.return_to_launch()
        await first(d.telemetry.armed(), lambda a: not a, 240)
    print(f"   {out['goto_outcome']}", flush=True)
    gt = ground_truth(monitor, name)
    out["max_dist_from_home_m"] = round(max(math.hypot(p[1] - home_xy[0], p[2] - home_xy[1]) for p in gt), 1) if gt else None
    return out


def landing_summary(gt, t_fault: float, home_xy) -> dict:
    after = [p for p in gt if p[0] >= t_fault]
    if not after:
        return {"ground_truth": False}
    landed = after[-1]
    # velocidad vertical de llegada al suelo: últimos 1.5 s antes de que la altura deje de bajar
    vz = 0.0
    for a, b in zip(after, after[1:]):
        if b[3] < 1.5 and b[0] > a[0]:
            vz = max(vz, (a[3] - b[3]) / (b[0] - a[0]))
    min_z = min(p[3] for p in after)
    alt_loss = max(0.0, after[0][3] - min(p[3] for p in after[: max(1, int(10 / 0.1))]))  # en los 10 s siguientes
    return {"ground_truth": True, "final_xy_m": [round(landed[1], 1), round(landed[2], 1)],
            "final_z_m": round(landed[3], 2),
            "dist_to_home_m": round(math.hypot(landed[1] - home_xy[0], landed[2] - home_xy[1]), 1),
            "dist_from_fault_point_m": round(math.hypot(landed[1] - after[0][1], landed[2] - after[0][2]), 1),
            "touchdown_vz_m_s": round(vz, 2), "altitude_loss_10s_m": round(alt_loss, 1), "min_z_m": round(min_z, 2)}


async def run(case: str, monitor: Path, model: str, extra: dict | None = None) -> dict:
    name = f"{model}_0"
    d = await connect(0)
    params = {"SYS_FAILURE_EN": 1}
    if case == "motor":                                   # ya vienen en los airframes de 6 y 8 motores (tools/gen_sdf.py);
        params |= {"CA_FAILURE_MODE": 1, "COM_ACT_FAIL_ACT": 2, "FD_ACT_EN": 1}    # se repiten antes de armar
    if case == "motor_sin_deteccion":                     # un dron sin telemetría de ESC: PX4 no puede detectar
        params |= {"CA_FAILURE_MODE": 0}
    if case == "battery":
        # umbrales de operación minera (el regreso desde lejos necesita margen); el estimador de PX4 ve el 6 % del
        # simulador como ~19 %: con los umbrales por defecto (crítico 7 %) nunca volvería
        params |= {"COM_LOW_BAT_ACT": 3, "SIM_BAT_DRAIN": 40.0, "BAT_LOW_THR": 0.35, "BAT_CRIT_THR": 0.25,
                   "BAT_EMERGEN_THR": 0.10}
    if case == "link":
        params |= {"NAV_DLL_ACT": 2, "COM_DL_LOSS_T": 5}
    if case == "geofence":
        params |= {"GF_ACTION": 3, "GF_PREDICT": 1}
    params |= extra or {}
    rec = Recorder(d)
    asyncio.ensure_future(rec.run())
    home = await setup_flight(d, params, away_m=0.0 if case == "geofence" else AWAY_EAST_M)
    gt = ground_truth(monitor, name)
    home_xy = (gt[0][1], gt[0][2]) if gt else (0.0, 0.0)
    t_fault_sim = gt[-1][0] if gt else 0.0
    print(f"✖ falla: {case}", flush=True)
    res: dict = {"case": case, "model": model, "params": params}

    if case in ("motor", "motor_sin_deteccion"):
        from mavsdk_grpc.failure import FailureType, FailureUnit

        k = 0
        kill = asyncio.to_thread(subprocess.run, ["gz", "topic", "-t", f"/model/{name}/motor_failure", "-m", "gz.msgs.Int32",
                                                  "-p", f"data: {k}"], check=True, timeout=10)
        if case == "motor":                                # el ESC muere: sin empuje y sin telemetría, a la vez
            await asyncio.gather(kill, d.failure.inject(FailureUnit.SYSTEM_MOTOR, FailureType.OFF, k + 1))
        else:
            await kill
        res["motor_off"] = k
        res["detection"] = case == "motor"
        if case == "motor":                                # PX4 debe detectarlo y aterrizar solo
            try:
                await first(d.telemetry.flight_mode(), lambda m: m.name == "LAND", 20)
                res["autonomous_land"] = True
            except asyncio.TimeoutError:
                res["autonomous_land"] = False
                print("   PX4 no activó el aterrizaje: se ordena", flush=True)
                await d.action.land()
        else:
            await asyncio.sleep(15)                        # ¿se sostiene con un motor menos?
            print("↓ aterrizaje ordenado con un motor apagado", flush=True)
            await d.action.land()
        await first(d.telemetry.armed(), lambda a: not a, 240)
    elif case == "gps":
        await d.param.set_param_int("SIM_GPS_USED", 0)
        try:
            await first(d.telemetry.armed(), lambda a: not a, 300)
        except asyncio.TimeoutError:
            res["note"] = "no aterrizó en 300 s"
    elif case == "battery":
        await d.param.set_param_float("SIM_BAT_MIN_PCT", 6.0)
        await first(d.telemetry.armed(), lambda a: not a, 400)
    elif case == "link":
        d._stop_mavsdk_server()                           # la estación deja de enviar heartbeats
        print("   enlace con la estación cortado; se observa con la posición real de Gazebo", flush=True)
        await wait_gt(monitor, name, lambda p: math.hypot(p[1] - home_xy[0], p[2] - home_xy[1]) < 3 and p[3] < 0.8, 300)
        await asyncio.sleep(5)
        d2 = System(port=50071)                           # enlace recuperado: ¿está en tierra y desarmado?
        await d2.connect(system_address="udpin://0.0.0.0:14540")
        await first(d2.core.connection_state(), lambda s: s.is_connected, 60)
        res["armed_after"] = await anext(d2.telemetry.armed())
        res["mode_after"] = (await anext(d2.telemetry.flight_mode())).name
    elif case == "geofence":
        res |= await geofence_case(d, home, monitor, name, home_xy)
    await asyncio.sleep(3)
    gt = ground_truth(monitor, name)
    res |= landing_summary(gt, t_fault_sim, home_xy)
    res["px4_modes"] = rec.modes
    res["max_tilt_deg"] = round(rec.max_tilt, 1)
    res["passed"] = verdict(case, res)
    print(("✔ " if res["passed"] else "✘ ") + json.dumps({k: res.get(k) for k in
          ("dist_to_home_m", "dist_from_fault_point_m", "touchdown_vz_m_s", "max_tilt_deg")}), flush=True)
    return res


def verdict(case: str, r: dict) -> bool:
    if not r.get("ground_truth"):
        return False
    safe_landing = r["final_z_m"] < 1.0 and r["touchdown_vz_m_s"] < 3.0
    modes = [m for _, m in r.get("px4_modes", [])]
    if case == "motor":
        return safe_landing and r["max_tilt_deg"] < 45 and r.get("autonomous_land", False)
    if case == "motor_sin_deteccion":
        return safe_landing and r["max_tilt_deg"] < 45 and r["altitude_loss_10s_m"] < 8
    if case == "gps":
        return safe_landing and r["dist_from_fault_point_m"] < 25
    if case == "battery":
        return safe_landing and "RETURN_TO_LAUNCH" in modes and r["dist_to_home_m"] < 5
    if case == "link":
        return safe_landing and r["dist_to_home_m"] < 5 and r.get("armed_after") is False
    if case == "geofence":
        return (safe_landing and r["mission_rejected"] and r["max_dist_from_home_m"] < FENCE_HALF_M + 5
                and r["dist_to_home_m"] < 5)
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", choices=["motor", "motor_sin_deteccion", "gps", "battery", "link", "geofence"], required=True)
    ap.add_argument("--param", action="append", default=[], help="parámetro extra de PX4, p. ej. MC_AIRMODE=1 (repetible)")
    ap.add_argument("--n", type=int, default=1, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    monitor = a.out.parent / "monitor.csv"
    extra = {k: (float(v) if "." in v else int(v)) for k, v in (p.split("=", 1) for p in a.param)}
    res = asyncio.run(run(a.case, monitor, os.environ.get("MODEL", "ds_d"), extra))
    res["n"], res["ok"] = 1, int(res["passed"])
    print(json.dumps(res, indent=2, ensure_ascii=False))
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    os._exit(0 if res["passed"] else 1)           # los streams de gRPC abiertos no dejan terminar al intérprete


if __name__ == "__main__":
    try:
        main()
    except Exception:                                  # sin esto, un error deja colgado el intérprete (streams de gRPC)
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        os._exit(2)
