"""Unabhängiges Orakel für den Beladeplan: eigene Bewertung und Vollaufzählung statt evaluate_assignment und CP-SAT.

(1) Auf zufälligen Mini-Instanzen (2-5 Positionen mit verschiedenen Armen und Gewichtsgrenzen, bis 5 ULDs, auch Treibstoff mit anderem Hebelarm, auch unlösbare Fenster) ist das CP-SAT-Optimum
gleich dem Optimum der Aufzählung ALLER injektiven Teilzuordnungen, und evaluate_assignment stimmt mit einer eigenen Rechnung des Schwerpunkts an beiden Zeitpunkten überein.
(2) Auf zufälligen Instanzen mit 10 Positionen (5-6 ULDs: auch gegen die Aufzählung, 8/12/16 ULDs wie in der Messreihe: nur Neuimplementierung) stimmen H_greedy, H_balance und die Reparatur mit einer eigenen Neuimplementierung überein; nach der
Reparatur ist die Zuordnung zulässig und nie schwerer als das Optimum der Aufzählung (Teilmengen nach absteigendem Gewicht, numpy über alle Positionsfolgen)."""

import itertools
import random

import numpy as np
import pytest

import uldb_constants as C
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import ULD, Aircraft, Position, evaluate_assignment

TOL = 1e-9


def _own_eval(ws, arms, caps, ac, assign):
    """assign: {uld_index: position_index}; Schwerpunkt an beiden Zeitpunkten und Positionsgrenzen von Hand."""
    weight = sum(ws[i] for i in assign)
    moment = sum(ws[i] * arms[j] for i, j in assign.items())
    full = (ac.empty_moment_kgm + ac.fuel_kg * ac.fuel_arm_m + moment) / (ac.empty_weight_kg + ac.fuel_kg + weight)
    empty = (ac.empty_moment_kgm + moment) / (ac.empty_weight_kg + weight)
    inside = all(ac.cg_min_m - TOL <= v <= ac.cg_max_m + TOL for v in (full, empty))
    return inside and all(ws[i] <= caps[j] + 1e-6 for i, j in assign.items()), weight, full, empty


def _brute_force(ws, arms, caps, ac):
    """Maximales zulässiges Ladegewicht (None, wenn selbst die leere Zuordnung unzulässig ist) durch Aufzählung aller injektiven Teilzuordnungen."""
    best = None
    for k in range(len(ws) + 1):
        for subset in itertools.combinations(range(len(ws)), k):
            for places in itertools.permutations(range(len(arms)), k):
                ok, weight, _f, _e = _own_eval(ws, arms, caps, ac, dict(zip(subset, places)))
                if ok and (best is None or weight > best):
                    best = weight
    return best


def test_cp_sat_optimum_and_evaluation_agree_with_brute_force_on_mini_instances():
    pytest.importorskip("ortools")
    from uldb_oracle import solve_exact
    rng = random.Random(11)
    feasible = infeasible = 0
    for _ in range(70):
        n_pos, n_uld = rng.randint(2, 5), rng.randint(1, 5)
        arms = sorted(round(rng.uniform(4, 30), 2) for _ in range(n_pos))
        caps = [float(rng.choice([800, 1500, 2000, 2200])) for _ in range(n_pos)]
        ws = [float(rng.choice([rng.randint(100, 2200), round(rng.uniform(100, 2200), 1)])) for _ in range(n_uld)]
        arm0 = rng.choice([15.0, 17.0, 18.5])
        width = rng.choice([0.05, 0.2, 0.5, 1.0, 2.5])
        ac = Aircraft(40000.0, 40000.0 * arm0, rng.choice([0.0, 4000.0, 8000.0]), rng.choice([arm0, 14.0, 20.0, 25.0]), arm0 - width, arm0 + width)
        positions = [Position(f"p{i}", arms[i], caps[i]) for i in range(n_pos)]
        ulds = [ULD(f"u{i}", w) for i, w in enumerate(ws)]
        by_name = {p.name: p for p in positions}
        best = _brute_force(ws, arms, caps, ac)
        assign, status, _ = solve_exact(ulds, positions, ac, time_limit_s=5.0)
        ev = evaluate_assignment(assign, ulds, by_name, ac)
        if best is None:
            infeasible += 1
            assert int(status) == 3                                                   # INFEASIBLE: auch die leere Ladung liegt außerhalb und keine Ladung holt sie zurück
        else:
            feasible += 1
            assert ev["feasible"] and ev["cargo_weight"] == pytest.approx(best, abs=0.05)
        for _ in range(3):                                                            # evaluate_assignment gegen die eigene Rechnung auf Zufallszuordnungen
            k = rng.randint(0, min(n_uld, n_pos))
            a_idx = dict(zip(rng.sample(range(n_uld), k), rng.sample(range(n_pos), k)))
            ok, weight, full, empty = _own_eval(ws, arms, caps, ac, a_idx)
            e = evaluate_assignment({f"u{i}": f"p{j}" for i, j in a_idx.items()}, ulds, by_name, ac)
            assert e["feasible"] == ok and e["cargo_weight"] == pytest.approx(weight) and e["cg_full"] == pytest.approx(full, abs=1e-9) and e["cg_empty"] == pytest.approx(empty, abs=1e-9)
    assert feasible >= 40 and infeasible >= 3


def _own_greedy(ws):
    free, a = list(range(C.N_POS)), {}
    for i in sorted(range(len(ws)), key=lambda i: (-ws[i], i)):
        for j in free:
            if C.POS_MAX_WEIGHT_KG >= ws[i]:
                a[i] = j
                free.remove(j)
                break
    return a


def _own_balance(ws, ac):
    arms = [p.arm_m for p in C.POSITIONS]
    free, a, tot_w, tot_m, target = list(range(C.N_POS)), {}, ac.empty_weight_kg, ac.empty_moment_kgm, (ac.cg_min_m + ac.cg_max_m) / 2
    for i in sorted(range(len(ws)), key=lambda i: (-ws[i], i)):
        if not free:
            break
        best = min(free, key=lambda j: (abs((tot_m + ws[i] * arms[j]) / (tot_w + ws[i]) - target), free.index(j)))
        a[i] = best
        free.remove(best)
        tot_w, tot_m = tot_w + ws[i], tot_m + ws[i] * arms[best]
    return a


def _own_repair(ws, a, ac):
    arms, a = [p.arm_m for p in C.POSITIONS], dict(a)
    caps = [C.POS_MAX_WEIGHT_KG] * C.N_POS
    target = (ac.cg_min_m + ac.cg_max_m) / 2
    while a and not _own_eval(ws, arms, caps, ac, a)[0]:
        del a[max(a, key=lambda i: abs(arms[a[i]] - target) * ws[i])]
    return a


def _best_by_enumeration(ws, ac):
    """Teilmengen nach absteigendem Gewicht; die erste, für die irgendeine Positionsfolge beide Fenster einhält, ist das Optimum."""
    arms = np.array([p.arm_m for p in C.POSITIONS])
    w = np.array(ws)
    masks = np.arange(1 << len(ws))
    bits = ((masks[:, None] >> np.arange(len(ws))) & 1).astype(bool)
    totals = bits @ w
    for mi in np.argsort(-totals, kind="stable"):
        k = int(bits[mi].sum())
        if k > C.N_POS:
            continue
        sel = w[bits[mi]]
        lo = max(ac.cg_min_m * (t0 + totals[mi]) - m0 for t0, m0 in ((ac.empty_weight_kg + ac.fuel_kg, ac.empty_moment_kgm + ac.fuel_kg * ac.fuel_arm_m), (ac.empty_weight_kg, ac.empty_moment_kgm)))
        hi = min(ac.cg_max_m * (t0 + totals[mi]) - m0 for t0, m0 in ((ac.empty_weight_kg + ac.fuel_kg, ac.empty_moment_kgm + ac.fuel_kg * ac.fuel_arm_m), (ac.empty_weight_kg, ac.empty_moment_kgm)))
        if k == 0:
            return 0.0
        if hi < float(np.sort(sel)[::-1] @ np.sort(arms)[:k]) - 1e-9 or lo > float(np.sort(sel)[::-1] @ np.sort(arms)[::-1][:k]) + 1e-9:
            continue
        perms = np.array(list(itertools.permutations(range(C.N_POS), k)), dtype=np.intp)
        moments = arms[perms] @ sel
        if ((moments >= lo) & (moments <= hi)).any():
            return float(totals[mi])
    return 0.0


def test_heuristics_repair_and_enumerated_optimum_on_instances_like_the_measurement():
    rng = np.random.default_rng(3)
    for width, n_ulds, level in ((0.08, 5, "gemischt"), (0.08, 6, "leicht"), (0.15, 6, "gemischt"), (0.5, 6, "schwer"), (0.08, 12, "gemischt"), (0.3, 16, "gemischt"), (0.5, 8, "gemischt"), (1.0, 16, "schwer")):
        ac = C.make_aircraft(width)
        lo_w, hi_w = C.WEIGHT_LEVELS[level]
        for _ in range(6):
            ws = [float(rng.uniform(lo_w, hi_w)) for _ in range(n_ulds)]
            ulds = [ULD(f"u{i}", w) for i, w in enumerate(ws)]
            conv = lambda d: {int(k[1:]): int(v[1:]) for k, v in d.items()}
            greedy, balance = heuristic_greedy(ulds, C.POSITIONS, ac), heuristic_balance(ulds, C.POSITIONS, ac)
            assert conv(greedy) == _own_greedy(ws) and conv(balance) == _own_balance(ws, ac)
            for raw in (greedy, balance):
                rep = repair_to_feasible(raw, ulds, C.POS_BY_NAME, ac)
                assert conv(rep) == _own_repair(ws, conv(raw), ac)
                assert evaluate_assignment(rep, ulds, C.POS_BY_NAME, ac)["feasible"]
            if n_ulds <= 6:                                                            # Aufzählung aller Positionsfolgen nur dort, wo sie schnell fertig ist
                best = _best_by_enumeration(ws, ac)
                for raw in (greedy, balance):
                    assert evaluate_assignment(repair_to_feasible(raw, ulds, C.POS_BY_NAME, ac), ulds, C.POS_BY_NAME, ac)["cargo_weight"] <= best + 1e-6
                pytest.importorskip("ortools")
                from uldb_oracle import solve_exact
                cp, _status, _ = solve_exact(ulds, C.POSITIONS, ac, time_limit_s=5.0)
                assert evaluate_assignment(cp, ulds, C.POS_BY_NAME, ac)["cargo_weight"] == pytest.approx(best, abs=0.05)


def test_only_the_full_tank_violated_is_impossible_with_neutral_fuel():
    """Der Beleg der strukturellen Aussage: bei neutralem Treibstoff liegt der Index ohne Ladung beider Zeitpunkte auf der Fenstermitte, |cg_voll - Mitte| <= |cg_leer - Mitte|."""
    rng = random.Random(5)
    for _ in range(3000):
        ac = C.make_aircraft(rng.choice(C.WIDTH_OPTIONS))
        weight, moment = rng.uniform(0, 20000), rng.uniform(-400000, 400000)                       # beliebiges Ladungsgewicht und Ladungsmoment um die Mitte
        dev_full = abs(moment / (ac.empty_weight_kg + ac.fuel_kg + weight))
        dev_empty = abs(moment / (ac.empty_weight_kg + weight))
        assert dev_full <= dev_empty + 1e-12
