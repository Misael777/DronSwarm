"""Factores de seguridad centralizados (config/safety_factors.yaml)."""

from functools import cache

import yaml

from . import CONFIG


@cache
def _load() -> dict:
    return yaml.safe_load((CONFIG / "safety_factors.yaml").read_text())


def factor(name: str) -> float:
    """Valor de diseño de un factor; falla si está fuera del rango documentado."""
    f = _load()[name]
    if not f["min"] <= f["design"] <= f["max"]:
        raise ValueError(f"{name}: diseño {f['design']} fuera del rango [{f['min']}, {f['max']}]")
    return float(f["design"])


def all_factors() -> dict[str, float]:
    return {name: factor(name) for name in _load()}


@cache
def design_cases() -> dict:
    return yaml.safe_load((CONFIG / "design_cases.yaml").read_text())
