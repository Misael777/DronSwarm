"""M0 · Materiales del motor: acero eléctrico, imanes, cobre y plásticos de impresión.

Son valores TÍPICOS de catálogo, por clase de material. Se reemplazan por los del proveedor elegido (S17-05) y por
mediciones (pérdidas en el hierro con el anillo de prueba, M8).

Pérdidas en el hierro (modelo de dos términos, Steinmetz-Bertotti simplificado, válido para 0.5-1.6 T):
    p [W/kg] = kh · f · B^ALPHA + ke · (f · B)^2
kh y ke se ajustan con dos puntos de catálogo (1.0 T a 50 Hz y a 400 Hz). El corte con láser daña ~0.3-0.5 mm del
borde de cada lámina (tensiones y recristalización): se modela como un factor que crece con 1/ancho del diente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

ALPHA = 1.9                     # exponente de B en las pérdidas por histéresis (aceros NO de grano no orientado)


@dataclass(frozen=True)
class ElectricalSteel:
    name: str
    thickness_mm: float
    density: float              # kg/m³
    p10_50: float               # W/kg a 1.0 T, 50 Hz (catálogo)
    p10_400: float              # W/kg a 1.0 T, 400 Hz (catálogo)
    b_sat: float                # T, donde la permeabilidad cae fuerte (diseño: dientes ≤ ~0.9·b_sat)
    bh: tuple                   # curva B-H: ((H [A/m], B [T]), ...)
    price_usd_kg: float         # chapa (sin corte), compra chica
    note: str = ""

    @property
    def kh(self) -> float:
        return self._coeffs()[0]

    @property
    def ke(self) -> float:
        return self._coeffs()[1]

    def _coeffs(self) -> tuple[float, float]:
        # p = kh·f + ke·f² a 1 T  →  dos ecuaciones con f = 50 y 400 Hz
        f1, f2 = 50.0, 400.0
        ke = (self.p10_400 / f2 - self.p10_50 / f1) / (f2 - f1)
        kh = self.p10_50 / f1 - ke * f1
        return kh, ke

    def loss_w_per_kg(self, b_peak: float, f_hz: float) -> float:
        return self.kh * f_hz * b_peak ** ALPHA + self.ke * (f_hz * b_peak) ** 2

    def permeability(self, b: float) -> float:
        """μr a una inducción B (interpolación de la curva B-H)."""
        hs, bs = zip(*self.bh)
        b = min(b, bs[-1])
        h = float(_interp(b, bs, hs))
        return b / (4e-7 * math.pi * max(h, 1e-6))


def _interp(x, xs, ys):
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


_BH_NO = ((0, 0), (40, 0.5), (70, 1.0), (120, 1.2), (300, 1.4), (1000, 1.55), (3000, 1.65), (10000, 1.8), (50000, 2.0))
_BH_MILD = ((0, 0), (150, 0.5), (300, 1.0), (500, 1.2), (1000, 1.4), (2500, 1.55), (6000, 1.7), (15000, 1.85), (60000, 2.05))

STEELS = {
    "NO20": ElectricalSteel("Acero al silicio no orientado 0.20 mm (clase 20JNEH1200 / B20AT1500)", 0.20, 7650, 0.90, 12.0, 1.70,
                            _BH_NO, 9.0, "el mejor para motores de alta frecuencia; más caro y difícil de conseguir en plancha chica"),
    "NO27": ElectricalSteel("Acero al silicio no orientado 0.27 mm (clase 27JNEH / NO27)", 0.27, 7650, 1.00, 14.5, 1.70,
                            _BH_NO, 6.0, "compromiso entre pérdidas y precio; buena opción para el DS-D (frecuencias más bajas)"),
    "M270-35A": ElectricalSteel("Acero al silicio no orientado 0.35 mm (M270-35A / 35JN270)", 0.35, 7650, 1.10, 17.5, 1.70,
                                _BH_NO, 3.5, "el más común y barato; aceptable en el DS-D, justo en el DS-I"),
    "DC01": ElectricalSteel("Acero común laminado en frío 0.5 mm (DC01 / SPCC), sin silicio", 0.50, 7850, 5.0, 75.0, 1.55,
                            _BH_MILD, 1.2, "NO sirve para el estator (pérdidas 5-7 veces mayores); sí para el yugo del rotor (campo casi fijo)"),
}

LASER_DAMAGE_MM = 0.4           # ancho de borde degradado por el corte con láser de fibra (literatura: 0.3-0.5 mm)
LASER_DAMAGE_FACTOR = 1.6       # pérdidas en esa franja relativas al material sano


def laser_cut_factor(feature_width_mm: float, both_edges: bool = True) -> float:
    """Multiplicador de pérdidas de una pieza de ancho dado (diente, yugo) cortada con láser, sin recocido."""
    damaged = min(feature_width_mm, LASER_DAMAGE_MM * (2 if both_edges else 1))
    return 1 + (LASER_DAMAGE_FACTOR - 1) * damaged / feature_width_mm


@dataclass(frozen=True)
class Magnet:
    grade: str
    br20: float                 # T, remanencia a 20 °C
    hcj20_ka_m: float           # coercitividad intrínseca a 20 °C
    t_max_c: float              # temperatura máxima de trabajo (catálogo)
    alpha_br: float = -0.0012   # 1/K
    beta_hcj: float = -0.0060   # 1/K (aprox., para grados H/SH)
    mu_rec: float = 1.05
    density: float = 7500
    price_usd_kg: float = 90.0  # segmentos de arco, compra chica (se cotiza en S17-05)

    def br(self, t_c: float) -> float:
        return self.br20 * (1 + self.alpha_br * (t_c - 20))

    def hcj(self, t_c: float) -> float:
        return self.hcj20_ka_m * (1 + self.beta_hcj * (t_c - 20))


MAGNETS = {
    "N52H": Magnet("N52H", 1.43, 1353, 120),
    "N48SH": Magnet("N48SH", 1.38, 1592, 150, beta_hcj=-0.0055),
    "N42SH": Magnet("N42SH", 1.30, 1592, 150, beta_hcj=-0.0055, price_usd_kg=75),
    "N52": Magnet("N52 (sin sufijo)", 1.45, 876, 80, beta_hcj=-0.0065, price_usd_kg=80),
}


@dataclass(frozen=True)
class Conductor:
    name: str
    rho20: float                # Ω·m
    alpha: float                # 1/K
    density: float
    t_class_c: float            # clase térmica del esmalte
    price_usd_kg: float

    def rho(self, t_c: float) -> float:
        return self.rho20 * (1 + self.alpha * (t_c - 20))


COPPER = Conductor("Cobre esmaltado clase H (200 °C)", 1.724e-8, 0.00393, 8960, 200, 18.0)


@dataclass(frozen=True)
class Plastic:
    name: str
    density: float
    hdt_c: float                # temperatura de deflexión bajo carga (0.45 MPa)
    tensile_mpa: float          # resistencia a tracción (pieza impresa, dirección débil ≈ 50-70 % de esto)
    price_usd_kg: float


PLASTICS = {
    "PLA": Plastic("PLA", 1240, 55, 50, 20),
    "PETG": Plastic("PETG", 1270, 70, 50, 22),
    "ASA": Plastic("ASA", 1070, 95, 45, 25),
    "PA12-CF": Plastic("PA12 con fibra de carbono", 1150, 150, 70, 70),
    "PC": Plastic("Policarbonato", 1200, 130, 60, 35),
}

ALUMINUM_6061 = {"density": 2700, "yield_mpa": 276, "price_usd_kg": 8.0}
STEEL_SHAFT = {"name": "Eje de acero templado (plata o 4140)", "density": 7850, "yield_mpa": 650}
