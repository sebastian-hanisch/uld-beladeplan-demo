"""Reproduktion der Vorab-Messreihe (Detailplan AP 0/7): derselbe Sweep wie
packen-planung/messreihe_uld_beladeplan/sweep.py, hier gegen die aufgeteilten Module uldb_model/uldb_heuristics/
uldb_oracle. Schreibt data/uldb_results.json (nicht Teil der CI - Laufzeit rund 70-90 s). Vorlage für
tools/check_full.py: dort wird dieselbe Rechnung gegen die eingecheckte Datei geprüft (AP 7, Bau-Gate).

Die Zellen-Seeds kommen bewusst mechanisch unverändert aus `zlib.crc32(repr(parts).encode("utf-8"))` (wie im
Original messreihe_uld_beladeplan/sweep.py) - NICHT Pythons eingebautes hash() auf Tupeln/Strings, das ist
seit PEP 456 pro Prozess zufällig gesalzen (PYTHONHASHSEED) und macht einen Sweep nicht reproduzierbar, obwohl
er wie deterministisch aussieht (beim Bau von uld-gewicht-demo gefunden). Mit crc32 ist dieser Sweep über
verschiedene Prozesse und Python-Versionen hinweg BITGLEICH reproduzierbar - tools/check_full.py prüft das
auch tatsächlich so, nicht nur statistisch."""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uldb_constants import ARM_MAX, ARM_MIN, CENTER_M, EMPTY_WEIGHT_KG, FUEL_KG, N_POS, POS_MAX_WEIGHT_KG, WEIGHT_LEVELS  # noqa: E402
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible  # noqa: E402
from uldb_model import Aircraft, ULD, Position, evaluate_assignment  # noqa: E402
from uldb_oracle import solve_exact  # noqa: E402

POSITIONS = [Position(f"p{i}", ARM_MIN + i * (ARM_MAX - ARM_MIN) / (N_POS - 1), POS_MAX_WEIGHT_KG) for i in range(N_POS)]
POS_BY_NAME = {p.name: p for p in POSITIONS}

N_ULDS = [8, 12, 16]
WIDTHS = [1.0, 0.5, 0.3, 0.15, 0.08]
N_INSTANCES = 80
TIME_LIMIT = 2.0


def cell_seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode("utf-8")) % (2**31)


def run_sweep():
    rows = []
    for width in WIDTHS:
        ac = Aircraft(EMPTY_WEIGHT_KG, EMPTY_WEIGHT_KG * CENTER_M, FUEL_KG, CENTER_M, CENTER_M - width, CENTER_M + width)
        for level, (lo, hi) in WEIGHT_LEVELS.items():
            for n in N_ULDS:
                rng = np.random.default_rng(cell_seed(width, level, n))
                n_vio_greedy_raw = n_vio_balance_raw = 0
                n_only_full_bad = n_only_empty_bad = 0
                w_greedy_rep, w_balance_rep, w_exact = [], [], []
                n_exact_optimal = 0
                for _ in range(N_INSTANCES):
                    ulds = [ULD(f"u{i}", float(rng.uniform(lo, hi))) for i in range(n)]
                    g_raw = heuristic_greedy(ulds, POSITIONS, ac)
                    ev_g_raw = evaluate_assignment(g_raw, ulds, POS_BY_NAME, ac)
                    n_vio_greedy_raw += not ev_g_raw["feasible"]
                    if ev_g_raw["ok_full"] != ev_g_raw["ok_empty"]:
                        n_only_full_bad += not ev_g_raw["ok_full"]
                        n_only_empty_bad += not ev_g_raw["ok_empty"]

                    b_raw = heuristic_balance(ulds, POSITIONS, ac)
                    ev_b_raw = evaluate_assignment(b_raw, ulds, POS_BY_NAME, ac)
                    n_vio_balance_raw += not ev_b_raw["feasible"]

                    g_rep = repair_to_feasible(g_raw, ulds, POS_BY_NAME, ac)
                    w_greedy_rep.append(evaluate_assignment(g_rep, ulds, POS_BY_NAME, ac)["cargo_weight"])
                    b_rep = repair_to_feasible(b_raw, ulds, POS_BY_NAME, ac)
                    w_balance_rep.append(evaluate_assignment(b_rep, ulds, POS_BY_NAME, ac)["cargo_weight"])

                    cp_assign, status, _ = solve_exact(ulds, POSITIONS, ac, time_limit_s=TIME_LIMIT)
                    ev_cp = evaluate_assignment(cp_assign, ulds, POS_BY_NAME, ac)
                    w_exact.append(ev_cp["cargo_weight"])
                    n_exact_optimal += status == 4  # cp_model.OPTIMAL == 4

                w_greedy_rep = np.array(w_greedy_rep)
                w_balance_rep = np.array(w_balance_rep)
                w_exact = np.array(w_exact)
                rows.append(dict(
                    width=width, level=level, n_ulds=n,
                    violation_rate_greedy_raw=n_vio_greedy_raw / N_INSTANCES,
                    violation_rate_balance_raw=n_vio_balance_raw / N_INSTANCES,
                    only_full_bad_rate=n_only_full_bad / N_INSTANCES,
                    only_empty_bad_rate=n_only_empty_bad / N_INSTANCES,
                    mean_w_greedy_rep=float(w_greedy_rep.mean()),
                    mean_w_balance_rep=float(w_balance_rep.mean()),
                    mean_w_exact=float(w_exact.mean()),
                    gap_greedy_pct=float(100 * (w_exact - w_greedy_rep).mean() / w_exact.mean()),
                    gap_balance_pct=float(100 * (w_exact - w_balance_rep).mean() / w_exact.mean()),
                    gap_greedy_se=float(100 * (w_exact - w_greedy_rep).std(ddof=1) / np.sqrt(N_INSTANCES) / w_exact.mean()),
                    gap_balance_se=float(100 * (w_exact - w_balance_rep).std(ddof=1) / np.sqrt(N_INSTANCES) / w_exact.mean()),
                    exact_optimal_rate=n_exact_optimal / N_INSTANCES,
                ))
    return dict(n_pos=N_POS, arm_min=ARM_MIN, arm_max=ARM_MAX, center=CENTER_M, n_instances=N_INSTANCES,
                empty_weight_kg=EMPTY_WEIGHT_KG, fuel_kg=FUEL_KG, rows=rows)


def main():
    t0 = time.time()
    out = run_sweep()
    out_path = ROOT / "data" / "uldb_results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out['rows'])} Zellen, {len(out['rows']) * N_INSTANCES} Instanzen, {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
