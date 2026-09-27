"""Die 13 Korrektheits-Checks aus packen-planung/messreihe_uld_beladeplan/check.py als pytest, plus der
PFLICHT-Zwei-Zeitpunkte-Regressionstest (Detailplan Abschnitt 11): eine konstruierte Instanz, bei der die
Zuordnung am VOLLEN Tank zulässig, am LEEREN Tank aber unzulässig ist.

Warum nicht "oder umgekehrt": in diesem Modell ist Treibstoff neutral (fuel_arm_m == empty_arm_m), deshalb
liegt der Schwerpunkt-Index OHNE Ladung an beiden Zeitpunkten exakt auf der Fenstermitte (17,0 m) - siehe
test_nur_voll_verletzt_ist_strukturell_unmoeglich unten für die Herleitung und den empirischen Beleg
(only_full_bad_rate == 0,0 in allen 45 gemessenen Zellen, siehe data/uldb_results.json). Die konstruierbare
Richtung (voll zulässig, leer unzulässig) ist deshalb die einzig mögliche - und genau die, die ERGEBNIS.md
Befund 4 beschreibt."""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import Aircraft, ULD, Position, cg_index, cg_ok, evaluate_assignment, moment_of
from uldb_oracle import solve_exact
from uldb_results import load_results


def brute_force_best(ulds, positions, ac):
    """Unabhängige Referenz: enumeriert ALLE injektiven Teilzuordnungen ULD->Position (nur für kleine
    Instanzen), prüft evaluate_assignment, gibt das maximale zulässige Gesamtgewicht."""
    best_w = -1.0
    best_assign = None
    names_u = [u.name for u in ulds]
    names_p = [p.name for p in positions]
    pos_by_name = {p.name: p for p in positions}
    for k in range(0, len(ulds) + 1):
        for u_subset in itertools.combinations(range(len(ulds)), k):
            for p_perm in itertools.permutations(names_p, k):
                assign = {names_u[u_subset[i]]: p_perm[i] for i in range(k)}
                ev = evaluate_assignment(assign, ulds, pos_by_name, ac)
                if ev["feasible"] and ev["cargo_weight"] > best_w:
                    best_w, best_assign = ev["cargo_weight"], assign
    return best_w, best_assign


AC = Aircraft(empty_weight_kg=40000, empty_moment_kgm=40000 * 17.0, fuel_kg=8000, fuel_arm_m=16.0,
              cg_min_m=16.0, cg_max_m=18.0)
POS = [
    Position("fwd1", 10.0, 2000), Position("fwd2", 12.0, 2000),
    Position("aft1", 22.0, 2000), Position("aft2", 24.0, 2000),
]
POS_BY_NAME = {p.name: p for p in POS}


# --- 1. Handrechnung ------------------------------------------------------------------------------------
def test_check01_handrechnung_cg_index():
    w_empty = AC.empty_weight_kg + 2000
    m_empty = AC.empty_moment_kgm + moment_of(1000, 12.0) + moment_of(1000, 22.0)
    idx_hand = m_empty / w_empty
    assert cg_index(w_empty, m_empty) == pytest.approx(idx_hand, abs=1e-9)


# --- 2-4. Grenzfälle cg_ok() ----------------------------------------------------------------------------
def test_check02_cg_ok_grenze_exakt_getroffen_ist_zulaessig():
    assert cg_ok(1000.0, 1000.0 * 16.0, 16.0, 18.0)


def test_check02b_cg_ok_obere_grenze_exakt_getroffen_ist_zulaessig():
    """Symmetrische Ergänzung zu check02 (nur die untere Grenze getestet)."""
    assert cg_ok(1000.0, 1000.0 * 18.0, 16.0, 18.0)


def test_check02c_cg_ok_epsilon_grenzen_sind_beidseitig_zulaessig():
    """Schließt eine Testlücke, die der Fehler-Einbau-Test (tools/mutation_check.py) aufgedeckt hat: check02
    testet idx == cg_min exakt, das liegt aber klar INNERHALB der Toleranz cg_min - 1e-9, egal ob der
    Vergleich <= oder < ist (1e-9 ist keine reale Modellgrenze, sondern eine reine Rundungstoleranz). Erst ein
    idx exakt AUF der Toleranzgrenze selbst unterscheidet <= von <."""
    assert cg_ok(1.0, 16.0 - 1e-9, 16.0, 18.0)
    assert cg_ok(1.0, 18.0 + 1e-9, 16.0, 18.0)


def test_check03_cg_ok_knapp_ueber_oberer_grenze_ist_unzulaessig():
    assert not cg_ok(1000.0, 1000.0 * 18.001, 16.0, 18.0)


def test_check04_cg_ok_gesamtgewicht_null_ist_immer_zulaessig():
    assert cg_ok(0.0, 0.0, 16.0, 18.0)


def test_cg_index_von_gewicht_null_ist_null_ohne_division_durch_null():
    """cg_index() wird in evaluate_assignment nie mit Gewicht 0 aufgerufen (dort vorher abgefangen), aber die
    Funktion selbst muss trotzdem robust sein - direkter Aufruf, kein Umweg über evaluate_assignment."""
    assert cg_index(0.0, 0.0) == 0.0


# --- 5. evaluate_assignment: leere Zuordnung ------------------------------------------------------------
def test_check05_leere_zuordnung_laedt_nichts():
    ev0 = evaluate_assignment({}, [], POS_BY_NAME, AC)
    assert ev0["cargo_weight"] == 0.0 and ev0["n_loaded"] == 0


# --- 6. Positions-Gewichtsgrenze -------------------------------------------------------------------------
def test_check06_positions_gewichtsgrenze_wird_erkannt():
    u_heavy = ULD("H", 3000)  # > max_weight_kg der Position (2000)
    ev_over = evaluate_assignment({"H": "fwd1"}, [u_heavy], POS_BY_NAME, AC)
    assert ev_over["over_capacity"] and not ev_over["feasible"]


def test_check06b_gewicht_exakt_an_der_grenze_ist_nicht_over_capacity():
    u_exact = ULD("E", 2000.0)  # == max_weight_kg der Position (2000), nicht darüber
    ev_exact = evaluate_assignment({"E": "fwd1"}, [u_exact], POS_BY_NAME, AC)
    assert not ev_exact["over_capacity"]


# --- 7-8. Brute-Force gegen CP-SAT ------------------------------------------------------------------------
def test_check07_cp_sat_optimum_gleich_brute_force_optimum():
    ulds_small = [ULD("A", 1200), ULD("B", 900), ULD("C", 1500), ULD("D", 700), ULD("E", 1100)]
    bf_w, _ = brute_force_best(ulds_small, POS, AC)
    cp_assign, _, _ = solve_exact(ulds_small, POS, AC, time_limit_s=5.0)
    cp_ev = evaluate_assignment(cp_assign, ulds_small, POS_BY_NAME, AC)
    assert cp_ev["cargo_weight"] == pytest.approx(bf_w, abs=1e-6)
    assert cp_ev["feasible"]


# --- 9. CP-SAT nie schlechter als reparierte Heuristik ----------------------------------------------------
def test_check09_cp_sat_nie_schlechter_als_reparierte_greedy_heuristik():
    rng = np.random.default_rng(3)
    violations = 0
    for _ in range(30):
        n = rng.integers(4, 8)
        ulds_r = [ULD(f"u{i}", float(rng.integers(300, 2200))) for i in range(n)]
        g = repair_to_feasible(heuristic_greedy(ulds_r, POS, AC), ulds_r, POS_BY_NAME, AC)
        ev_g = evaluate_assignment(g, ulds_r, POS_BY_NAME, AC)
        cp_a, _, _ = solve_exact(ulds_r, POS, AC, time_limit_s=5.0)
        ev_cp = evaluate_assignment(cp_a, ulds_r, POS_BY_NAME, AC)
        if ev_cp["cargo_weight"] < ev_g["cargo_weight"] - 1e-6:
            violations += 1
    assert violations == 0


# --- 10. repair_to_feasible liefert immer eine zulässige Zuordnung -----------------------------------------
def test_check10_repair_to_feasible_liefert_immer_zulaessige_zuordnung():
    rng = np.random.default_rng(4)
    infeasible_after_repair = 0
    for _ in range(50):
        n = rng.integers(3, 9)
        ulds_r = [ULD(f"u{i}", float(rng.integers(300, 2500))) for i in range(n)]
        a = heuristic_greedy(ulds_r, POS, AC)
        a_rep = repair_to_feasible(a, ulds_r, POS_BY_NAME, AC)
        ev = evaluate_assignment(a_rep, ulds_r, POS_BY_NAME, AC)
        if not ev["feasible"]:
            infeasible_after_repair += 1
    assert infeasible_after_repair == 0


# --- 11. Regressionstest für den geschärften Hook ("vorn zuerst") ------------------------------------------
POS_MANY = [
    Position("fwd1", 8.0, 2000), Position("fwd2", 10.0, 2000), Position("fwd3", 12.0, 2000), Position("fwd4", 14.0, 2000),
    Position("aft1", 20.0, 2000), Position("aft2", 22.0, 2000), Position("aft3", 24.0, 2000), Position("aft4", 26.0, 2000),
]
POS_MANY_BY_NAME = {p.name: p for p in POS_MANY}
AC_MANY = Aircraft(empty_weight_kg=40000, empty_moment_kgm=40000 * 17.0, fuel_kg=8000, fuel_arm_m=17.0,
                    cg_min_m=16.5, cg_max_m=17.5)
ULDS_NOSE_HEAVY = [ULD(f"h{i}", 1800) for i in range(4)] + [ULD(f"l{i}", 200) for i in range(4)]


def test_check11_unreparierte_greedy_heuristik_verletzt_das_fenster():
    """Bug-Falle (Nullspalten-Signal): ohne diesen Test hätte eine zu großzügige Instanz den Effekt
    unsichtbar gemacht - bei der ersten Fassung mit nur 4 Positionen und lockerem Fenster blieb die naive
    Regel entgegen der Erwartung zulässig, siehe ERGEBNIS.md "Beim Bauen gefunden"."""
    raw = heuristic_greedy(ULDS_NOSE_HEAVY, POS_MANY, AC_MANY)
    ev_raw = evaluate_assignment(raw, ULDS_NOSE_HEAVY, POS_MANY_BY_NAME, AC_MANY)
    assert not ev_raw["feasible"]


# --- 12. H_balance liegt näher am Fensterziel als H_greedy --------------------------------------------------
def test_check12_h_balance_liegt_naeher_am_fensterziel_als_h_greedy():
    raw = heuristic_greedy(ULDS_NOSE_HEAVY, POS_MANY, AC_MANY)
    ev_raw = evaluate_assignment(raw, ULDS_NOSE_HEAVY, POS_MANY_BY_NAME, AC_MANY)
    bal = heuristic_balance(ULDS_NOSE_HEAVY, POS_MANY, AC_MANY)
    ev_bal = evaluate_assignment(bal, ULDS_NOSE_HEAVY, POS_MANY_BY_NAME, AC_MANY)
    target = (AC_MANY.cg_min_m + AC_MANY.cg_max_m) / 2.0
    assert abs(ev_bal["cg_empty"] - target) < abs(ev_raw["cg_empty"] - target)
    assert ev_bal["feasible"]  # bleibt hier sogar zulässig, ohne dass repariert werden musste


# --- 13. Determinismus ---------------------------------------------------------------------------------
def test_check13_determinismus_gleicher_seed_gleiche_gewichte():
    r1 = np.random.default_rng(11)
    r2 = np.random.default_rng(11)
    a1 = [float(r1.integers(300, 2200)) for _ in range(10)]
    a2 = [float(r2.integers(300, 2200)) for _ in range(10)]
    assert a1 == a2


# --- PFLICHT: Zwei-Zeitpunkte-Regressionstest (Detailplan Abschnitt 11) -------------------------------------
def test_zwei_zeitpunkte_check_voll_zulaessig_leer_unzulaessig():
    """Konstruierte Instanz: ein 2.000-kg-ULD ganz achtern (Hebelarm 24 m) verschiebt den Schwerpunkt bei
    engem Fenster (±0,3 m) so, dass der Index bei VOLLEM Tank (größeres Gesamtgewicht, kleinerer Ausschlag)
    noch im Fenster liegt, bei LEEREM Tank aber nicht mehr (kleineres Gesamtgewicht, größerer Ausschlag) -
    derselbe Mechanismus wie ERGEBNIS.md Befund 4. Ein Check, der nur den vollen Tank prüft, würde diese
    Zuordnung fälschlich als zulässig durchwinken."""
    ac = Aircraft(empty_weight_kg=40000, empty_moment_kgm=40000 * 17.0, fuel_kg=8000, fuel_arm_m=17.0,
                  cg_min_m=16.7, cg_max_m=17.3)
    pos_by_name = {"aft2": Position("aft2", 24.0, 2000)}
    uld = ULD("H", 2000.0)
    ev = evaluate_assignment({"H": "aft2"}, [uld], pos_by_name, ac)
    assert ev["ok_full"] is True
    assert ev["ok_empty"] is False
    assert ev["feasible"] is False  # feasible() muss BEIDE Zeitpunkte verlangen, nicht nur ok_full


# --- Grenzfälle der Heuristiken (aus dem Fehler-Einbau-Test, tools/mutation_check.py) ----------------------
def test_heuristic_greedy_laedt_uld_das_exakt_die_positionsgrenze_trifft():
    """Grenzfall: ein ULD-Gewicht exakt gleich der Positions-Gewichtsgrenze muss noch zugeordnet werden
    (>=, nicht >)."""
    pos = [Position("p1", 15.0, 2000.0)]
    uld = ULD("E", 2000.0)
    assign = heuristic_greedy([uld], pos, AC)
    assert assign == {"E": "p1"}


def test_heuristic_balance_laedt_uld_das_exakt_die_positionsgrenze_trifft():
    pos = [Position("p1", 17.0, 2000.0)]
    uld = ULD("E", 2000.0)
    assign = heuristic_balance([uld], pos, AC)
    assert assign == {"E": "p1"}


def test_repair_to_feasible_entfernt_nach_gewichtetem_nicht_nach_rohem_hebelabstand():
    """Regressionstest für die Gewichtung in repair_to_feasible: ein leichtes ULD weit vom Zentrum (roher
    Hebelabstand groß, aber wenig Einfluss auf den Schwerpunkt) gegen ein schweres ULD nah am Zentrum (roher
    Hebelabstand klein, aber großer Momentbeitrag). Die Reparatur muss das ULD mit dem größeren GEWICHTETEN
    Abstand entfernen (hier: das schwere B, Score 1900*1=1900 > leichtes A, Score 100*8=800) - nicht das mit
    dem größeren rohen Hebelabstand (das wäre A)."""
    ac = Aircraft(empty_weight_kg=40000, empty_moment_kgm=40000 * 17.0, fuel_kg=8000, fuel_arm_m=17.0,
                  cg_min_m=16.95, cg_max_m=17.05)
    pos_by_name = {"pA": Position("pA", 25.0, 2000.0), "pB": Position("pB", 18.0, 2000.0)}
    uld_a, uld_b = ULD("A", 100.0), ULD("B", 1900.0)
    assign = {"A": "pA", "B": "pB"}
    ev_both = evaluate_assignment(assign, [uld_a, uld_b], pos_by_name, ac)
    assert not ev_both["feasible"]  # beide zusammen verletzen das enge Fenster

    repaired = repair_to_feasible(assign, [uld_a, uld_b], pos_by_name, ac)
    assert repaired == {"A": "pA"}  # B (größerer gewichteter Abstand) wird entfernt, A bleibt
    ev_rep = evaluate_assignment(repaired, [uld_a, uld_b], pos_by_name, ac)
    assert ev_rep["feasible"]


def test_nur_voll_verletzt_ist_strukturell_unmoeglich():
    """Empirischer Beleg für die obige Docstring-Behauptung: bei neutralem Treibstoff (fuel_arm_m ==
    empty_arm_m, wie in diesem Modell) liegt der Schwerpunkt-Index OHNE Ladung an beiden Zeitpunkten exakt
    auf der Fenstermitte, und das Gesamtgewicht ist am leeren Tank immer kleiner - jede Momentabweichung
    wirkt sich dort also mindestens so stark aus wie am vollen Tank. "Nur voll verletzt" kann deshalb nicht
    vorkommen; in allen 45 gemessenen Zellen (3.600 Instanzen) ist only_full_bad_rate exakt 0,0 (siehe
    data/uldb_results.json, nachgerechnet in tests/test_claims.py)."""
    data = load_results()
    assert all(c["only_full_bad_rate"] == 0.0 for c in data["rows"])
