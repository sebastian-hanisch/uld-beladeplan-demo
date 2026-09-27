"""Beladeplan über mehrere ULD-Positionen - der exakte Löser (CP-SAT).

Mechanisch aus packen-planung/messreihe_uld_beladeplan/beladeplan.py übernommen, unverändert. `ortools`
wird LAZY importiert (erst beim Aufruf von solve_exact), damit ein Import von uldb_oracle allein (z. B. in
Tests, die nur H_greedy/H_balance brauchen) kein ortools voraussetzt - hier aber ohnehin immer gerechnet
(kein separater Exakt-Tab, siehe app.py: bei 10 Positionen/16 ULDs unter 2 s, siehe ERGEBNIS.md Befund 5)."""
from __future__ import annotations

from uldb_model import Aircraft, ULD, Position, moment_of

SCALE = 100  # kg-Auflösung für CP-SAT (ganzzahlig)
ARM_SCALE = 1000  # mm-Auflösung für den Hebelarm


def solve_exact(ulds: list[ULD], positions: list[Position], ac: Aircraft, time_limit_s: float = 10.0):
    """CP-SAT: 0/1-Zuordnung ULD->Position (höchstens 1 Position je ULD, höchstens 1 ULD je Position),
    Positions-Gewichtsgrenze, Schwerpunkt-Fenster BEIDE Zeitpunkte linearisiert, maximiert geladenes Gewicht."""
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    n, m = len(ulds), len(positions)
    x = {(i, j): model.NewBoolVar(f"x_{i}_{j}") for i in range(n) for j in range(m)}

    for i in range(n):
        model.Add(sum(x[i, j] for j in range(m)) <= 1)
    for j in range(m):
        model.Add(sum(x[i, j] for i in range(n)) <= 1)
        # Positions-Gewichtsgrenze
        model.Add(sum(x[i, j] * int(round(ulds[i].weight_kg * SCALE)) for i in range(n))
                   <= int(round(positions[j].max_weight_kg * SCALE)))

    # Schwerpunkt-Fenster an beiden Zeitpunkten, linearisiert:
    #   cg_min <= (M0 + sum x*w*arm) / (W0 + sum x*w) <= cg_max
    #   <=> sum x*w*(arm - cg_min) >= cg_min*W0 - M0   UND   sum x*w*(cg_max - arm) >= M0 - cg_max*W0
    def add_cg_constraints(W0: float, M0: float):
        lhs_min = sum(x[i, j] * int(round(ulds[i].weight_kg * (positions[j].arm_m - ac.cg_min_m) * ARM_SCALE))
                       for i in range(n) for j in range(m))
        rhs_min = int(round((ac.cg_min_m * W0 - M0) * ARM_SCALE))
        model.Add(lhs_min >= rhs_min)
        lhs_max = sum(x[i, j] * int(round(ulds[i].weight_kg * (ac.cg_max_m - positions[j].arm_m) * ARM_SCALE))
                       for i in range(n) for j in range(m))
        rhs_max = int(round((M0 - ac.cg_max_m * W0) * ARM_SCALE))
        model.Add(lhs_max >= rhs_max)

    W0_full = ac.empty_weight_kg + ac.fuel_kg
    M0_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m)
    add_cg_constraints(W0_full, M0_full)
    W0_empty = ac.empty_weight_kg
    M0_empty = ac.empty_moment_kgm
    add_cg_constraints(W0_empty, M0_empty)

    model.Maximize(sum(x[i, j] * int(round(ulds[i].weight_kg * SCALE)) for i in range(n) for j in range(m)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    assign = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i in range(n):
            for j in range(m):
                if solver.Value(x[i, j]):
                    assign[ulds[i].name] = positions[j].name
    return assign, status, solver
