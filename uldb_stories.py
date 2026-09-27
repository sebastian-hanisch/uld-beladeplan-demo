"""Abnahmekriterien der fünf Presets (Detailplan Abschnitt 7) - jedes einzeln gegen die vorgerechnete
Messreihe (data/uldb_results.json) prüfbar, damit ein Preset nie eine Geschichte erzählt, die die Zahlen
nicht tragen."""
from __future__ import annotations

import uldb_constants as C
import uldb_results as R
from uldb_format import fmt_num, fmt_pct


def _cell_for(name: str, data: dict) -> dict:
    p = C.PRESETS[name]
    return R.find_cell(data, p["width"], p["level"], p["n_ulds"])


def check_standard(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Standard", data)
    vio, gap_g, gap_b = cell["violation_rate_greedy_raw"], cell["gap_greedy_pct"], cell["gap_balance_pct"]
    ok = vio >= 0.50 and gap_g >= 5.0 and gap_b <= 1.0
    return ok, (f"Verletzungsrate H_greedy {fmt_pct(vio)} (>= 50 % erwartet), Lücke H_greedy {fmt_num(gap_g, 1)} % "
                f"(>= 5 % erwartet), Lücke H_balance {fmt_num(gap_b, 1)} % (<= 1 % erwartet)")


def check_enges_fenster(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Enges Fenster", data)
    gap_b = cell["gap_balance_pct"]
    ok = gap_b > 0.0
    return ok, f"Lücke H_balance {fmt_num(gap_b, 1)} % (> 0 % erwartet: hier zeigt sich die Grenze der einfachen Regel)"


def check_weites_fenster(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Weites Fenster", data)
    vio = cell["violation_rate_greedy_raw"]
    ok = vio <= 0.10
    return ok, f"Verletzungsrate H_greedy {fmt_pct(vio)} (<= 10 % erwartet: der Unterschied zwischen den Regeln verschwindet fast)"


def check_viele_ulds_wenige_positionen(data: dict) -> tuple[bool, str]:
    """Strukturelle Prüfung statt einer Messung: jede Position nimmt höchstens ein ULD auf (siehe
    uldb_oracle.solve_exact, Nebenbedingung sum_i x[i,j] <= 1), also kann CP-SAT bei 16 ULDs und nur 10
    Positionen NIE mehr als 10 ULDs laden - das Auswahlproblem ist hier keine Messgröße, sondern eine direkte
    Folge des Modells."""
    p = C.PRESETS["Viele ULDs, wenige Positionen"]
    ok = p["n_ulds"] > C.N_POS
    return ok, f"{p['n_ulds']} ULDs, {C.N_POS} Positionen (n_ulds > N_POS erwartet: nicht alle ULDs können mitfliegen)"


def check_extremfall(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Extremfall", data)
    gap_g = cell["gap_greedy_pct"]
    ok = gap_g >= 40.0
    return ok, f"Lücke H_greedy {fmt_num(gap_g, 1)} % (>= 40 % erwartet: größter gemessener wirtschaftlicher Preis der naiven Regel)"


CHECKS = {
    "Standard": check_standard,
    "Enges Fenster": check_enges_fenster,
    "Weites Fenster": check_weites_fenster,
    "Viele ULDs, wenige Positionen": check_viele_ulds_wenige_positionen,
    "Extremfall": check_extremfall,
}


def check_all(data: dict) -> dict[str, tuple[bool, str]]:
    return {name: fn(data) for name, fn in CHECKS.items()}
