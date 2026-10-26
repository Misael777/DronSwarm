"""E6 · Ruteo automático (Freerouting) + DRC (kicad-cli) de las placas generadas por make_boards.py.

    source ~/.local/opt/kicad8/env.sh && /usr/bin/python3 electronics/kicad/route_boards.py gnss [fc ...]

Para cada placa: plano de GND en In1.Cu y de alimentación en In2.Cu (zonas → planos en el DSN), exporta Specctra DSN,
rutea con Freerouting 2.5 (Java 25, sin interfaz), importa el SES, rellena zonas, guarda y corre el DRC. El resultado
(pistas, vías, conexiones sin rutear, violaciones) va a electronics/kicad/<placa>/ruteo.json.
Es un PRIMER PASE: las pistas de potencia y RF se revisan a mano antes de fabricar (ver electronics/kicad/README.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
JAVA = Path.home() / ".local/opt/jre25/bin/java"
FREEROUTING = Path.home() / ".local/opt/freerouting/freerouting-2.5.0.jar"
MM = pcbnew.FromMM
PLANES = {"gnss": "3V3_GNSS", "fc": "3V3", "bms_ds_i": "3V3", "bms_ds_d": "3V3", "esc_ds_i": "3V3", "esc_ds_d": "3V3",
          "charger": "3V3"}
RF = {"gnss": ("ANT_LINE", "RF_PI", "RF_IN")}       # microcinta 50 Ω en L1 sobre GND en L2 (prepreg 0.2 mm): ~0.36 mm


def zone(board, net: str, layer, inset: float = 0.6, solid: bool = True) -> None:
    bb = board.GetBoardEdgesBoundingBox()
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)          # sin islas de cobre aisladas
    ol = z.Outline()
    ol.NewOutline()
    x0, y0 = pcbnew.ToMM(bb.GetX()) + inset, pcbnew.ToMM(bb.GetY()) + inset
    x1, y1 = pcbnew.ToMM(bb.GetRight()) - inset, pcbnew.ToMM(bb.GetBottom()) - inset
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(MM(x), MM(y))
    board.Add(z)


def edge_keepout(board, margin: float = 0.7) -> None:
    """Cuatro áreas prohibidas (pistas y vías) a lo largo del borde: Freerouting no conoce la separación al borde."""
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()))
    for a, b, c, e in ((x0, y0, x1, y0 + margin), (x0, y1 - margin, x1, y1), (x0, y0, x0 + margin, y1), (x1 - margin, y0, x1, y1)):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET.AllCuMask()
        z.SetLayerSet(ls)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((a, b), (c, b), (c, e), (a, e)):
            ol.Append(MM(x), MM(y))
        board.Add(z)


def route(name: str, passes: int = 100) -> dict:
    d = HERE / name
    pcb = d / f"{name}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    for t in list(board.GetTracks()):
        if not t.IsLocked():                                           # las pistas bloqueadas (RF) se conservan
            board.Remove(t)
    for z in list(board.Zones()):
        board.Remove(z)
    board.GetDesignSettings().m_TrackMinWidth = MM(0.15)
    edge_keepout(board)
    zone(board, "GND", pcbnew.In1_Cu)
    if board.FindNet(PLANES[name]):
        zone(board, PLANES[name], pcbnew.In2_Cu)
    ns = board.GetDesignSettings().m_NetSettings
    if name in RF:
        rf = pcbnew.NETCLASS("RF50")
        rf.SetTrackWidth(MM(0.36))
        rf.SetClearance(MM(0.3))
        ns.m_NetClasses["RF50"] = rf
        for n in RF[name]:
            if board.FindNet(n):
                board.FindNet(n).SetNetClass(rf)
    dsn, ses = d / f"{name}.dsn", d / f"{name}.ses"
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    cmd = [str(JAVA), "-jar", str(FREEROUTING), "-de", str(dsn), "-do", str(ses), "-mp", str(passes), "-mt", "4",
           "--gui.enabled=false"]
    log = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    (d / "freerouting.log").write_text(log.stdout[-20000:] + log.stderr[-5000:])
    if not ses.exists():
        return {"placa": name, "error": "Freerouting no generó el SES (ver freerouting.log)"}
    pcbnew.ImportSpecctraSES(board, str(ses))
    for z in [z for z in board.Zones() if z.GetIsRuleArea()]:
        board.Remove(z)                                                # las áreas eran solo para el autorruteador
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone(board, "GND", layer, inset=0.6)                           # rellenos de GND exteriores (tras el ruteo)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(pcb))
    drc_json = d / "drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--schematic-parity",
                    "-o", str(drc_json), str(pcb)], capture_output=True, text=True)
    rep = json.loads(drc_json.read_text()) if drc_json.exists() else {}
    viol = [v for v in rep.get("violations", []) if v.get("severity") == "error"]
    kinds = {}
    for v in viol:
        kinds[v["type"]] = kinds.get(v["type"], 0) + 1
    res = {"placa": name, "pistas": sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"),
           "vias": sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA"),
           "sin_rutear": len(rep.get("unconnected_items", [])), "errores_drc": len(viol), "tipos": kinds}
    (d / "ruteo.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    for f in (dsn, ses):
        f.unlink(missing_ok=True)
    return res


def best_of(name: str, tries: int = 3) -> dict:
    """Freerouting no es determinista: se rutea hasta `tries` veces y se conserva la placa con menos pendientes."""
    import shutil
    d = HERE / name
    pcb = d / f"{name}.kicad_pcb"
    base = d / f"{name}.unrouted.kicad_pcb"
    shutil.copy(pcb, base)
    best, best_key = None, None
    for k in range(tries):
        shutil.copy(base, pcb)
        r = route(name)
        key = (r.get("sin_rutear", 999) + r.get("errores_drc", 999), k)
        if best is None or key < best_key:
            best, best_key = r, key
            shutil.copy(pcb, d / f"{name}.best.kicad_pcb")
            shutil.copy(d / "drc.json", d / "drc.best.json")
        if key[0] == 0:
            break
    shutil.move(d / f"{name}.best.kicad_pcb", pcb)
    shutil.move(d / "drc.best.json", d / "drc.json")
    base.unlink()
    best["intentos"] = k + 1
    (d / "ruteo.json").write_text(json.dumps(best, indent=1, ensure_ascii=False) + "\n")
    return best


if __name__ == "__main__":
    os.environ.setdefault("KICAD8_FOOTPRINT_DIR", "")
    for n in sys.argv[1:]:
        print(best_of(n), flush=True)
