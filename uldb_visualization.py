"""Beladeplan über mehrere ULD-Positionen - Plotly-Figuren.

Laderaumkarte (drei Zuordnungen H_greedy/H_balance/CP-SAT nebeneinander, Hebelarm auf der x-Achse - dieselbe
Achse trägt auch das Schwerpunktfenster, siehe loading_map_figure) plus die vorgerechneten Grafiken (Lücke
über die Fensterbreite, Regime über alle 45 Zellen). Alle Achsen `fixedrange` (Touch-Scrollen soll nicht am
Chart hängen bleiben, siehe DEMO-PLAYBOOK Abschnitt 3)."""
from __future__ import annotations

import plotly.graph_objects as go

from uldb_constants import COLOR_BALANCE, COLOR_EXACT, COLOR_GREEDY, POSITIONS, POS_MAX_WEIGHT_KG

METHOD_LABEL = {"greedy": "H_greedy (repariert)", "balance": "H_balance (repariert)", "exact": "CP-SAT (Optimum)"}
METHOD_COLOR = {"greedy": COLOR_GREEDY, "balance": COLOR_BALANCE, "exact": COLOR_EXACT}
METHOD_SYMBOL = {"greedy": "circle", "balance": "diamond", "exact": "square"}


def _loaded_weight_by_position(assign: dict[str, str], ulds: list, positions) -> list[float]:
    weight_by_pos = {p.name: 0.0 for p in positions}
    ulds_by_name = {u.name: u for u in ulds}
    for uld_name, pos_name in assign.items():
        weight_by_pos[pos_name] = weight_by_pos.get(pos_name, 0.0) + ulds_by_name[uld_name].weight_kg
    return [weight_by_pos[p.name] for p in positions]


def loading_map_figure(ulds: list, assigns: dict[str, dict], evals: dict[str, dict], ac, positions=POSITIONS):
    """Balken je Position (Hebelarm auf der x-Achse) für alle drei Zuordnungen nebeneinander, Schwerpunkt-
    fenster als grüner Streifen auf derselben Achse, CG-Index voll/leer je Verfahren als Marker oberhalb der
    Balken."""
    arms = [p.arm_m for p in positions]
    max_y = POS_MAX_WEIGHT_KG * 1.35
    fig = go.Figure()
    fig.add_vrect(x0=ac.cg_min_m, x1=ac.cg_max_m, fillcolor="rgba(61,139,95,0.15)", line_width=0,
                  annotation_text="Schwerpunktfenster", annotation_position="top left", layer="below")
    for method in ("greedy", "balance", "exact"):
        weights = _loaded_weight_by_position(assigns[method], ulds, positions)
        fig.add_trace(go.Bar(
            x=arms, y=weights, name=METHOD_LABEL[method], marker_color=METHOD_COLOR[method],
            hovertext=[f"{METHOD_LABEL[method]}: {w:.0f} kg" for w in weights], hoverinfo="text",
        ))
    for method in ("greedy", "balance", "exact"):
        ev = evals[method]
        fig.add_trace(go.Scatter(
            x=[ev["cg_full"]], y=[max_y * 0.94], mode="markers", marker=dict(symbol="triangle-down", size=12, color=METHOD_COLOR[method]),
            name=f"{METHOD_LABEL[method]} CG (voll)", showlegend=False,
            hovertext=[f"{METHOD_LABEL[method]}: CG voll = {ev['cg_full']:.2f} m"], hoverinfo="text",
        ))
        fig.add_trace(go.Scatter(
            x=[ev["cg_empty"]], y=[max_y * 1.04], mode="markers", marker=dict(symbol="triangle-up", size=12, color=METHOD_COLOR[method]),
            name=f"{METHOD_LABEL[method]} CG (leer)", showlegend=False,
            hovertext=[f"{METHOD_LABEL[method]}: CG leer = {ev['cg_empty']:.2f} m"], hoverinfo="text",
        ))
    fig.update_layout(
        barmode="group", height=380, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Hebelarm (m)", range=[3.0, 31.0], fixedrange=True),
        yaxis=dict(title="Geladenes Gewicht je Position (kg)", range=[0, max_y], fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
    )
    return fig


def gap_over_width_figure(rows: list[dict]):
    """Lücke H_greedy (repariert) gegen H_balance (repariert) zum CP-SAT-Optimum über die Fensterbreite."""
    widths = [f"±{r['width']:g} m" for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=widths, y=[r["gap_greedy_pct"] for r in rows], name="Lücke H_greedy (repariert)",
                          marker_color=COLOR_GREEDY, text=[f"{r['gap_greedy_pct']:.1f} %" for r in rows], textposition="outside"))
    fig.add_trace(go.Bar(x=widths, y=[r["gap_balance_pct"] for r in rows], name="Lücke H_balance (repariert)",
                          marker_color=COLOR_BALANCE, text=[f"{r['gap_balance_pct']:.1f} %" for r in rows], textposition="outside"))
    fig.update_layout(
        barmode="group", height=340, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Schwerpunktfenster ±", fixedrange=True),
        yaxis=dict(title="Lücke zum CP-SAT-Optimum (%)", range=[0, 62], fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def regime_figure(rows: list[dict]):
    """Wirtschaftlicher Preis der naiven Regel (Lücke H_greedy, Prozent) über alle 45 Zellen, gefärbt nach Urteil."""
    color_map = {"optimal": "#3d8b5f", "luecke": "#c9a227", "unkritisch": "#7a7a7a"}
    xs = [f"±{r['width']:g}/{r['level'][:4]}/{r['n_ulds']}" for r in rows]
    ys = [r["gap_greedy"] for r in rows]
    colors = [color_map[r["state"]] for r in rows]
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=colors, hovertext=[r["label"] for r in rows], hoverinfo="text+y"))
    fig.update_layout(
        height=340, margin=dict(l=10, r=10, t=20, b=90),
        xaxis=dict(title="Fensterbreite / Gewichtsniveau / ULD-Zahl", tickangle=90, fixedrange=True, tickfont=dict(size=8)),
        yaxis=dict(title="Lücke H_greedy zum Optimum (%)", fixedrange=True),
        showlegend=False,
    )
    return fig
