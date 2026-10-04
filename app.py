"""
Beladeplan: welche ULDs, welche Position? - interaktive Fall-Demo (Weight & Balance)
Sebastian Hanisch - Operations Research und Machine Learning

Zweites Stück der Packen-Ausbaulinie, eigenständig gegenüber uld-gewicht-demo (dort: Volumen-Packung EINES
ULD gegen Schwerpunkt) und geschärft gegenüber stauplanung-demo (dort: Vollbelegung + Umstau-Sequenz an
EINEM Zeitpunkt). Hier: welche ULDs kommen auf welche der 10 Laderaumpositionen, damit weder eine Position
ihre Gewichtsgrenze überschreitet noch der Flugzeug-Schwerpunkt - an ZWEI Zeitpunkten, vollem UND leerem
Tank - aus dem zulässigen Fenster läuft, bei maximal geladenem Gewicht? Live: eine Instanz mit drei
Verfahren (H_greedy, H_balance, CP-SAT-Optimum). Vorgerechnet: die Messreihe über 80 Instanzen je Zelle
(data/uldb_results.json), die die Aussage trägt.

Lauffähig mit: streamlit run app.py
"""
import numpy as np
import streamlit as st

import uldb_constants as C
import uldb_results as R
import uldb_stories as S
import uldb_visualization as V
from uldb_format import fmt_num, fmt_pct
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import ULD, evaluate_assignment
from uldb_oracle import solve_exact
from uldb_pdf_export import generate_uldb_pdf
from uldb_presets import (SETTING_SPECS, apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                           randomize_seed, sync_query_params)

st.set_page_config(page_title="Beladeplan: welche ULDs, welche Position? – Sebastian Hanisch", layout="wide")

DATA = R.load_results()


@st.cache_data(show_spinner=False, max_entries=256)
def _live(width, n_ulds, level, seed):
    ac = C.make_aircraft(width)
    lo, hi = C.WEIGHT_LEVELS[level]
    rng = np.random.default_rng(seed)
    ulds = [ULD(f"u{i}", float(rng.uniform(lo, hi))) for i in range(n_ulds)]

    g_raw = heuristic_greedy(ulds, C.POSITIONS, ac)
    g_rep = repair_to_feasible(g_raw, ulds, C.POS_BY_NAME, ac)
    ev_g = evaluate_assignment(g_rep, ulds, C.POS_BY_NAME, ac)

    b_raw = heuristic_balance(ulds, C.POSITIONS, ac)
    b_rep = repair_to_feasible(b_raw, ulds, C.POS_BY_NAME, ac)
    ev_b = evaluate_assignment(b_rep, ulds, C.POS_BY_NAME, ac)

    cp_assign, status, _ = solve_exact(ulds, C.POSITIONS, ac, time_limit_s=2.0)
    ev_cp = evaluate_assignment(cp_assign, ulds, C.POS_BY_NAME, ac)

    return dict(
        ulds=ulds, ac=ac,
        assign_greedy=g_rep, assign_balance=b_rep, assign_exact=cp_assign,
        ev_greedy=ev_g, ev_balance=ev_b, ev_exact=ev_cp,
        cp_status=status,
    )


st.title("🛫 Beladeplan: welche ULDs, welche Position?")
st.markdown(
    """
Welche ULDs kommen auf welche der **10 Laderaumpositionen**, damit keine Position ihre Gewichtsgrenze
überschreitet und der Flugzeug-**Schwerpunkt** sowohl mit vollem als auch mit **leerem Tank** im zulässigen
Fenster liegt - bei maximal geladenem Gewicht? Ein **Auswahlproblem**: anders als bei `stauplanung-demo`
(Vollbelegung, Umstau-Sequenz, ein Zeitpunkt) muss hier nicht jedes ULD mitfliegen, dafür muss das
Schwerpunktfenster an **zwei Zeitpunkten** gleichzeitig halten. Die Demo zeigt live **eine Instanz** mit drei
Verfahren (**H_greedy**, ignoriert Balance; **H_balance**, schwerpunkt-bewusst; **CP-SAT**, das bewiesene
Optimum, hier immer mitgerechnet - unter 2 s), und vorgerechnet die Messreihe über **80 Instanzen je Zelle**,
die die Aussage trägt. Wie das Modell funktioniert, steht im Expander „Wie funktioniert diese Demo?" weiter
unten, die formale Beschreibung im Expander „📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_names = list(C.PRESETS)
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(len(row))
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Schwerpunktfenster**")
    width = st.select_slider("Fensterbreite ±", options=list(C.WIDTH_OPTIONS), key="width_slider",
                             help="Zulässiger Schwerpunkt-Ausschlag um die Flugzeugmitte (17,0 m), in Metern. "
                                  "Enger = schwerer zu erfüllen.")
    st.markdown("**Ladung**")
    n_ulds = st.select_slider("Anzahl ULDs", options=list(C.ULDS_OPTIONS), key="ulds_slider",
                              help="Gemessene Stufen der Messreihe (8 / 12 / 16). Mehr ULDs als Positionen "
                                   "(10) macht es zum echten Auswahlproblem.")
    level = st.selectbox("Gewichtsniveau", options=list(C.LEVEL_OPTIONS), key="level_select",
                         format_func=lambda v: C.LEVEL_LABEL[v],
                         help="Bereich, aus dem die ULD-Gewichte gleichverteilt gezogen werden.")
    st.markdown("**Gezeigte Instanz**")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1,
                           help="Nummer der gezeigten Instanz.")
    st.button("🎲 Neue Instanz", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed.")

sync_query_params({key: st.session_state[key] for key in SETTING_SPECS})
width, n_ulds, seed = float(width), int(n_ulds), int(seed)

cell = R.find_cell(DATA, width, level, n_ulds)
live = _live(width, n_ulds, level, seed)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht (Kernabschnitt ①, live: eine Instanz)
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🛫 Welche ULDs kommen auf welche Position?")
st.caption(f"Live-Instanz (eine Instanz): Seed {seed}, {n_ulds} ULDs, Gewichtsniveau {C.LEVEL_LABEL[level]}, "
           f"Fensterbreite ±{fmt_num(width, 2)} m. Alle drei Verfahren laufen bei jeder Einstellung neu "
           "(CP-SAT unter 2 s, je Einstellung zwischengespeichert). Eine einzelne Instanz – die vorgerechnete "
           "Messreihe unten trägt die Aussage.")

st.plotly_chart(V.loading_map_figure(live["ulds"], {"greedy": live["assign_greedy"], "balance": live["assign_balance"],
                                                      "exact": live["assign_exact"]},
                                      {"greedy": live["ev_greedy"], "balance": live["ev_balance"], "exact": live["ev_exact"]},
                                      live["ac"]), width="stretch", key="main_loading_map")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Geladenes Gewicht H_greedy", f"{live['ev_greedy']['cargo_weight']:.0f} kg",
          delta="zulässig" if live["ev_greedy"]["feasible"] else "unzulässig", delta_color="off")
k2.metric("Geladenes Gewicht H_balance", f"{live['ev_balance']['cargo_weight']:.0f} kg",
          delta="zulässig" if live["ev_balance"]["feasible"] else "unzulässig", delta_color="off")
k3.metric("Geladenes Gewicht CP-SAT", f"{live['ev_exact']['cargo_weight']:.0f} kg", delta="Optimum", delta_color="off")
k4.metric("Schwerpunkt-Index (voll) G/B/CP", f"{live['ev_greedy']['cg_full']:.2f}/{live['ev_balance']['cg_full']:.2f}/{live['ev_exact']['cg_full']:.2f} m")
st.caption(f"Schwerpunkt-Index (leer) H_greedy/H_balance/CP-SAT: {live['ev_greedy']['cg_empty']:.2f} / "
           f"{live['ev_balance']['cg_empty']:.2f} / {live['ev_exact']['cg_empty']:.2f} m - zulässiges Fenster "
           f"[{live['ac'].cg_min_m:.2f}; {live['ac'].cg_max_m:.2f}] m an BEIDEN Zeitpunkten.")

st.info(R.judgment_text(cell))
st.caption("Ehrliche Grenze: eine Instanz zeigt nur einen von 80 möglichen Zufallsfällen; die Meldung oben "
           "stützt sich auf die Messreihe (80 Instanzen dieser Zelle), nicht auf diese eine Instanz.")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt ② (vorgerechnet): was die Messreihe zeigt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Was die Messreihe über 80 Instanzen je Zelle zeigt")
st.markdown(
    """
Kernfrage: Wie oft verletzt eine Regel ohne Balance-Bewusstsein das Schwerpunktfenster, was kostet das an
Ladegewicht, und wie nah kommt eine balance-bewusste Regel ans CP-SAT-Optimum? Die Antwort steht auf
**80 Instanzen je Zelle** (45 Zellen: Fensterbreite × Gewichtsniveau × ULD-Zahl), vorgerechnet und **nie live**
gerechnet. Gezeigt wird die exakt gemessene Zelle Ihrer Einstellung (die drei Regler bilden genau die drei
Sweep-Dimensionen ab, keine Näherung nötig).
"""
)

st.markdown("**1 · Lücke zum CP-SAT-Optimum über die Fensterbreite** (festes Gewichtsniveau/ULD-Zahl Ihrer Einstellung)")
w_rows = R.width_rows(DATA, level, n_ulds)
st.plotly_chart(V.gap_over_width_figure(w_rows), width="stretch", key="core_gap")
st.caption("H_greedy ignoriert Balance komplett und wird bei engem Fenster teuer. H_balance bleibt fast "
           "überall bei 0 % Lücke, öffnet aber bei sehr engem Fenster (±0,08 m) eine kleine, echte Lücke - "
           "das ist Befund 3 der Messreihe, ehrlich gezeigt statt kaschiert.")

st.markdown("**2 · Zwei-Zeitpunkte-Effekt** – wie oft fängt der Check nur den leeren, nicht den vollen Tank?")
oe = R.only_empty_summary(DATA)
oe_cell = oe["max_only_empty_cell"]
c1, c2 = st.columns([2, 3])
with c1:
    st.metric("Nur-leer-Tank-Verletzungen (Mittel über 45 Zellen)", fmt_pct(oe["mean_only_empty"]))
    st.metric("Nur-leer-Tank-Verletzungen (Extremfall)", fmt_pct(oe["max_only_empty"]))
with c2:
    st.markdown(f"Über alle 45 gemessenen Zellen verletzt H_greedy (unrepariert) im Mittel **{fmt_pct(oe['mean_only_empty'])}** "
                f"und im Extremfall (±{oe_cell['width']:g} m, {oe_cell['level']}, {oe_cell['n_ulds']} ULDs) bis zu "
                f"**{fmt_pct(oe['max_only_empty'])}** der Instanzen **nur** am leeren Tank - mit vollem Tank wäre "
                "dieselbe Zuordnung zulässig gewesen. Mechanismus: mit leerem Tank ist das Gesamtgewicht kleiner, "
                "dieselbe Ladungs-Moment-Abweichung wirkt sich stärker auf den Schwerpunkt-Index aus. Ein Check nur "
                "am vollen Tank - der Umfang von `stauplanung-demo`s Schwerpunktgrenze - hätte diese Fälle durchgelassen.")

st.markdown("**3 · Regime** – wirtschaftlicher Preis der naiven Regel über alle 45 gemessenen Zellen")
regime = R.regime_rows(DATA)
st.plotly_chart(V.regime_figure(regime), width="stretch", key="core_regime")
_counts = {}
for r in regime:
    _counts[r["state"]] = _counts.get(r["state"], 0) + 1
_state_text = (
    f"„{R.STATE_LABEL[R.STATE_UNKRITISCH]}“ ({_counts.get(R.STATE_UNKRITISCH, 0)} von 45 Zellen), "
    f"„{R.STATE_LABEL[R.STATE_OPTIMAL]}“ ({_counts.get(R.STATE_OPTIMAL, 0)}), "
    f"„{R.STATE_LABEL[R.STATE_LUECKE]}“ ({_counts.get(R.STATE_LUECKE, 0)})"
)
gb = R.gap_balance_summary(DATA)
st.caption(f"Urteil in drei Zuständen (wie die Meldung oben): {_state_text}. **Grenzen der Heuristik:** in "
           f"{gb['n_total'] - gb['n_zero']} von {gb['n_total']} Zellen hat H_balance selbst eine Lücke zum "
           f"Optimum (bis {fmt_num(gb['max_gap'], 1)} % bei ±{gb['max_cell']['width']:g} m, {gb['max_cell']['level']}, "
           f"{gb['max_cell']['n_ulds']} ULDs) - ausdrücklich benannt, nicht versteckt.")

with pdf_slot:
    st.download_button(
        "📄 Beladeplan als PDF herunterladen",
        data=generate_uldb_pdf(dict(width=width, n_ulds=n_ulds, level=level, seed=seed), live, cell),
        file_name="uld_beladeplan.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Einstellungen, Kennzahlen aller drei Verfahren und die Meldung der gezeigten Instanz.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Ansichten
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tabs = st.tabs(["🛫 Laderaumkarte", "📊 Verfahren", "📈 Messreihe"])
    with tabs[0]:
        st.markdown("Alle drei Zuordnungen auf derselben Hebelarm-Achse, Schwerpunktfenster als grüner "
                     "Streifen, CG-Index voll (▽) und leer (△) je Verfahren als Marker oberhalb der Balken.")
        st.plotly_chart(V.loading_map_figure(live["ulds"], {"greedy": live["assign_greedy"], "balance": live["assign_balance"],
                                                              "exact": live["assign_exact"]},
                                              {"greedy": live["ev_greedy"], "balance": live["ev_balance"], "exact": live["ev_exact"]},
                                              live["ac"]), width="stretch", key="tab_loading_map")
    with tabs[1]:
        st.markdown("Alle drei Verfahren auf **dieser** Instanz, Kennzahlen nebeneinander:")
        st.dataframe(
            {
                "Kennzahl": ["Geladenes Gewicht (kg)", "Anzahl ULDs geladen", "Schwerpunkt-Index (voll)",
                             "Schwerpunkt-Index (leer)", "Zulässig"],
                "H_greedy": [f"{live['ev_greedy']['cargo_weight']:.0f}", str(live['ev_greedy']['n_loaded']),
                             f"{live['ev_greedy']['cg_full']:.2f}", f"{live['ev_greedy']['cg_empty']:.2f}",
                             "ja" if live['ev_greedy']['feasible'] else "nein"],
                "H_balance": [f"{live['ev_balance']['cargo_weight']:.0f}", str(live['ev_balance']['n_loaded']),
                              f"{live['ev_balance']['cg_full']:.2f}", f"{live['ev_balance']['cg_empty']:.2f}",
                              "ja" if live['ev_balance']['feasible'] else "nein"],
                "CP-SAT": [f"{live['ev_exact']['cargo_weight']:.0f}", str(live['ev_exact']['n_loaded']),
                           f"{live['ev_exact']['cg_full']:.2f}", f"{live['ev_exact']['cg_empty']:.2f}",
                           "ja" if live['ev_exact']['feasible'] else "nein"],
            },
            width="stretch", hide_index=True,
        )
        st.caption(f"Zum Vergleich die Messreihe dieser Zelle (80 Instanzen): {R.judgment_text(cell)}")
    with tabs[2]:
        st.markdown("Alle 45 gemessenen Zellen als Tabelle (Fensterbreite, Gewichtsniveau, ULD-Zahl, "
                     "Verletzungsrate H_greedy, Lücke beider Verfahren, Zwei-Zeitpunkte-Anteil, Urteil):")
        st.dataframe(
            {
                "Fenster ±": [f"{r['width']:g} m" for r in regime], "Gewicht": [r["level"] for r in regime],
                "ULDs": [r["n_ulds"] for r in regime], "Verletzung H_greedy": [fmt_pct(r["violation_greedy"]) for r in regime],
                "Lücke H_greedy": [fmt_num(r["gap_greedy"], 1) + " %" for r in regime],
                "Lücke H_balance": [fmt_num(r["gap_balance"], 1) + " %" for r in regime],
                "Nur-leer-Verletzung": [fmt_pct(r["only_empty_bad"]) for r in regime],
                "Urteil": [r["label"] for r in regime],
            },
            width="stretch", hide_index=True, height=360,
        )

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Instanz.** Flugzeug mit Leergewicht {C.EMPTY_WEIGHT_KG:.0f} kg bei Hebelarm {C.CENTER_M:.1f} m
(Referenzpunkt), Treibstoff {C.FUEL_KG:.0f} kg (Hebelarm {C.CENTER_M:.1f} m, selbst neutral),
Schwerpunktfenster [{C.CENTER_M:.1f} − Breite; {C.CENTER_M:.1f} + Breite] m. **{C.N_POS} Laderaumpositionen**
gleichmäßig von Hebelarm {C.ARM_MIN:.1f} bis {C.ARM_MAX:.1f} m, je {C.POS_MAX_WEIGHT_KG:.0f} kg Gewichtsgrenze.
ULDs: 8/12/16 Stück je Instanz, Gewicht gleichverteilt in einem von drei Bereichen (leicht/gemischt/schwer).

**Die Verfahren.** **H_greedy:** schwerste ULDs zuerst, jeweils die erste freie Position mit ausreichender
Gewichtsgrenze (Positions-Reihenfolge von vorn nach hinten) - ohne Rücksicht auf Balance. **H_balance:**
schwerste ULDs zuerst, aber jeweils die freie Position, die den Schwerpunkt (Leergewicht-Zustand) am
nächsten an die Fenstermitte bringt. **Reparatur:** entfernt aus einer unzulässigen Zuordnung das ULD mit
dem größten gewichteten Hebelabstand zur Fenstermitte, bis beide Zeitpunkte zulässig sind - bildet nach, was
ein Lademeister tut. **CP-SAT:** 0/1-Zuordnung ULD→Position, Schwerpunktfenster an beiden Zeitpunkten
linearisiert, maximiertes geladenes Gewicht; fand in 100 % von 3.600 gerechneten Instanzen das bewiesene
Optimum.

**Warum die naive Regel bei engem Fenster real Ladegewicht kostet, nicht nur Zulässigkeit.** Die Reparatur
macht auch H_greedy zulässig - aber dabei müssen ULDs wieder ausgeladen werden, und je enger das Fenster,
desto mehr. Der Preis zeigt sich als fehlendes geladenes Gewicht gegenüber dem CP-SAT-Optimum, nicht als
Unzulässigkeit.

**Warum die balance-bewusste Regel fast immer optimal ist - und wo genau nicht.** H_balance bevorzugt bei
jedem Schritt die Position, die den Schwerpunkt am nächsten an die Fenstermitte bringt - bei {C.N_POS}
Positionen und Fensterbreite ≥ ±0,15 m reicht das praktisch immer für das CP-SAT-Optimum. Bei sehr engem
Fenster (±0,08 m) öffnet sich eine kleine, aber echte Lücke: dort reicht eine myopische, nie zurückblickende
Regel nicht mehr aus, um die letzten Prozentpunkte Ladegewicht herauszuholen.

**Was der Zwei-Zeitpunkte-Check zeigt.** Mit leerem Tank ist das Gesamtgewicht kleiner, dieselbe
Ladungs-Moment-Abweichung wirkt sich also stärker auf den Schwerpunkt-Index aus. Ein Check nur am vollen
Tank - der naheliegende erste Ansatz, und genau der Umfang von `stauplanung-demo`s Schwerpunktgrenze (ein
Zeitpunkt) - hätte einen Teil der Verletzungen durchgelassen.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- Flugzeug- und Positionsdaten erfunden, nicht kalibriert; die Größenordnung orientiert sich grob an
  schmalen Verkehrsflugzeugen, ist aber kein Zitat einer echten Gewichts-und-Schwerpunkt-Tabelle.
- Nur der Längs-Schwerpunkt (fore/aft); keine Seitenlage (links/rechts), die `stauplanung-demo` mit
  „Seitenneigung" bereits hat - bewusst nicht übernommen, um die Abgrenzung klar zu halten.
- Positions-Gewichtsgrenzen sind unabhängig voneinander (reale Frachträume haben oft zusätzliche Grenzen
  für Positionsgruppen).
- Treibstoff hat in der Basis denselben Hebelarm wie das Leergewicht (neutral).
- **Nicht Teil dieser Demo:** Seitenlage/Seitenneigung, gruppierte Positions-Gewichtsgrenzen, ein
  asymmetrischer Treibstoff-Hebelarm, eine dritte (Tausch-)Heuristik, mehr als {C.N_POS} Positionen oder 16
  ULDs, echte Flugzeugtyp-Daten.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Schwerpunkt-Index.** $\mathrm{cg}(W, M) = M / W$ (Gesamtmoment durch Gesamtgewicht).

**Zulässigkeit.** $\mathrm{cg\_min} \le \mathrm{cg}(W_0 + \sum_i x_i w_i,\, M_0 + \sum_i x_i w_i \cdot \mathrm{arm}_i) \le \mathrm{cg\_max}$,
ausgewertet für $(W_0, M_0)$ = voller UND leerer Tank.

**Linearisierung für CP-SAT.** $\sum_i x_i w_i (\mathrm{arm}_i - \mathrm{cg\_min}) \ge \mathrm{cg\_min} \cdot W_0 - M_0$
(und spiegelbildlich für die obere Grenze), je einmal für voll und leer.

**Ziel.** $\max \sum_i x_i w_i$ unter $\sum_j x_{ij} \le 1$ je ULD $i$, $\sum_i x_{ij} \le 1$ je Position $j$,
Positions-Gewichtsgrenze $\sum_i x_{ij} w_i \le \mathrm{cap}_j$.

Implementiert in `uldb_model.py` (Datentypen, Bewertung), `uldb_heuristics.py` (H_greedy, H_balance,
Reparatur) und `uldb_oracle.py` (CP-SAT).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html)."
)
