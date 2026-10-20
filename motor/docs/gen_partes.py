#!/usr/bin/env python3
"""M7 · Guía didáctica de las partes del motor → motor/docs/partes.html (autocontenida, se abre en el navegador).

Dibuja el corte del motor con la geometría REAL del diseño elegido (las mismas láminas del DXF de M6) y explica cada parte.

    .venv/bin/python motor/docs/gen_partes.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motor.calculo.design import H_TIP, SLOT_OPENING  # noqa: E402
from motor.calculo.report_m2 import magnet_spec, wire_plan  # noqa: E402

INF = ROOT / "motor" / "informes"
OUT = ROOT / "motor" / "docs" / "partes.html"


def halves(ns: int, r_s: float, w: float, h_slot: float, n_arc: int = 8) -> list[list[list[float]]]:
    """Las dos mitades de cobre de cada ranura (mm), en el orden lado-del-diente-k, lado-del-diente-k+1."""
    r_t = r_s - H_TIP * 1e3
    r_b = r_t - h_slot
    out = []
    for k in range(ns):
        phi_k, phi_n = 2 * math.pi * k / ns, 2 * math.pi * (k + 1) / ns
        phi_s = (phi_k + phi_n) / 2

        def p(r, a):
            return [round(r * math.cos(a), 3), round(r * math.sin(a), 3)]
        a_b1, a_t1 = phi_k + math.asin(w / 2 / r_b), phi_k + math.asin(w / 2 / r_t)
        a_b2, a_t2 = phi_n - math.asin(w / 2 / r_b), phi_n - math.asin(w / 2 / r_t)
        left = [p(r_b, a_b1), p(r_t, a_t1)] + [p(r_t, a_t1 + (phi_s - a_t1) * i / n_arc) for i in range(1, n_arc + 1)] + \
               [p(r_b, phi_s - (phi_s - a_b1) * i / n_arc) for i in range(0, n_arc)]
        right = [p(r_b, phi_s), p(r_t, phi_s)] + [p(r_t, phi_s + (a_t2 - phi_s) * i / n_arc) for i in range(1, n_arc + 1)] + \
                [p(r_b, a_b2 - (a_b2 - phi_s) * i / n_arc) for i in range(0, n_arc)]
        out += [left, right]
    return out


def lamination(ns: int, r_s: float, w: float, h_slot: float, n: int = 6) -> list[list[float]]:
    """Contorno exterior de la lámina (dientes con zapata), en mm."""
    r_t = r_s - H_TIP * 1e3
    r_b = r_t - h_slot
    b0 = SLOT_OPENING * 1e3
    pts = []
    for k in range(ns):
        phi_k, phi_n = 2 * math.pi * k / ns, 2 * math.pi * (k + 1) / ns
        phi_s = (phi_k + phi_n) / 2
        o1, o2 = phi_s - math.asin(b0 / 2 / r_s), phi_s + math.asin(b0 / 2 / r_s)
        a_t1, a_t2 = phi_k + math.asin(w / 2 / r_t), phi_n - math.asin(w / 2 / r_t)
        a_b1, a_b2 = phi_k + math.asin(w / 2 / r_b), phi_n - math.asin(w / 2 / r_b)
        ot1, ot2 = phi_s - math.asin(b0 / 2 / r_t), phi_s + math.asin(b0 / 2 / r_t)

        def p(r, a):
            return [round(r * math.cos(a), 3), round(r * math.sin(a), 3)]
        prev_o2 = (phi_k - math.pi / ns) + math.asin(b0 / 2 / r_s)
        pts += [p(r_s, prev_o2 + (o1 - prev_o2) * i / n) for i in range(n + 1)]          # cara del diente k (zapata)
        pts += [p(r_t, ot1), p(r_t, a_t1)][::-1][:0]
        pts += [p(r_t, ot1)]
        pts += [p(r_t, ot1 - (ot1 - a_t1) * i / 3) for i in range(1, 4)]
        pts += [p(r_b, a_b1)]
        pts += [p(r_b, a_b1 + (a_b2 - a_b1) * i / n) for i in range(1, n)]
        pts += [p(r_b, a_b2), p(r_t, a_t2)]
        pts += [p(r_t, a_t2 + (ot2 - a_t2) * i / 3) for i in range(1, 4)]
        pts += [p(r_s, o2)]
    return pts


def bom_cost() -> dict:
    rows = list(csv.DictReader(open(ROOT / "motor" / "bom" / "lista_materiales_motor.csv", encoding="utf-8")))
    return {v: round(sum(float(r["uso"]) / float(r["por_presentacion"]) * float(r["precio"]) for r in rows if r["motor"] in (v, "común")), 0)
            for v in ("DS-I", "DS-D")}


def data() -> dict:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    fem = json.loads((INF / "M4_fem.json").read_text())
    cad = json.loads((ROOT / "cad" / "exports" / "motor" / "resumen.json").read_text())
    cost = bom_cost()
    out = {}
    for veh, c in chosen.items():
        d, g, p = c["design"], c["geometry"], cad[veh]["params"]
        r_s = d["d_stator"] / 2 * 1e3
        out[veh] = {
            "ns": d["ns"], "poles": 2 * d["pole_pairs"], "r_s": r_s, "r_bore": g["r_bore"] * 1e3, "r_mag_in": g["r_mag_in"] * 1e3,
            "r_mag_out": g["r_mag_out"] * 1e3, "r_out": g["r_out"] * 1e3, "pole_arc": d["pole_arc"], "coils": c["coils"],
            "outline": lamination(d["ns"], r_s, g["w_tooth"] * 1e3, g["h_slot"] * 1e3),
            "halves": halves(d["ns"], r_s, g["w_tooth"] * 1e3, g["h_slot"] * 1e3),
            "label": c["label"], "stack": d["l_stack"] * 1e3, "turns": d["turns"], "delta": d["delta"], "wire": wire_plan(g["a_cond_ideal"]),
            "magnets": magnet_spec(c), "n_lam": p["n_lam"], "n_ring": p["n_ring"], "shaft": p["shaft"], "bearing_od": p["bearing_od"],
            "overhang": p["overhang"], "cap_t": p["cap_t"], "base_t": p["base_t"], "kv": round(fem[veh]["bemf"]["kv_fem"]),
            "r_mohm": round(c["r_line_20_ohm"] * 1e3), "eff": round(c["eta_weighted"] * 100, 1), "eff_cots": round(c["reference"]["weighted_efficiency"] * 100, 1),
            "mass_g": round(c["mass"]["total"] * 1e3), "autonomy": round((c["endurance_rel"] - 1) * 100, 1), "cost": cost[veh],
            "cots": c["reference"]["name"].split(" (")[0], "cots_price": 75 if veh == "DS-I" else 170, "w_tooth": g["w_tooth"] * 1e3,
            "gap": d["gap"] * 1e3, "h_magnet": d["h_magnet"] * 1e3, "h_ring": g["h_rotor_yoke"] * 1e3,
            "cog": round(fem[veh]["cogging"]["pct_of_hover"], 2), "bearing": "694ZZ" if veh == "DS-I" else "696ZZ"}
    return out


PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motor DronSwarm por dentro</title>
<style>
:root{--bg:#fcfcfb;--surface:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e4e3df;--accent:#2a78d6;
--steel:#9aa0a6;--steel2:#5f6368;--cu:#c77a3a;--a:#2a78d6;--b:#eb6834;--c:#1baf7a;--n:#d55181;--s:#6250d6;--print:#f2a65a;--sel:#eda100}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--surface:#1d1d1c;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e88;
--line:#33322f;--accent:#3987e5;--steel:#7d838a;--steel2:#b6bcc3;--cu:#d98c4a;--a:#3987e5;--b:#d95926;--c:#199e70;--n:#d55181;--s:#9085e9;--print:#c9853f}}
:root[data-theme="dark"]{--bg:#141413;--surface:#1d1d1c;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e88;--line:#33322f;--accent:#3987e5;
--steel:#7d838a;--steel2:#b6bcc3;--cu:#d98c4a;--a:#3987e5;--b:#d95926;--c:#199e70;--n:#d55181;--s:#9085e9;--print:#c9853f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:21px;margin:40px 0 8px}h3{margin:0 0 6px;font-size:18px}
.sub{color:var(--ink2);margin:0 0 18px}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0 20px}
.seg button{border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:7px 14px;font:inherit;cursor:pointer}
.seg button:first-child{border-radius:8px 0 0 8px}.seg button:last-child{border-radius:0 8px 8px 0}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff;border-color:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:8px 0 6px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stat b{display:block;font-size:22px}.stat span{color:var(--ink2);font-size:13px}
.grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:20px;align-items:start}
@media (max-width:860px){.grid{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px}
svg{width:100%;height:auto;display:block}
.part{cursor:pointer;transition:opacity .15s}.part:hover{opacity:.8}
.hl{stroke:var(--sel)!important;stroke-width:1.2!important}
.list{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0}
.chip{border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:999px;padding:4px 10px;font:inherit;font-size:14px;cursor:pointer}
.chip[aria-pressed="true"]{border-color:var(--sel);box-shadow:0 0 0 2px var(--sel) inset}
dl{margin:10px 0 0}dt{font-weight:600;color:var(--ink2);font-size:13px;text-transform:uppercase;letter-spacing:.03em;margin-top:10px}dd{margin:2px 0 0}
.warn{background:color-mix(in srgb,var(--sel) 14%,transparent);border-radius:8px;padding:8px 10px}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:13px;color:var(--ink2);margin-top:8px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-1px}
ol.steps{padding-left:22px}ol.steps li{margin:6px 0}
.anim-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:14px;color:var(--ink2)}
.anim-controls button{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}
input[type=range]{accent-color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
footer{color:var(--muted);font-size:13px;margin-top:40px}
</style>
</head>
<body>
<main>
<h1>El motor DronSwarm por dentro</h1>
<p class="sub">Un motor brushless "outrunner": las bobinas quedan quietas en el centro y la campana con los imanes gira por fuera, con la hélice arriba.
Toca cada parte del dibujo para ver qué es, para qué sirve y cómo la hacemos con la cortadora láser y la impresora.</p>
<div class="bar"><span>Motor del</span><div class="seg" role="group" aria-label="Dron">
<button data-veh="DS-I" aria-pressed="true">DS-I · inspección</button><button data-veh="DS-D" aria-pressed="false">DS-D · entrega</button></div></div>
<div class="stats" id="stats"></div>

<h2>1 · Las partes</h2>
<div class="grid">
 <div class="card">
  <svg id="top" viewBox="-60 -60 120 120" role="img" aria-label="Corte del motor visto desde arriba"></svg>
  <div class="legend"><span><i style="background:var(--steel)"></i>acero al silicio</span><span><i style="background:var(--a)"></i>fase A</span>
  <span><i style="background:var(--b)"></i>fase B</span><span><i style="background:var(--c)"></i>fase C</span><span><i style="background:var(--n)"></i>imán N</span>
  <span><i style="background:var(--s)"></i>imán S</span><span><i style="background:var(--steel2)"></i>anillo del rotor</span></div>
  <svg id="side" viewBox="0 0 120 70" role="img" aria-label="Corte lateral del motor" style="margin-top:14px"></svg>
  <div class="list" id="chips"></div>
 </div>
 <div class="card" id="info" aria-live="polite"></div>
</div>

<h2>2 · Cómo gira</h2>
<div class="grid">
 <div class="card"><svg id="anim" viewBox="-60 -60 120 120" role="img" aria-label="Animación del campo giratorio"></svg>
  <div class="anim-controls"><button id="play">Pausa</button><label>Velocidad <input id="speed" type="range" min="0.05" max="1" step="0.05" value="0.25"></label></div></div>
 <div class="card">
  <p>El controlador (ESC) manda corriente a las tres fases, <b style="color:var(--a)">A</b>, <b style="color:var(--b)">B</b> y <b style="color:var(--c)">C</b>, en turnos.
  Cada bobina se vuelve un electroimán. El color más intenso es más corriente.</p>
  <p>Esos electroimanes forman un campo magnético que <b>gira</b>. Los imanes de la campana lo siguen, porque los <b style="color:var(--n)">N</b> son atraídos por los S de las bobinas y al revés, y así gira la hélice.</p>
  <p>El ESC "escucha" la tensión que generan los imanes al pasar (la contra-FEM) para saber dónde está el rotor y cuándo cambiar de fase. Por eso no hacen falta sensores.</p>
  <p>Con <span id="np"></span> imanes y <span id="ns"></span> dientes, el campo da una vuelta eléctrica cada <span id="frac"></span> de vuelta mecánica. Eso multiplica el torque y deja girar la hélice lento y eficiente, sin reductor (ver M3).</p>
  <dl><dt>Kv</dt><dd><span id="kv2"></span> rpm por voltio: a 22 V sin carga giraría a ~<span id="rpmv"></span> rpm.</dd>
  <dt>Cogging (tirones sin corriente)</dt><dd><span id="cog"></span> % del torque de hover: casi imperceptible (FEM, M4).</dd></dl>
 </div>
</div>

<h2>3 · Armado paso a paso</h2>
<div class="card"><ol class="steps" id="steps"></ol></div>

<h2>4 · ¿Por qué hacerlo nosotros?</h2>
<div class="card"><table id="cmp"></table></div>
<footer>Generado por <code>motor/docs/gen_partes.py</code> con la geometría del diseño elegido (M2), verificado por elementos finitos (M4). Dimensiones en mm.</footer>
</main>
<script>
const DATA = __DATA__;
const PARTS = [
 {id:"lam", name:"Estator (paquete de láminas)", color:"var(--steel)",
  what: d=>`Un "engranaje" de acero al silicio con ${d.ns} dientes, hecho de ${d.n_lam} láminas de 0.20 mm pegadas (paquete de ${d.stack.toFixed(1)} mm de alto, Ø${(2*d.r_s).toFixed(1)} mm).`,
  does:"Guía el campo magnético de las bobinas hacia los imanes. Cada diente es el núcleo de un electroimán.",
  mat:"Acero al silicio no orientado de 0.20 mm (NO20), con aislante en las dos caras.",
  why:"Láminas finas y aisladas entre sí: el campo cambia cientos de veces por segundo y un bloque macizo se calentaría por corrientes parásitas. El silicio baja la histéresis. Los dientes terminan en una zapata ancha para repartir el campo y dejar una abertura de 1.6 mm por donde pasa el alambre.",
  how:"Se cortan con la cortadora láser de fibra desde el DXF (lamina_estator.dxf), se desbarban, y se apilan en el mandril impreso con la chaveta alineada, con una capa finísima de epoxi.",
  err:"Rebabas o borde quemado por exceso de potencia: más pérdidas. Láminas desalineadas: el bobinado roza y el rotor puede tocar."},
 {id:"cu", name:"Bobinado (cobre)", color:"var(--a)",
  what: d=>`Una bobina por diente: ${d.turns} vueltas de ${d.wire}, conectadas en ${d.delta?"triángulo":"estrella"} formando 3 fases.`,
  does:"Cuando pasa corriente, cada bobina convierte su diente en un electroimán. El ESC las enciende en turnos y crea el campo que gira.",
  mat:"Alambre de cobre esmaltado clase H (aislado para 200 °C), varios hilos finos en paralelo.",
  why:"Bobinas concentradas, cada una alrededor de un solo diente: son cortas, con poco cobre fuera del hierro, y eso da menos pérdidas. Varios hilos finos llenan mejor la ranura y son más fáciles de doblar que uno grueso.",
  how:"A mano, con el soporte de bobinado impreso, siguiendo el orden de fases del CAD (A, a, B, b… una mayúscula es un sentido y la minúscula el contrario). Después se impregna con barniz.",
  err:"Raspar el esmalte contra el borde del diente da un cortocircuito. Bobinar flojo deja menos cobre en la ranura: el motor pierde la eficiencia ganada (es el riesgo principal del diseño)."},
 {id:"gap", name:"Entrehierro", color:"var(--line)",
  what: d=>`El espacio de aire de ${d.gap.toFixed(1)} mm entre los dientes y los imanes.`,
  does:"Deja girar el rotor sin tocar el estator. Por ahí cruza todo el campo que produce el torque.",
  mat:"Aire.",
  why:"Cuanto más chico, más campo y más torque, pero hay que fabricarlo sin roces. 0.5-0.6 mm es lo que se logra en casa con piezas impresas y rodamientos buenos.",
  how:"Lo definen la concentricidad de la base (tubo con rodamientos) y de la tapa. Se verifica girando a mano: no debe rozar en ninguna posición.",
  err:"Base o tapa excéntricas: el rotor roza, o la atracción magnética carga de más los rodamientos."},
 {id:"mag", name:"Imanes", color:"var(--n)",
  what: d=>`Imanes de neodimio: ${d.magnets}.`,
  does:"Crean el campo fijo del rotor. Las bobinas los empujan y los tiran: eso es el torque.",
  mat:"Neodimio-hierro-boro N48SH: muy fuerte y apto para 150 °C (el SH aguanta el calor y la corriente sin desmagnetizarse).",
  why:"Polaridad alternada N-S-N-S alrededor del anillo. Bloques chicos en vez de arcos curvos: son más baratos y casi igual de buenos con tantos polos.",
  how:"Se pegan dentro del anillo del rotor usando la plantilla impresa, que los deja equidistantes, con epoxi. Cada imán se verifica con una brújula antes de soltarlo.",
  err:"Dos imanes iguales seguidos: el motor vibra y pierde torque. Golpearlos: se rompen (son frágiles) y pellizcan fuerte. Siempre con pinza no magnética, gafas y guantes."},
 {id:"ring", name:"Anillo del rotor (campana)", color:"var(--steel2)",
  what: d=>`Anillo de acero de ${d.h_ring.toFixed(1)} mm de pared (Ø exterior ${(2*d.r_out).toFixed(1)} mm), hecho de ${d.n_ring} anillos de chapa de 1 mm pegados.`,
  does:"Cierra el camino del campo entre un imán y el siguiente por fuera y sostiene los imanes cuando gira.",
  mat:"Acero común DC01 (sin silicio): ahí el campo casi no cambia, así que no hace falta acero eléctrico.",
  why:"Por dentro no es redondo: tiene una cara plana por imán. Así cada bloque apoya plano, queda en su lugar y no choca con el anillo en los bordes. Su espesor está calculado para que el acero no se sature (≈ 1.7 T en la FEM).",
  how:"Se corta con el láser desde anillo_rotor.dxf y se apilan los anillos alineados por las muescas, con epoxi.",
  err:"Anillos desalineados: desbalance y vibración."},
 {id:"cap", name:"Tapa (lleva la hélice)", color:"var(--print)",
  what: d=>`Disco impreso de ${d.cap_t.toFixed(0)} mm con 4 aberturas de ventilación, el cubo del eje y los 4 agujeros de la hélice.`,
  does:"Une el anillo del rotor con el eje y transmite el torque a la hélice. Las aberturas dejan entrar aire para enfriar el bobinado.",
  mat:"PETG impreso (ASA o PA-CF si se quiere más margen de temperatura).",
  why:"El anillo entra en una pollera que lo centra y se pega usando el útil de concentricidad. El agujero del eje es en forma de D: el plano del eje traba el giro. Arriba, una arandela y un anillo E quedan al ras dentro de un rebaje. La hélice se atornilla a insertos roscados de latón.",
  how:"Se imprime (tapa.stl) boca abajo, con 4 paredes y relleno de 40 % o más. El agujero se escaría a medida, el eje se pega con adhesivo retenedor y los insertos se colocan con el soldador.",
  err:"Pegar el anillo sin el útil: queda descentrado y el rotor roza o vibra. No escariar el agujero: el eje queda flojo o torcido."},
 {id:"shaft", name:"Eje", color:"var(--muted)",
  what: d=>`Eje de acero de Ø${d.shaft.toFixed(0)} mm que va de la base a la tapa.`,
  does:"Es el centro de giro: une la tapa (rotor + hélice) con los rodamientos de la base.",
  mat:"Acero plata (o 4140) rectificado h6.",
  why:"Con este diámetro, el eje tiene un factor de seguridad ≥ 3.5 contra el torque y el efecto giroscópico de la hélice (M5).",
  how:"Se compra la barra rectificada, se corta a medida, se le hacen dos ranuras para los anillos E (DIN 6799) y un plano para la tapa. Sin torno: se gira en el taladro y se ranura con un disco de corte fino.",
  err:"Ranuras muy anchas: el anillo E baila. Rayar la zona de los rodamientos."},
 {id:"brg", name:"Rodamientos", color:"var(--ink2)",
  what: d=>`Dos rodamientos ${d.bearing} dentro del tubo de la base.`,
  does:"Dejan girar el eje casi sin fricción y soportan el empuje de la hélice. Van en X: los aros de afuera apoyan en hombros de la base; los de adentro quedan apretados entre un anillo E abajo y la tapa arriba, con una arandela ondulada que les da precarga (sin juego).",
  mat:"Acero, con tapas ZZ contra el polvo.",
  why:"Por fatiga duran decenas de miles de horas (M5). En la mina los limita el polvo, así que conviene comprar de marca y revisarlos.",
  how:"Se colocan a presión (con morsa, no a golpes) en los asientos de la base impresa. El ajuste se calibra antes con la probeta de ajustes.",
  err:"Golpearlos al instalarlos: quedan marcados, hacen ruido y duran poco."},
 {id:"base", name:"Base", color:"var(--print)",
  what: d=>`Pieza impresa con el tubo que lleva los rodamientos y sostiene el estator, y la placa con el patrón de montaje DMI.`,
  does:"Fija el motor al brazo del dron y mantiene el estator centrado con el rotor.",
  mat:"PETG impreso (llega a 40-51 °C según M5; PETG ablanda a ~70 °C).",
  why:"El tubo tiene una chaveta que entra en la muesca de las láminas: el estator no puede girar. Adentro tiene los dos asientos de rodamiento con hombros. Abajo lleva 4 insertos roscados para atornillarla al brazo y un canal para los 3 cables de fase.",
  how:"Se imprime (base.stl) con la brida sobre la cama. Los insertos se colocan con el soldador. El estator se pega sobre el tubo con epoxi, centrado con tiras de 0.05 mm.",
  err:"Tubo excéntrico: el entrehierro queda desparejo, sube la atracción magnética y aparecen roces."},
];
const STEPS = ["Cortar las láminas del estator y los anillos del rotor con el láser (DXF).","Desbarbar y limpiar con alcohol.",
"Apilar las láminas en el mandril, pegarlas y prensarlas; curar 24 h.","Aislar con barniz en los bordes y papel Nomex en las ranuras.",
"Bobinar cada diente siguiendo el orden de fases; apretado y ordenado.","Conectar las fases (triángulo) y soldar los cables.",
"Impregnar el bobinado con barniz y curar.","Pegar los anillos del rotor.","Pegar los imanes con la plantilla, alternando N y S (verificar con brújula).",
"Imprimir la probeta de ajustes y calibrar la impresora; imprimir la tapa, la base y los útiles.","Ensamblar: rodamientos, estator sobre la base, anillo del rotor en la tapa (útil de concentricidad), eje, arandelas y anillos E.","Balancear y control de calidad: resistencia, aislamiento, giro libre, Kv."];
let veh="DS-I", sel="lam";
const $=s=>document.querySelector(s);
const NS="http://www.w3.org/2000/svg";
function el(tag,attrs,parent){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);parent&&parent.appendChild(e);return e;}
const pts=a=>a.map(p=>p[0].toFixed(3)+","+(-p[1]).toFixed(3)).join(" ");
function ringPath(r1,r2){return `M ${r2} 0 A ${r2} ${r2} 0 1 0 ${-r2} 0 A ${r2} ${r2} 0 1 0 ${r2} 0 Z M ${r1} 0 A ${r1} ${r1} 0 1 1 ${-r1} 0 A ${r1} ${r1} 0 1 1 ${r1} 0 Z`;}
function sector(r1,r2,a1,a2){const p=(r,a)=>`${(r*Math.cos(a)).toFixed(3)} ${(-r*Math.sin(a)).toFixed(3)}`;return `M ${p(r1,a1)} L ${p(r2,a1)} A ${r2} ${r2} 0 0 0 ${p(r2,a2)} L ${p(r1,a2)} A ${r1} ${r1} 0 0 1 ${p(r1,a1)} Z`;}
const phaseColor={A:"var(--a)",B:"var(--b)",C:"var(--c)"};
function drawTop(svg, d, interactive, rot=0){
  svg.innerHTML=""; const R=d.r_out*1.08; svg.setAttribute("viewBox",`${-R} ${-R} ${2*R} ${2*R}`);
  const g=el("g",{},svg);
  const stator=el("path",{d:"M "+pts(d.outline).replace(/ /g," L ")+" Z "+`M ${d.r_bore} 0 A ${d.r_bore} ${d.r_bore} 0 1 1 ${-d.r_bore} 0 A ${d.r_bore} ${d.r_bore} 0 1 1 ${d.r_bore} 0 Z`,
    "fill-rule":"evenodd",fill:"var(--steel)",stroke:"var(--steel2)","stroke-width":.15,class:interactive?"part":"","data-part":"lam"},g);
  const coils=[];
  d.halves.forEach((h,i)=>{const slot=Math.floor(i/2), side=i%2; const tooth= side===0? slot : (slot+1)%d.ns;
    const ch=d.coils[tooth]; const c=el("polygon",{points:pts(h),fill:phaseColor[ch.toUpperCase()],stroke:"var(--cu)","stroke-width":.12,
    class:interactive?"part":"","data-part":"cu"},g); coils.push({el:c,phase:"ABC".indexOf(ch.toUpperCase()),sign:(ch===ch.toUpperCase()?1:-1)*(side===0?1:-1)});});
  const rotor=el("g",{transform:`rotate(${-rot})`},g);
  const half=d.pole_arc*Math.PI/d.poles;
  for(let k=0;k<d.poles;k++){const c=k*2*Math.PI/d.poles; el("path",{d:sector(d.r_mag_in,d.r_mag_out,c-half,c+half),fill:k%2?"var(--s)":"var(--n)",class:interactive?"part":"","data-part":"mag"},rotor);}
  el("path",{d:ringPath(d.r_mag_out,d.r_out),"fill-rule":"evenodd",fill:"var(--steel2)",class:interactive?"part":"","data-part":"ring"},rotor);
  el("path",{d:ringPath(d.r_s,d.r_mag_in),"fill-rule":"evenodd",fill:"transparent",stroke:"var(--line)","stroke-dasharray":"0.6 0.6","stroke-width":.12,class:interactive?"part":"","data-part":"gap"},g);
  el("circle",{r:d.shaft/2,fill:"var(--muted)",class:interactive?"part":"","data-part":"shaft"},g);
  el("circle",{r:d.bearing_od/2,fill:"none",stroke:"var(--ink2)","stroke-width":.5,class:interactive?"part":"","data-part":"brg"},g);
  return {coils,rotor};
}
function drawSide(d){
  const s=$("#side"); s.innerHTML="";
  const H=d.base_t+2*d.overhang+d.stack+d.cap_t+12, W=2*d.r_out*1.1, sc=Math.min(110/W,62/H);
  s.setAttribute("viewBox",`${-W/2*sc-4} -4 ${W*sc+8} ${H*sc+10}`);
  const y=v=>(H-v)*sc, x=v=>v*sc, rect=(x0,x1,y0,y1,fill,part,extra={})=>{el("rect",{x:x(x0),y:y(y1),width:x(x1-x0),height:(y1-y0)*sc,fill,class:"part","data-part":part,...extra},s);el("rect",{x:x(-x1),y:y(y1),width:x(x1-x0),height:(y1-y0)*sc,fill,class:"part","data-part":part,...extra},s);};
  const zs=d.base_t+d.overhang, ze=zs+d.stack, top=ze+d.overhang+1;
  rect(d.bearing_od/2, Math.max(d.r_bore+5,(d.cots_price>100?35:25)/2+4), 0, d.base_t, "var(--print)","base");
  rect(d.bearing_od/2, d.r_bore, d.base_t, top, "var(--print)","base",{opacity:.8});
  rect(d.shaft/2, d.bearing_od/2, 0, 4, "var(--ink2)","brg"); rect(d.shaft/2, d.bearing_od/2, top-4, top, "var(--ink2)","brg");
  rect(d.r_bore, d.r_s, zs, ze, "var(--steel)","lam");
  rect(d.r_bore+1, d.r_s-1.5, zs-d.overhang+0.5, zs, "var(--a)","cu"); rect(d.r_bore+1, d.r_s-1.5, ze, ze+d.overhang-0.5, "var(--a)","cu");
  rect(d.r_mag_in, d.r_mag_out, zs, ze, "var(--n)","mag"); rect(d.r_mag_out, d.r_out, zs-1, ze+1, "var(--steel2)","ring");
  rect(0, d.r_out+1.2, top, top+d.cap_t, "var(--print)","cap");
  el("rect",{x:x(-d.shaft/2),y:y(top+d.cap_t+4),width:x(d.shaft),height:(top+d.cap_t+10)*sc,fill:"var(--muted)",class:"part","data-part":"shaft"},s);
  el("text",{x:0,y:y(top+d.cap_t+5.5),"text-anchor":"middle","font-size":3,fill:"var(--ink2)"},s).textContent="hélice ↑";
}
function info(){
  const d=DATA[veh], p=PARTS.find(q=>q.id===sel);
  $("#info").innerHTML=`<h3>${p.name}</h3><p>${p.what(d)}</p><dl><dt>Qué hace</dt><dd>${p.does}</dd><dt>Material</dt><dd>${p.mat}</dd>
  <dt>Por qué tiene esa forma</dt><dd>${p.why}</dd><dt>Cómo lo hacemos aquí</dt><dd>${p.how}</dd><dt>Errores típicos</dt><dd class="warn">${p.err}</dd></dl>`;
  document.querySelectorAll(".chip").forEach(c=>c.setAttribute("aria-pressed",c.dataset.part===sel));
  document.querySelectorAll("#top .part, #side .part").forEach(e=>e.classList.toggle("hl",e.dataset.part===sel));
}
function render(){
  const d=DATA[veh];
  $("#stats").innerHTML=[["Ranuras / polos",d.label],["Eficiencia ponderada",d.eff+" %<span> (comercial "+d.eff_cots+" %)</span>"],
   ["Masa",d.mass_g+" g"],["Autonomía del dron","+"+d.autonomy+" %"],["Material por motor","US$"+d.cost+"<span> (comercial US$"+d.cots_price+")</span>"]]
   .map(([a,b])=>`<div class="stat"><b>${b}</b><span>${a}</span></div>`).join("");
  drawTop($("#top"),d,true); drawSide(d);
  document.querySelectorAll("#top .part, #side .part").forEach(e=>e.addEventListener("click",()=>{sel=e.dataset.part;info();}));
  $("#chips").innerHTML=PARTS.map(p=>`<button class="chip" data-part="${p.id}">${p.name}</button>`).join("");
  document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{sel=c.dataset.part;info();}));
  $("#np").textContent=d.poles; $("#ns").textContent=d.ns; $("#frac").textContent="1/"+(d.poles/2); $("#kv2").textContent=d.kv;
  $("#rpmv").textContent=(d.kv*22).toLocaleString("es"); $("#cog").textContent=d.cog;
  $("#steps").innerHTML=STEPS.map(s=>`<li>${s}</li>`).join("");
  $("#cmp").innerHTML=`<tr><th></th><th>Comercial (${d.cots})</th><th>Propio (${d.label})</th></tr>
   <tr><td>Precio / material</td><td>US$${d.cots_price}</td><td>US$${d.cost} de material + ~${veh==="DS-I"?4:6} h de trabajo</td></tr>
   <tr><td>Eficiencia (mismo modelo)</td><td>${d.eff_cots} %</td><td>${d.eff} %</td></tr>
   <tr><td>Autonomía del dron</td><td>—</td><td>+${d.autonomy} %</td></tr>
   <tr><td>Kv / resistencia</td><td>—</td><td>${d.kv} rpm/V / ${d.r_mohm} mΩ</td></tr>`;
  info(); anim.setup();
}
const anim={t:0,run:true,setup(){this.parts=drawTop($("#anim"),DATA[veh],false);},
  frame(dt){if(!this.run)return;const d=DATA[veh];this.t+=dt*Number($("#speed").value);const th=this.t;const pp=d.poles/2;
   this.parts.rotor.setAttribute("transform",`rotate(${-(th*180/Math.PI)%360})`);
   this.parts.coils.forEach(c=>{const i=Math.sin(pp*th-c.phase*2*Math.PI/3)*c.sign;c.el.setAttribute("opacity",(0.18+0.82*Math.abs(i)).toFixed(2));});}};
let last=performance.now();function loop(now){anim.frame((now-last)/1000);last=now;requestAnimationFrame(loop);}requestAnimationFrame(loop);
$("#play").addEventListener("click",()=>{anim.run=!anim.run;$("#play").textContent=anim.run?"Pausa":"Seguir";});
document.querySelectorAll(".seg button").forEach(b=>b.addEventListener("click",()=>{veh=b.dataset.veh;document.querySelectorAll(".seg button").forEach(x=>x.setAttribute("aria-pressed",x===b));render();}));
render();
</script>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(PAGE.replace("__DATA__", json.dumps(data(), ensure_ascii=False)))
    print(OUT, f"{OUT.stat().st_size / 1024:.0f} kB")


if __name__ == "__main__":
    main()
