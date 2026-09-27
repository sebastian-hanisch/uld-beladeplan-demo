"""Zahlenformate mit deutschem Dezimalkomma (wie in den anderen Fall-Demos, z. B. uldg_format.py)."""


def fmt_num(v: float, digits: int = 1, signed: bool = False) -> str:
    text = f"{v:+.{digits}f}" if signed else f"{v:.{digits}f}"
    return text.replace(".", ",")


def fmt_pct(v: float, digits: int = 1, signed: bool = False) -> str:
    """Anteil (0..1) als Prozentzahl mit Dezimalkomma: 0.745 -> '74,5 %'."""
    return f"{fmt_num(100.0 * v, digits, signed)} %"


def fmt_pp(v: float, digits: int = 1, signed: bool = True) -> str:
    """Bereits in Prozentpunkten vorliegender Wert (z. B. eine Lücke in Prozent des Zielwerts)."""
    return f"{fmt_num(v, digits, signed)} Prozentpunkte"
