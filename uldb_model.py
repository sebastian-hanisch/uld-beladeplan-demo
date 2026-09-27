"""Beladeplan über mehrere ULD-Positionen (Weight & Balance) - Datentypen und Bewertung.

Mechanisch aus packen-planung/messreihe_uld_beladeplan/beladeplan.py übernommen (dort bereits gegen 13
Checks verifiziert, siehe ERGEBNIS.md) - Logik unverändert, nur in eigene Module aufgeteilt (uldb_model,
uldb_heuristics, uldb_oracle statt einer Datei).

Geschärfter Hook gegenüber stauplanung-demo (Dopplungsrisiko dort: gewichtete Objekte -> Positionen,
Momentenbilanz, CP-SAT gegen Heuristiken, siehe messreihe_uld_gewicht/ERGEBNIS.md):
  - AUSWAHL statt Vollbelegung: nicht jedes ULD fliegt mit, Ziel ist das geladene Gewicht zu maximieren
    (0/1-Rucksack mit einer Momenten-Nebenbedingung statt Stapel-Sequenz mit Umstau-Minimierung).
  - Envelope an ZWEI Zeitpunkten: Start (voller Tank) UND nach Treibstoffverbrauch (leerer Tank) müssen
    beide im Schwerpunkt-Fenster liegen - eine Facette, die es bei der Schiffs-Stauplanung (ein Zeitpunkt,
    kein Verbrauch während der Fahrt in diesem Sinn) nicht gibt.
  - Keine Sequenz-/Reihenfolge-Dimension: eine einmalige Zuordnung ULD -> Position, kein Umladen unterwegs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    name: str
    arm_m: float       # Hebelarm ab Referenzpunkt (Datum), m
    max_weight_kg: float


@dataclass
class ULD:
    name: str
    weight_kg: float


@dataclass
class Aircraft:
    empty_weight_kg: float
    empty_moment_kgm: float   # empty_weight_kg * empty_arm_m, vorab zusammengefasst
    fuel_kg: float
    fuel_arm_m: float
    cg_min_m: float
    cg_max_m: float


def moment_of(weight_kg: float, arm_m: float) -> float:
    return weight_kg * arm_m


def cg_index(total_weight_kg: float, total_moment_kgm: float) -> float:
    return total_moment_kgm / total_weight_kg if total_weight_kg > 0 else 0.0


def cg_ok(total_weight_kg: float, total_moment_kgm: float, cg_min: float, cg_max: float) -> bool:
    if total_weight_kg <= 0:
        return True
    idx = cg_index(total_weight_kg, total_moment_kgm)
    return cg_min - 1e-9 <= idx <= cg_max + 1e-9


def evaluate_assignment(assign: dict[str, str], ulds: list[ULD], positions: dict[str, Position],
                         ac: Aircraft) -> dict:
    """Bewertet eine Zuordnung {ULD-Name: Positionsname} an BEIDEN Zeitpunkten (voll/leer Tank)."""
    pos_by_name = positions
    used = set()
    cargo_weight = 0.0
    cargo_moment = 0.0
    for u in ulds:
        p = assign.get(u.name)
        if p is None:
            continue
        assert p not in used, f"Position {p} doppelt belegt"
        used.add(p)
        pos = pos_by_name[p]
        cargo_weight += u.weight_kg
        cargo_moment += moment_of(u.weight_kg, pos.arm_m)

    w_full = ac.empty_weight_kg + ac.fuel_kg + cargo_weight
    m_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m) + cargo_moment
    w_empty = ac.empty_weight_kg + cargo_weight
    m_empty = ac.empty_moment_kgm + cargo_moment

    ok_full = cg_ok(w_full, m_full, ac.cg_min_m, ac.cg_max_m)
    ok_empty = cg_ok(w_empty, m_empty, ac.cg_min_m, ac.cg_max_m)
    over_capacity = any(
        sum(u.weight_kg for u in ulds if assign.get(u.name) == p.name) > p.max_weight_kg + 1e-6
        for p in pos_by_name.values()
    )
    return dict(
        cargo_weight=cargo_weight,
        n_loaded=len(used),
        cg_full=cg_index(w_full, m_full) if w_full > 0 else 0.0,
        cg_empty=cg_index(w_empty, m_empty) if w_empty > 0 else 0.0,
        feasible=ok_full and ok_empty and not over_capacity,
        ok_full=ok_full, ok_empty=ok_empty, over_capacity=over_capacity,
    )
