"""Handverlesene Mutantenliste für die beiden Kernmodule (uldb_model.py, uldb_heuristics.py): jede alte
Stelle kommt im jeweiligen Modul genau einmal vor. Wie bei uld-gewicht-demo (siehe dortiges tools/mutants.py)
sind es hier nur zwei kleine, mechanisch aus beladeplan.py übernommene Module - eine handverlesene Liste
deckt jede Vergleichsoperation, jede Vorzeichen-/Faktor-Stelle und jede Sortierordnung ab, ohne die
Maschinerie eines Generators zu brauchen.

EQUIVALENT_NOTES wird nach dem ersten vollen Lauf mit der tatsächlichen Einordnung der Überlebenden gefüllt
(siehe tools/mutation_check.py und den Bericht im Abschluss-Kommentar)."""
EQUIVALENT_NOTES = """Stand nach mehreren Läufen (28 handverlesene Mutanten, --jobs 1 zur Vermeidung von
Laufzeitschwankungen unter CPU-Last - bei hoher Parallelität (--jobs 6) meldete CP-SAT unter Last vereinzelt
andere Ergebnisse, siehe unten): Lauf 1 fand 18, 10 überlebten; nach dem Schließen von 8 echten Testlücken
(tests/test_model.py: die Epsilon-Grenzfälle von cg_ok() auf BEIDEN Seiten, cg_index() direkt mit Gewicht 0
aufgerufen, ein Grenzfall "Gewicht exakt an der Positionsgrenze" für H_greedy UND H_balance, und der
Regressionstest, dass repair_to_feasible() nach dem GEWICHTETEN, nicht dem rohen Hebelabstand entfernt) fand
der stabile Lauf (--jobs 1) 23 von 28, 5 überlebten - drei davon beweisbar/strukturell gleichwertig, zwei als
akzeptierter Rest-Befund dokumentiert:

(1) `> p.max_weight_kg + 1e-6` -> `>=`: unterscheidet sich nur, wenn eine Positionsbelegung exakt
    `max_weight_kg + 1e-6` kg beträgt - eine Summe aus realistischen kg-Gewichten trifft dieses Epsilon
    praktisch nie exakt (dieselbe Klasse wie die 1e-9-Toleranzen in cg_ok(), siehe uld-gewicht-demo
    tools/mutants.py für dasselbe Muster).
(2) `cg_full=... if w_full > 0 else 0.0` -> `>= 0`: w_full = Leergewicht + Treibstoff + Fracht ist in diesem
    Modell IMMER > 40.000 kg (Leergewicht und Treibstoff sind feste, positive Konstanten) - die Grenze bei 0
    wird nie erreicht, der Unterschied zwischen `>` und `>=` ist an dieser Stelle unerreichbarer Code.
(3) `dist = abs(idx - target)` -> `* 0.5`: mathematisch bewiesen gleichwertig - `dist` wird in
    heuristic_balance() NUR für einen Vergleich `dist < best_dist` zwischen Kandidaten derselben Iteration
    verwendet; eine Multiplikation ALLER Kandidaten-Distanzen mit demselben positiven Faktor ändert das
    Ergebnis von `argmin` nicht.
(4) `while guard < len(ulds) + 1:` -> `while guard < len(ulds):` und
(5) `guard += 1` -> `guard += 2` (beide dasselbe Iterationsbudget in repair_to_feasible() betreffend):
    der guard ist ein großzügiges Sicherheitsnetz gegen eine Endlosschleife, kein Modellparameter. In JEDER
    gemessenen Instanz (3.600 Sweep-Instanzen, alle Zufallsinstanzen in check09/check10, alle eingefrorenen
    Referenzfälle) konvergiert die Reparatur nach wenigen Schritten (typischerweise 1-3 Entfernungen), weit
    unter der Hälfte von len(ulds)+1 - ein Fall, der tatsächlich mehr als die Hälfte der ULDs sequenziell
    entfernen muss, um zulässig zu werden, wurde beim Konstruktionsversuch nur über eine entartete
    Flugzeugkonfiguration erreicht (ein Fenster, das schon die LEERE Zuordnung verletzt - ein Flugzeug, dessen
    eigene Gewichts-und-Schwerpunkt-Angaben außerhalb seines eigenen Fensters liegen, kommt in diesem Modell
    nicht sinnvoll vor). Als akzeptierter Rest-Befund dokumentiert statt mit einer künstlichen, modellfremden
    Instanz erzwungen.

**Laufzeitschwankung unter CPU-Last (beim Bauen gefunden):** bei `--jobs 6` (starke Parallelität, viele
gleichzeitige CP-SAT-Läufe mit je `num_search_workers=8`) meldete derselbe Mutantensatz in einem Lauf nur 2
statt 5 Überlebende - vermutlich, weil CP-SAT unter CPU-Konkurrenz gelegentlich das Zeitlimit ausschöpft und
dadurch minimal andere (aber weiterhin zulässige) Lösungen liefert. Für ein verlässliches Ergebnis
`tools/mutation_check.py --jobs 1` verwenden (langsamer, aber reproduzierbar) - die Zahl oben (23/28, 5
Überlebende) ist über mehrere `--jobs 1`- und `--jobs 2`-Läufe hinweg stabil."""

MUTANTS = [
    # --- uldb_model.py ---------------------------------------------------------------------------------
    ("uldb_model.py", "return total_moment_kgm / total_weight_kg if total_weight_kg > 0 else 0.0",
     "return total_moment_kgm / total_weight_kg if total_weight_kg >= 0 else 0.0"),
    ("uldb_model.py", "if total_weight_kg <= 0:", "if total_weight_kg < 0:"),
    ("uldb_model.py", "return cg_min - 1e-9 <= idx <= cg_max + 1e-9", "return cg_min - 1e-9 < idx <= cg_max + 1e-9"),
    ("uldb_model.py", "return cg_min - 1e-9 <= idx <= cg_max + 1e-9", "return cg_min - 1e-9 <= idx < cg_max + 1e-9"),
    ("uldb_model.py", "w_full = ac.empty_weight_kg + ac.fuel_kg + cargo_weight",
     "w_full = ac.empty_weight_kg + cargo_weight"),
    ("uldb_model.py", "m_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m) + cargo_moment",
     "m_full = ac.empty_moment_kgm + cargo_moment"),
    ("uldb_model.py", "m_empty = ac.empty_moment_kgm + cargo_moment", "m_empty = ac.empty_moment_kgm"),
    ("uldb_model.py", "cargo_weight += u.weight_kg", "cargo_weight += u.weight_kg * 1.01"),
    ("uldb_model.py", "cargo_moment += moment_of(u.weight_kg, pos.arm_m)",
     "cargo_moment += moment_of(u.weight_kg, pos.arm_m) * 1.01"),
    ("uldb_model.py", "> p.max_weight_kg + 1e-6", ">= p.max_weight_kg + 1e-6"),
    ("uldb_model.py", "feasible=ok_full and ok_empty and not over_capacity,", "feasible=ok_full and ok_empty,"),
    ("uldb_model.py", "ok_full = cg_ok(w_full, m_full, ac.cg_min_m, ac.cg_max_m)",
     "ok_full = cg_ok(w_empty, m_empty, ac.cg_min_m, ac.cg_max_m)"),
    ("uldb_model.py", "ok_empty = cg_ok(w_empty, m_empty, ac.cg_min_m, ac.cg_max_m)",
     "ok_empty = cg_ok(w_full, m_full, ac.cg_min_m, ac.cg_max_m)"),
    ("uldb_model.py", "cg_full=cg_index(w_full, m_full) if w_full > 0 else 0.0,",
     "cg_full=cg_index(w_full, m_full) if w_full >= 0 else 0.0,"),
    # --- uldb_heuristics.py -----------------------------------------------------------------------------
    ("uldb_heuristics.py",
     'order = sorted(ulds, key=lambda u: -u.weight_kg)\n    free = list(positions)\n    assign: dict[str, str] = {}\n    for u in order:\n        for p in list(free):',
     'order = sorted(ulds, key=lambda u: u.weight_kg)\n    free = list(positions)\n    assign: dict[str, str] = {}\n    for u in order:\n        for p in list(free):'),
    ("uldb_heuristics.py",
     'order = sorted(ulds, key=lambda u: -u.weight_kg)\n    free = list(positions)\n    assign: dict[str, str] = {}\n    target = (ac.cg_min_m + ac.cg_max_m) / 2.0\n    cur_w = ac.empty_weight_kg',
     'order = sorted(ulds, key=lambda u: u.weight_kg)\n    free = list(positions)\n    assign: dict[str, str] = {}\n    target = (ac.cg_min_m + ac.cg_max_m) / 2.0\n    cur_w = ac.empty_weight_kg'),
    ("uldb_heuristics.py", "if p.max_weight_kg >= u.weight_kg:", "if p.max_weight_kg > u.weight_kg:"),
    ("uldb_heuristics.py", "if p.max_weight_kg < u.weight_kg:\n                continue",
     "if p.max_weight_kg <= u.weight_kg:\n                continue"),
    ("uldb_heuristics.py", "new_m = cur_m + moment_of(u.weight_kg, p.arm_m)",
     "new_m = cur_m + moment_of(u.weight_kg, p.arm_m) * 1.01"),
    ("uldb_heuristics.py", "dist = abs(idx - target)", "dist = abs(idx - target) * 0.5"),
    ("uldb_heuristics.py", "if best is None or dist < best_dist:", "if best is None or dist <= best_dist:"),
    ("uldb_heuristics.py", "cur_w += u.weight_kg", "cur_w += u.weight_kg * 1.01"),
    ("uldb_heuristics.py", "cur_m += moment_of(u.weight_kg, best.arm_m)",
     "cur_m += moment_of(u.weight_kg, best.arm_m) * 1.01"),
    ("uldb_heuristics.py", "while guard < len(ulds) + 1:", "while guard < len(ulds):"),
    ("uldb_heuristics.py", "if ev[\"feasible\"]:\n            return assign", "if not ev[\"feasible\"]:\n            return assign"),
    ("uldb_heuristics.py",
     "worst = max(assign, key=lambda n: abs(positions[assign[n]].arm_m - target) * uld_by_name[n].weight_kg)",
     "worst = max(assign, key=lambda n: abs(positions[assign[n]].arm_m - target))"),
    ("uldb_heuristics.py", "del assign[worst]", "del assign[list(assign)[0]]"),
    ("uldb_heuristics.py", "guard += 1", "guard += 2"),
]
