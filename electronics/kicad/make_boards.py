"""E6 · Placas KiCad desde las netlists SKIDL: huellas, nets, contorno, 4 capas, clases de red y colocación por bloques.

    source ~/.local/opt/kicad8/env.sh && /usr/bin/python3 electronics/kicad/make_boards.py [placa ...]

Para cada placa crea electronics/kicad/<placa>/<placa>.kicad_pcb (+ .kicad_pro y fp-lib-table) con:
  - las huellas de la netlist (bibliotecas de KiCad 8 + DronSwarm.pretty) y sus nets asignadas por número de pad;
  - el camino jerárquico (KIID) de cada pieza, para que "Actualizar PCB desde el esquema" siga funcionando;
  - contorno, 4 capas, reglas y clases de red (Potencia: 1.0 mm; AltaTension 12S: separación según recubrimiento);
  - colocación inicial agrupada por subcircuito (sin optimizar: el lazo de potencia GaN se ubica a mano, ver README).
Las piezas cuya huella falta (p. ej. LMG1210 hasta tener el plano RVR0019A) se listan y la placa queda incompleta.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
FP_DIR = Path(os.environ.get("KICAD8_FOOTPRINT_DIR", "/usr/share/kicad/footprints"))
MM = pcbnew.FromMM

# Contorno [mm] y nets de potencia por placa. 12S ≥ 51 V: IPC-2221 B4 (con recubrimiento) 0.13 mm; sin recubrimiento a
# más de 3,050 m (B3) pediría 1.5 mm → las placas de 12S llevan recubrimiento conformado obligatorio.
BOARDS = {
    "esc_ds_d": {"size": (40, 70), "power": r"^(VBUS|GND|BAT_N|PHASE_[ABC])$", "hv": True},
    "esc_ds_i": {"size": (60, 60), "power": r"^(VBUS|GND|PGND\d|M\d_[ABC])$", "hv": False},
    "fc": {"size": (55, 45), "power": r"^(GND|5V|BRICK\d_5V|USB_VBUS|5V_PERIPH|5V_HIPOWER)$", "hv": False},
    "gnss": {"size": (40, 40), "power": r"^(GND|5V)$", "hv": False},
    "bms_ds_i": {"size": (60, 40), "power": r"^(GND|PACK_N|CHG_N|CHG_MID)$", "hv": False},
    "bms_ds_d": {"size": (80, 45), "power": r"^(GND|PACK_N|CHG_N|CHG_MID)$", "hv": True},
    "charger": {"size": (100, 80), "power": r"^(VIN_RAW|VIN|VOUT_INT|VOUT_D|VOUT|GND|IN_N|OUT_N|SW_A|SW_B)$", "hv": True},
}


def parse_netlist(path: Path) -> tuple[list, dict]:
    text = path.read_text()
    comps = []
    for blk in re.split(r"\n\s*\(comp\s*\n", text[text.index("(components"):text.index("\n  (nets")])[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        val = re.search(r'\(value "([^"]*)"\)', blk).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        sheet = re.search(r'\(sheetpath\s+\(names "([^"]*)"\)\s+\(tstamps "([^"]*)"\)\)', blk)
        ts = re.findall(r'\(tstamps "([^"]+)"\)\)', blk)
        comps.append({"ref": ref, "value": val, "footprint": fp.group(1) if fp else "", "sheet": sheet.group(1) if sheet else "/",
                      "sheet_ts": sheet.group(2) if sheet else "/", "ts": ts[-1] if ts else ""})
    nets = {}
    body = text[text.index("(nets"):]
    for blk in re.split(r"\(net\s*\n\s*\(code", body)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        nets[name] = re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', blk)
    return comps, nets


def load_fp(fpid: str):
    lib, name = fpid.split(":", 1)
    path = HERE / "DronSwarm.pretty" if lib == "DronSwarm" else FP_DIR / f"{lib}.pretty"
    if not (path / f"{name}.kicad_mod").exists():
        return None
    return pcbnew.FootprintLoad(str(path), name)


SMALL = re.compile(r"^(Resistor_SMD|Capacitor_SMD|Inductor_SMD|LED_SMD|Diode_SMD):\w*_(0402|0603|0805)_|SOD-323|SOT-23$")


def bbox_mm(fp) -> tuple[float, float]:
    """Tamaño por el contorno de cortesía (courtyard) + 0.4 mm de separación."""
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return pcbnew.ToMM(bb.GetWidth()) + 0.4, pcbnew.ToMM(bb.GetHeight()) + 0.4


def _origin(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return fp.GetPosition() - bb.GetOrigin()


def _shelf(items: list, fps: dict, width: float) -> float:
    """Empaqueta por estantes (filas) en el ancho dado; items = lista de grupos (listas de ref). Devuelve el alto."""
    x0 = y0 = 2.0
    cx, cy, row_h = x0, y0, 0.0
    for refs in items:
        for r in sorted(refs, key=lambda r: -bbox_mm(fps[r])[1]):
            w, h = bbox_mm(fps[r])
            if cx + w > x0 + width:
                cx, cy, row_h = x0, cy + row_h, 0.0
            fps[r].SetPosition(pcbnew.VECTOR2I(MM(cx + 0.2), MM(cy + 0.2)) + _origin(fps[r]))
            cx += w
            row_h = max(row_h, h)
    return cy + row_h + 2.0


def place_groups(board, fps: dict, comps: list, size: tuple, exclude: set = frozenset(), top_width: float | None = None) -> float:
    """Piezas grandes arriba y pasivos chicos (0402-0805, SOT-23) abajo, ambos agrupados por subcircuito y en el mismo
    orden, para que cada pasivo quede bajo su bloque. Devuelve el alto usado [mm]."""
    top, bot = defaultdict(list), defaultdict(list)
    for c in comps:
        r = c["ref"]
        if r not in fps or r in exclude:
            continue
        if SMALL.search(c["footprint"]):
            fps[r].Flip(fps[r].GetPosition(), False)
            bot[c["sheet"]].append(r)
        else:
            top[c["sheet"]].append(r)
    sheets = sorted(set(top) | set(bot), key=lambda s: -sum(bbox_mm(fps[r])[0] * bbox_mm(fps[r])[1] for r in top.get(s, [])))
    W = size[0] - 4
    h_top = _shelf([top.get(s, []) for s in sheets], fps, top_width or W)
    h_bot = _shelf([bot.get(s, []) for s in sheets], fps, W)
    return max(h_top, h_bot)


def _to_top(fp, x: float, y: float, rot: float = 0.0) -> None:
    if fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))


def _track(board, a, b, net, width: float) -> None:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a)
    t.SetEnd(b)
    t.SetWidth(MM(width))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    t.SetLocked(True)
    board.Add(t)


def gnss_rf(board, fps: dict, size: tuple) -> None:
    """Cadena de RF en línea recta en la cara superior: u.FL → C7 (100 pF) → R2 (0 Ω) → pin 11 del LG290P, microcinta
    de 0.36 mm sobre el GND de In1; derivaciones (TVS, alimentación de la antena, π sin montar) bajo la línea."""
    u = next(fp for fp in fps.values() if fp.GetValue() == "LG290P")
    W, H = size
    _to_top(u, W - 12.2 / 2 - 3.0, H / 2)                              # módulo a la derecha, 3 mm del borde
    p11 = next(p for p in u.Pads() if p.GetNumber() == "11").GetPosition()
    y = pcbnew.ToMM(p11.y)
    x11 = pcbnew.ToMM(p11.x)
    # Todo fuera de los 3 mm libres que pide Quectel alrededor del módulo (borde del módulo = x11 − 1.05)
    _to_top(fps["R2"], x11 - 5.2, y)                                  # R1 del π (0 Ω)
    _to_top(fps["C7"], x11 - 7.4, y)                                  # bloqueo de DC 100 pF
    _to_top(fps["J_ANT"], x11 - 12.0, y, 180)                         # u.FL girado: el vivo mira al módulo
    for ref, x in (("C9", x11 - 4.72), ("C8", x11 - 6.0), ("D1", x11 - 9.3)):
        _to_top(fps[ref], x, y + 1.6, 270)                            # derivaciones a GND bajo la línea (pad 1 arriba)
    _to_top(fps["L1"], x11 - 8.9, y - 1.6, 270)                       # 68 nH arriba (pad 2 = línea, abajo)
    _to_top(fps["R1"], x11 - 8.9, y - 3.6, 270)                       # 10 Ω desde VDD_RF
    _to_top(fps["C5"], x11 - 7.6, y - 3.1, 90)                        # desacople de la alimentación de la antena
    _to_top(fps["C6"], x11 - 10.2, y - 3.1, 90)
    # Pads de prueba de UART2 y RESET_N junto a sus pines (6, 7, 8), fuera de los 3 mm del módulo
    for k, (ref, num) in enumerate((("TP_TXD2", "6"), ("TP_RXD2", "7"), ("TP_RESET_N", "8"))):
        py = pcbnew.ToMM(next(p for p in u.Pads() if p.GetNumber() == num).GetPosition().y)
        _to_top(fps[ref], x11 - 5.4 - 1.7 * (k % 2), py)
    nets = {n: board.FindNet(n) for n in ("ANT_LINE", "RF_PI", "RF_IN")}
    pad = {(r, n): next(p for p in fps[r].Pads() if p.GetNumber() == n).GetPosition()
           for r, n in (("J_ANT", "1"), ("C7", "1"), ("C7", "2"), ("R2", "1"), ("R2", "2"), ("D1", "1"), ("L1", "2"),
                        ("C8", "1"), ("C9", "1"))}
    _track(board, pad[("J_ANT", "1")], pad[("C7", "1")], nets["ANT_LINE"], 0.36)
    _track(board, pad[("C7", "2")], pad[("R2", "1")], nets["RF_PI"], 0.36)
    _track(board, pad[("R2", "2")], p11, nets["RF_IN"], 0.36)
    for (r, n), net in ((("D1", "1"), "ANT_LINE"), (("L1", "2"), "ANT_LINE"), (("C8", "1"), "RF_PI"), (("C9", "1"), "RF_IN")):
        q = pad[(r, n)]
        _track(board, q, pcbnew.VECTOR2I(q.x, p11.y), nets[net], 0.25)


def outline(board, w: float, h: float) -> None:
    for (a, b), (c, d) in (((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(a), MM(b)))
        s.SetEnd(pcbnew.VECTOR2I(MM(c), MM(d)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)


def rules(board, cfg: dict) -> dict:
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(4)
    board.SetCopperLayerCount(4)
    ds.m_TrackMinWidth = MM(0.127)
    ds.m_MinClearance = MM(0.127)
    ds.m_ViasMinSize = MM(0.45)
    ds.m_MinThroughDrill = MM(0.25)
    ns = ds.m_NetSettings
    dflt = ns.m_DefaultNetClass
    dflt.SetTrackWidth(MM(0.2))
    dflt.SetClearance(MM(0.15))
    dflt.SetViaDiameter(MM(0.6))
    dflt.SetViaDrill(MM(0.3))
    pw = pcbnew.NETCLASS("Potencia")
    pw.SetTrackWidth(MM(1.0))
    pw.SetClearance(MM(0.25 if cfg["hv"] else 0.2))
    pw.SetViaDiameter(MM(1.0))
    pw.SetViaDrill(MM(0.5))
    ns.m_NetClasses["Potencia"] = pw
    n = 0
    for net in board.GetNetsByName().values():
        if re.match(cfg["power"], str(net.GetNetname())):
            net.SetNetClass(pw)
            n += 1
    return {"potencia": n}


def project_file(path: Path, cfg: dict) -> None:
    """Proyecto KiCad con las clases de red (patrones) para que persistan al abrir en la interfaz."""
    pro = {"board": {"design_settings": {"rules": {"min_clearance": 0.127, "min_track_width": 0.127}}},
           "meta": {"filename": path.name, "version": 1},
           "net_settings": {"classes": [
               {"name": "Default", "clearance": 0.15, "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3},
               {"name": "Potencia", "clearance": 0.25 if cfg["hv"] else 0.2, "track_width": 1.0, "via_diameter": 1.0,
                "via_drill": 0.5}],
               "meta": {"version": 3},
               "netclass_patterns": [{"netclass": "Potencia", "pattern": cfg["power"]}]}}
    path.write_text(json.dumps(pro, indent=2) + "\n")
    (path.parent / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "DronSwarm")(type "KiCad")(uri "${KIPRJMOD}/../DronSwarm.pretty")(options "")(descr "Huellas propias"))\n)\n')


def make(board_name: str) -> dict:
    cfg = BOARDS[board_name]
    out = HERE / board_name
    comps, nets = parse_netlist(out / f"{board_name}.net")
    board = pcbnew.BOARD()
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes}
    fps, missing = {}, defaultdict(list)
    for c in comps:
        fp = load_fp(c["footprint"]) if c["footprint"] else None
        if fp is None:
            missing[c["footprint"] or "(sin huella)"].append(c["ref"])
            continue
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"])
        path = (c["sheet_ts"].rstrip("/") + "/" + c["ts"]) if c["ts"] else ""
        if path:
            fp.SetPath(pcbnew.KIID_PATH(path))
        board.Add(fp)
        for pad in fp.Pads():
            n = pin_net.get((c["ref"], pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fps[c["ref"]] = fp
    if board_name == "gnss":                                           # módulo y RF a la derecha; el resto en 13 mm
        rf = {r for r, fp in fps.items() if fp.GetValue() == "LG290P"} | {"J_ANT", "C7", "R2", "C8", "C9", "D1", "L1", "R1", "C5", "C6", "TP_TXD2", "TP_RXD2", "TP_RESET_N"}
        used_h = place_groups(board, fps, comps, cfg["size"], rf, 10.0)
        gnss_rf(board, fps, cfg["size"])
    else:
        used_h = place_groups(board, fps, comps, cfg["size"])
    w, h = cfg["size"][0], max(cfg["size"][1], used_h)
    outline(board, w, h)
    rc = rules(board, cfg)
    pcb = out / f"{board_name}.kicad_pcb"
    board.Save(str(pcb))
    project_file(out / f"{board_name}.kicad_pro", cfg)
    return {"placa": board_name, "piezas": len(fps), "nets": len(nets), "faltan_huellas": dict(missing),
            "contorno_mm": [w, round(h, 1)], "alto_pedido_mm": cfg["size"][1], **rc}


def main() -> None:
    names = sys.argv[1:] or list(BOARDS)
    res = [make(n) for n in names]
    f = HERE / "placas.json"
    prev = {r["placa"]: r for r in json.loads(f.read_text())} if f.exists() else {}
    prev.update({r["placa"]: r for r in res})                          # actualiza sin borrar las otras placas
    f.write_text(json.dumps([prev[k] for k in BOARDS if k in prev], indent=1, ensure_ascii=False) + "\n")
    for r in res:
        print(r)


if __name__ == "__main__":
    main()
