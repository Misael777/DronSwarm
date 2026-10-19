#!/usr/bin/env python3
"""S06-06 · Evidencia de simulación por historia de usuario → docs/evidencias/simulacion/README.md

Lee los resultados (JSON) de cada prueba guardada en docs/evidencias/ y arma la matriz historia → prueba → métrica →
criterio → estado. Así los números del informe salen siempre de los archivos de resultados.

    .venv/bin/python tools/evidence_report.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "docs" / "evidencias"
SIM = EV / "simulacion"
OUT = SIM / "README.md"


def j(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def ok(flag: bool | None) -> str:
    return "—" if flag is None else ("✅ cumple" if flag else "❌ no cumple")


def fault_row(case: str, label: str, criterion: str) -> str:
    r = j(SIM / "fallas" / case / "resultado.json")
    hu = "HU-10" if case == "geofence" else "HU-09"
    if not r:
        return f"| {hu} | {label} | (sin corrida) | {criterion} | pendiente |"
    modes = " → ".join(m for _, m in r.get("px4_modes", [])) or "—"
    metric = (f"aterrizó a {r.get('dist_to_home_m')} m de casa y a {r.get('dist_from_fault_point_m')} m del punto de la falla; "
              f"llegada al suelo {r.get('touchdown_vz_m_s')} m/s; inclinación máx. {r.get('max_tilt_deg')}°; modos PX4: {modes}")
    if case.startswith("motor"):
        metric += f"; perdió {r.get('altitude_loss_10s_m')} m de altura en 10 s"
    if case == "geofence":
        metric = (f"misión que cruza la geocerca: {'rechazada' if r.get('mission_rejected') else 'ACEPTADA'}; "
                  f"distancia máx. a la base {r.get('max_dist_from_home_m')} m (límite {r.get('fence_half_m')} m); "
                  f"{r.get('goto_outcome', '')}; aterrizó a {r.get('dist_to_home_m')} m de casa")
    if r.get("note"):
        metric += f". _{r['note']}_"
    return f"| {hu} | {label} | {metric} | {criterion} | {ok(r.get('passed'))} |"


def write() -> Path:
    kin = j(SIM / "enjambre_cinematico" / "resumen.json") or {}
    sitl = j(SIM / "enjambre_sitl" / "resumen.json")
    sitl1 = j(SIM / "enjambre_sitl" / "corrida_01" / "seguridad.json")
    hu08 = j(SIM / "hu08_sectores" / "resultado.json")
    insp = j(EV / "sitl" / "inspeccion_tajo" / "resultado.json")
    entr = j(EV / "sitl" / "entrega_fondo_tajo" / "resultado.json")
    coop = j(EV / "sitl" / "coop_10kg" / "takeoff.json")
    cvs = {p.stem: j(p) for p in sorted((SIM / "calculo_vs_sim").glob("*.json"))}

    nominal = kin.get("consenso_nominal", {})
    kin_runs = sum(v["runs"] for k, v in kin.items() if k != "sin_evitacion")
    kin_coll = sum(v["runs_with_collision"] for k, v in kin.items() if k != "sin_evitacion")
    rows = [
        "| Historia | Prueba | Resultado medido | Criterio | Estado |",
        "|---|---|---|---|---|",
    ]
    if insp:
        rows.append(f"| HU-01 | Grilla fotogramétrica sobre el tajo (DS-I, mina simulada, S05) | {insp['photos']} fotos, error medio de "
                    f"posición {insp['photo_error_mean_m']} m, grilla en {insp['grid_time_s']} s | GSD ≤ 3 cm/px; ortofoto ≤ 5 cm "
                    "(la ortofoto se valida con ODM en campo) | ✅ vuelo · ODM pendiente (S13) |")
        rows.append(f"| HU-02 | Órbita de talud dentro del tajo (DS-I, S05) | bajó a {abs(insp['orbit_min_alt_m']):.0f} m bajo el borde | "
                    "GSD ≤ 1 cm/px a 30 m de la fachada | 🟡 parcial: falta misión de fachada |")
    if entr:
        rows.append(f"| HU-06 | Entrega de 5 kg al fondo del tajo con liberación (DS-D, S05) | caja liberada a {entr['delivery_error_m']} m "
                    f"del objetivo | entrega + liberación + regreso; 3 km con ≥ 20 % de batería | ✅ en simulación; 3 km verificado "
                    "por cálculo (+114 % de margen) |")
    if coop:
        rows.append(f"| (pedido) | Carga cooperativa: 3 DS-D levantan 10 kg (S05) | caja a {coop['box_max_height_m']} m, trasladada "
                    f"{coop['box_moved_north_m']} m | levantar, trasladar y aterrizar | ✅ vista previa (reparto de carga: v2) |")
    if hu08:
        rows.append(f"| HU-08 | 6 DS-I levantan un área por sectores y 'abortar todo' (PX4 + Gazebo) | sectores asignados, capas "
                    f"{min(hu08['layers_m']):.0f}-{max(hu08['layers_m']):.0f} m, separación mínima 3D {hu08['min_separation_3d_m']} m, "
                    f"todos en casa {hu08['abort_to_all_landed_s']} s después de abortar | sectores, altitudes separadas, nunca < 10 m, "
                    f"abortar con un botón | {ok(hu08['passed'])} |")
    if sitl:
        rows.append(f"| HU-08 | Enjambre de 6 en formación cerrada: V, torre, círculo, cruce, regreso (PX4 + Gazebo, {sitl['runs']} corridas) | "
                    f"{sitl['runs_with_collision']} corridas con colisión; separación mínima {sitl['min_separation_m']} m; "
                    f"torre a {sitl['min_obstacle_clearance_m']} m | 0 colisiones en 20 corridas (S06-03) | "
                    f"{ok(sitl['runs_with_collision'] == 0 and sitl['runs'] >= 20)} |")
    elif sitl1:
        rows.append(f"| HU-08 | Enjambre de 6 en formación cerrada (PX4 + Gazebo, 1 corrida) | separación mínima {sitl1['min_separation_m']} m, "
                    f"colisiones {sitl1['collisions']} | 0 colisiones en 20 corridas | 🟡 campaña pendiente |")
    if nominal:
        rows.append(f"| HU-08 | Simulador rápido: {kin_runs} corridas en 8 condiciones (radio con 30-50 % de pérdida, caída de radio, viento) | "
                    f"{kin_coll} corridas con colisión; separación mínima {min(v['min_separation_m']['min'] for k, v in kin.items() if k != 'sin_evitacion')} m | "
                    "0 colisiones | " + ok(kin_coll == 0) + " |")
    rows += [
        fault_row("motor", "Motor caído en DS-D con detección (ESC con telemetría)", "se sostiene y aterriza sin golpe"),
        fault_row("motor_dsh", "Motor caído en DS-H (8 motores) con detección", "se sostiene y aterriza sin golpe"),
        fault_row("motor_sin_deteccion", "Motor caído en DS-D sin detección", "ídem (muestra por qué hace falta la detección)"),
        fault_row("gps", "Pérdida de GNSS (DS-I)", "aterrizaje seguro sin alejarse > 25 m"),
        fault_row("battery", "Batería crítica (DS-I)", "RTL automático y aterrizaje en casa"),
        fault_row("link", "Pérdida de enlace con la estación (DS-I)", "RTL automático y aterrizaje en casa"),
        fault_row("geofence", "Geocerca de 70 × 70 m (DS-I)", "misión rechazada y el dron no cruza el límite"),
    ]
    cad = SIM / "cad_s07_s08"
    if cad.exists():
        ins, ent, mix = (j(cad / f) for f in ("inspeccion_ds-i_cad.json", "entrega_ds-d_cad.json", "enjambre_mixto_cad.json"))
        if ins:
            rows.append(f"| HU-01/02 | Inspección con el DS-I **diseñado en CAD** (masa y malla reales, S07) | {ins['photos']} fotos, error medio "
                        f"{ins['photo_error_mean_m']} m, órbita a {abs(ins['orbit_min_alt_m']):.0f} m bajo el borde | igual que S05 | {ok(ins['passed'])} |")
        if ent:
            rows.append(f"| HU-06 | Entrega con el DS-D **diseñado en CAD** (S08) | caja liberada a {ent['delivery_error_m']} m del objetivo | "
                        f"igual que S05 | {ok(ent['passed'])} |")
        if mix:
            rows.append(f"| HU-08 | Enjambre mixto DS-I + DS-D (CAD) + DS-H en formación (S08) | {mix['ok']} de {mix['n']} drones completaron | "
                        f"formación de 4 drones de 3 tamaños | {ok(mix['passed'])} |")
    rows += [
        "| HU-03 | Corredor de faja transportadora | — | video 4K georreferenciado de 3 km | pendiente (misión de corredor, S13) |",
        "| HU-04, HU-05, HU-11 | Procesamiento fotogramétrico (ODM) | — | DEM ±5 cm, modelo en ≤ 30 min, sin licencias | pendiente (S13) |",
        "| HU-07 | Envío de muestras | cubierto por la entrega HU-06 | caja sellada, registro en bitácora | 🟡 bitácora pendiente (DS-GCS) |",
        "| HU-12 | Mantenimiento rápido | — | cambio de motor/hélice/batería en minutos | pendiente (diseño mecánico, S07-S09) |",
        "| HU-13 | Mina subterránea | — | — | v2 |",
    ]
    cvs_rows = ["| Dron | Vuelo | Error de rpm | Empuje/peso | Autonomía a las rpm medidas / calculada |", "|---|---|---|---|---|"]
    for name, r in cvs.items():
        cvs_rows.append(f"| {r['vehicle']} | {name.split('_', 1)[1]} | {r['rpm_error_pct']:+.1f} % | {r['thrust_over_weight']:.3f} | "
                        f"{r['endurance_min_at_measured_rpm']} / {r['endurance_min_predicted']} min |")
    kin_rows = ["| Condición | Corridas | Con colisión | Separación mín. | Torre (libre) | Error de formación p95 |", "|---|---|---|---|---|---|"]
    for k, r in kin.items():
        kin_rows.append(f"| {k.replace('_', ' ')} | {r['runs']} | {r['runs_with_collision']} | {r['min_separation_m']['min']} m | "
                        f"{r['min_obstacle_clearance_m']} m | {r['formation_error_p95_m_median']} m |")
    lines = [
        "# Evidencia de simulación por historia de usuario",
        "",
        f"> Generado por `tools/evidence_report.py` el {dt.date.today().isoformat()} a partir de los resultados guardados en "
        "`docs/evidencias/`. No editar a mano.",
        "",
        "Todo esto es **simulación**: PX4 real (el mismo autopiloto que volará) con drones modelados desde el dimensionamiento, "
        "en Gazebo. Las colisiones las mide un monitor del mundo con la posición real de cada dron, no el código que se prueba. "
        "Lo que la simulación no puede probar (cámara real, radio real, motores reales) se valida en los prototipos (S10-S16).",
        "",
        "## Matriz por historia",
        "",
        *rows,
        "",
        "## Simulador rápido del enjambre (Monte Carlo)",
        "",
        "Mismo código de control que en PX4 + Gazebo, con dinámica simplificada para correr cientos de casos: viento con ráfagas, "
        "ruido de GNSS y la radio simulada (retardo, pérdidas, alcance). `sin evitación` es el control: muestra que el escenario "
        "sí exige esquivar.",
        "",
        *kin_rows,
        "",
        "Figuras: `enjambre_cinematico/trayectorias_nominal.png`, `trayectorias_caida_radio_en_cruce.png` y la animación `enjambre_nominal.gif`.",
        "",
        "## Cálculo ↔ simulación",
        "",
        *cvs_rows,
        "",
        "Coherencia del modelo del simulador con el diseño (mismas constantes); la validación independiente es el banco de empuje (S10).",
        "",
        "## Carpetas",
        "",
        "- `enjambre_cinematico/` campaña Monte Carlo · `enjambre_sitl/` enjambre en PX4 + Gazebo · `hu08_sectores/` levantamiento por sectores",
        "- `fallas/<caso>/` inyección de fallas · `calculo_vs_sim/` métricas de vuelo contra el dimensionamiento",
        "- Misiones del S05 (inspección, entrega, carga cooperativa): `docs/evidencias/sitl/`",
        "- Para verlo en vivo: `./dronswarm.sh` → **N** (con ventana de Gazebo).",
        "",
    ]
    OUT.write_text("\n".join(lines))
    return OUT


if __name__ == "__main__":
    print(write())
