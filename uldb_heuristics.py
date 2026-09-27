"""Beladeplan über mehrere ULD-Positionen - die zwei Heuristiken und die Reparatur.

Mechanisch aus packen-planung/messreihe_uld_beladeplan/beladeplan.py übernommen, unverändert (siehe
uldb_model.py für die Herkunft und den geschärften Hook gegenüber stauplanung-demo)."""
from __future__ import annotations

from uldb_model import Aircraft, ULD, Position, cg_index, evaluate_assignment, moment_of


def heuristic_greedy(ulds: list[ULD], positions: list[Position], ac: Aircraft) -> dict[str, str]:
    """H_greedy: schwerste ULDs zuerst, jeweils die erste freie Position mit ausreichender Gewichtsgrenze,
    committet ohne Rückblick - prüft die Schwerpunkt-Fenster erst am Ende (typischer myopischer Fehler)."""
    order = sorted(ulds, key=lambda u: -u.weight_kg)
    free = list(positions)
    assign: dict[str, str] = {}
    for u in order:
        for p in list(free):
            if p.max_weight_kg >= u.weight_kg:
                assign[u.name] = p.name
                free.remove(p)
                break
    return assign


def heuristic_balance(ulds: list[ULD], positions: list[Position], ac: Aircraft) -> dict[str, str]:
    """H_balance: schwerste ULDs zuerst, aber jeweils die freie Position, die den Schwerpunkt (Leergewicht-
    Zustand) am nächsten an die Fenstermitte bringt - eine gängige praktische Beladestrategie (Ausgleich
    fwd/aft statt vorne beginnend)."""
    order = sorted(ulds, key=lambda u: -u.weight_kg)
    free = list(positions)
    assign: dict[str, str] = {}
    target = (ac.cg_min_m + ac.cg_max_m) / 2.0
    cur_w = ac.empty_weight_kg
    cur_m = ac.empty_moment_kgm
    for u in order:
        best = None
        best_dist = None
        for p in free:
            if p.max_weight_kg < u.weight_kg:
                continue
            new_w = cur_w + u.weight_kg
            new_m = cur_m + moment_of(u.weight_kg, p.arm_m)
            idx = cg_index(new_w, new_m)
            dist = abs(idx - target)
            if best is None or dist < best_dist:
                best, best_dist = p, dist
        if best is not None:
            assign[u.name] = best.name
            free.remove(best)
            cur_w += u.weight_kg
            cur_m += moment_of(u.weight_kg, best.arm_m)
    return assign


def repair_to_feasible(assign: dict[str, str], ulds: list[ULD], positions: dict[str, Position],
                        ac: Aircraft) -> dict[str, str]:
    """Entfernt aus einer (möglicherweise unzulässigen) Zuordnung so lange die ULDs mit dem größten
    Hebel-Abstand zur Fenstermitte (im Leergewicht-Zustand), bis beide Zeitpunkte zulässig sind. Bildet
    nach, was ein Lademeister tut, wenn ein Plan die Grenzen reißt: etwas rausnehmen, nicht neu rechnen."""
    assign = dict(assign)
    uld_by_name = {u.name: u for u in ulds}
    target = (ac.cg_min_m + ac.cg_max_m) / 2.0
    guard = 0
    while guard < len(ulds) + 1:
        ev = evaluate_assignment(assign, ulds, positions, ac)
        if ev["feasible"]:
            return assign
        if not assign:
            return assign
        worst = max(assign, key=lambda n: abs(positions[assign[n]].arm_m - target) * uld_by_name[n].weight_kg)
        del assign[worst]
        guard += 1
    return assign
