"""Beladeplan über mehrere ULD-Positionen - Laden und Auswerten der vorgerechneten Messreihe
(data/uldb_results.json, 45 Zellen x 80 Instanzen, aus packen-planung/messreihe_uld_beladeplan/sweep.py,
bitgleich als data/uldb_results.json übernommen, siehe tools/sweep.py und tools/check_full.py).

Die drei Regler (Fensterbreite, ULD-Zahl, Gewichtsniveau) bilden genau die drei Sweep-Dimensionen ab
(AP 0 bestätigt: alle 45 Kombinationen liegen exakt auf einer gemessenen Zelle, siehe
tests/test_results.py::test_alle_reglerkombinationen_liegen_auf_einer_gemessenen_zelle) - `find_cell` ist
deshalb ein exakter Treffer, keine Näherung auf die nächstliegende Zelle."""
from __future__ import annotations

import functools
import json
import pathlib

from uldb_format import fmt_num, fmt_pct

DATA_PATH = pathlib.Path(__file__).parent / "data" / "uldb_results.json"

WIDTH_OPTIONS = (1.0, 0.5, 0.3, 0.15, 0.08)
LEVEL_OPTIONS = ("leicht", "gemischt", "schwer")
ULDS_OPTIONS = (8, 12, 16)

# Urteilsschwellen (Kernabschnitt, drei Zustände wie im Detailplan Abschnitt 6 vorgesehen). Mit 80 Instanzen
# je Zelle liegt die Stichprobenstreuung einer Anteilsschätzung (Standardfehler sqrt(p(1-p)/80)) bei
# höchstens rund 5,6 Prozentpunkten; die gemessene Verletzungsrate springt zwischen 3,75 % und 18,75 % (siehe
# tests/test_results.py), die Schwelle unten liegt sauber dazwischen.
UNKRITISCH_VIO_GREEDY_MAX = 0.15   # H_greedy verletzt ohnehin selten: die Enge des Fensters ist in dieser Zelle kaum ein Thema
# gap_balance_pct ist über 42 von 45 Zellen exakt 0,0 % (Nullspalten-Signal, deshalb stressgetestet, siehe
# ERGEBNIS.md Befund 3) und springt in den drei betroffenen Zellen auf 0,22 / 1,47 / 2,38 %. Die Schwelle
# 0,5 Prozentpunkte trennt die eine kleine, an der Stichprobenstreuung nicht signifikante Abweichung (0,22 %,
# Standardfehler ebenfalls 0,22 %) sauber von den beiden echten, mit deutlichem Abstand zu ihrem eigenen
# Standardfehler gemessenen Lücken (1,47 % bei Standardfehler 0,76 %, 2,38 % bei Standardfehler 1,14 %).
DEUTLICHE_LUECKE_MIN_GAP_PP = 0.5

STATE_UNKRITISCH = "unkritisch"
STATE_OPTIMAL = "optimal"
STATE_LUECKE = "luecke"

STATE_LABEL = {
    STATE_UNKRITISCH: "Fenster ohnehin unkritisch",
    STATE_OPTIMAL: "Balance-Regel praktisch optimal",
    STATE_LUECKE: "Balance-Regel hat hier eine Lücke",
}


@functools.lru_cache(maxsize=1)
def load_results(path: pathlib.Path | None = None) -> dict:
    p = path or DATA_PATH
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def cells(data: dict) -> list[dict]:
    return data["rows"]


def find_cell(data: dict, width: float, level: str, n_ulds: int) -> dict:
    """Exakter Treffer (AP 0: die Reglerstufen SIND die gemessenen Zellen)."""
    for r in cells(data):
        if abs(r["width"] - width) < 1e-9 and r["level"] == level and r["n_ulds"] == n_ulds:
            return r
    raise KeyError((width, level, n_ulds))


def judgment(cell: dict) -> str:
    """Drei Zustände (Kernabschnitt, Detailplan Abschnitt 6). Eine Zelle mit seltener Verletzung durch
    H_greedy zählt als "ohnehin unkritisch", unabhängig von der Balance-Lücke - die Fensterbreite ist dort
    schlicht kein Thema."""
    if cell["violation_rate_greedy_raw"] < UNKRITISCH_VIO_GREEDY_MAX:
        return STATE_UNKRITISCH
    if cell["gap_balance_pct"] >= DEUTLICHE_LUECKE_MIN_GAP_PP:
        return STATE_LUECKE
    return STATE_OPTIMAL


def judgment_text(cell: dict) -> str:
    state = judgment(cell)
    vio_g = fmt_pct(cell["violation_rate_greedy_raw"])
    gap_b = fmt_num(cell["gap_balance_pct"], 1)
    if state == STATE_UNKRITISCH:
        return f"{STATE_LABEL[state]}: H_greedy verletzt das Fenster hier ohnehin nur in {vio_g} der Instanzen."
    if state == STATE_OPTIMAL:
        return f"{STATE_LABEL[state]}: H_greedy verletzt in {vio_g} der Instanzen, H_balance (repariert) hat dennoch nur {gap_b} % Lücke zum CP-SAT-Optimum."
    return f"{STATE_LABEL[state]}: selbst H_balance (repariert) hat hier {gap_b} % Lücke zum CP-SAT-Optimum - bei sehr engem Fenster reicht die einfache Regel nicht mehr."


def regime_rows(data: dict) -> list[dict]:
    """Alle 45 Zellen mit Urteil, für die Regime-Tabelle."""
    out = []
    for c in cells(data):
        out.append({
            "width": c["width"], "level": c["level"], "n_ulds": c["n_ulds"],
            "violation_greedy": c["violation_rate_greedy_raw"], "violation_balance": c["violation_rate_balance_raw"],
            "gap_greedy": c["gap_greedy_pct"], "gap_balance": c["gap_balance_pct"],
            "only_empty_bad": c["only_empty_bad_rate"], "only_full_bad": c["only_full_bad_rate"],
            "state": judgment(c), "label": STATE_LABEL[judgment(c)],
        })
    return out


def width_rows(data: dict, level: str, n_ulds: int) -> list[dict]:
    """Lücke H_greedy gegen H_balance über die Fensterbreite (für die Kerngrafik), feste Gewichtsniveau/ULD-Zahl."""
    return [find_cell(data, w, level, n_ulds) for w in WIDTH_OPTIONS]


def only_empty_summary(data: dict) -> dict:
    """Zwei-Zeitpunkte-Effekt: Anteil der Instanzen, die nur am leeren bzw. nur am vollen Tank verletzt
    wären, über alle 45 Zellen (ERGEBNIS.md Befund 4)."""
    only_empty = [c["only_empty_bad_rate"] for c in cells(data)]
    only_full = [c["only_full_bad_rate"] for c in cells(data)]
    max_cell = max(cells(data), key=lambda c: c["only_empty_bad_rate"])
    return {
        "mean_only_empty": sum(only_empty) / len(only_empty),
        "mean_only_full": sum(only_full) / len(only_full),
        "max_only_empty": max_cell["only_empty_bad_rate"],
        "max_only_empty_cell": max_cell,
    }


def gap_balance_summary(data: dict) -> dict:
    """ERGEBNIS.md Befund 3: wie oft und wie stark H_balance (repariert) selbst eine Lücke zum Optimum hat."""
    rows = cells(data)
    n_zero = sum(1 for c in rows if abs(c["gap_balance_pct"]) < 1e-9)
    max_cell = max(rows, key=lambda c: c["gap_balance_pct"])
    return {"n_zero": n_zero, "n_total": len(rows), "max_gap": max_cell["gap_balance_pct"], "max_cell": max_cell}


def max_gap_greedy(data: dict) -> dict:
    return max(cells(data), key=lambda c: c["gap_greedy_pct"])
