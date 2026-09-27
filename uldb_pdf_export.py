"""Erzeugt einen downloadbaren Beladeplan als PDF (in-memory, kein Zwischenspeichern auf Disk): Einstellungen,
Kennzahlen aller drei Verfahren, die Meldung der gezeigten Instanz und die Positionsliste aller drei
Zuordnungen.

fpdf2-Fallstricke (siehe DEMO-PLAYBOOK Abschnitt 7): echte Umlaute sind in den Kernschriften unproblematisch,
Gedankenstrich (-) und Euro-Zeichen (EUR statt Symbol) vermeiden - hier kommt ohnehin kein Geldbetrag vor."""
import time

import uldb_constants as C
from uldb_format import fmt_num, fmt_pct


def generate_uldb_pdf(settings: dict, live: dict, cell: dict) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Beladeplan - welche ULDs, welche Position?", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Einstellungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Fensterbreite +/- {fmt_num(settings['width'], 2)} m, Gewichtsniveau {settings['level']}",
              new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"ULDs: {settings['n_ulds']}, Seed {settings['seed']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Kennzahlen aller drei Verfahren (diese Instanz)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    headers = ["Kennzahl", "H_greedy", "H_balance", "CP-SAT"]
    widths = [55, 45, 45, 45]
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    ev_g, ev_b, ev_cp = live["ev_greedy"], live["ev_balance"], live["ev_exact"]
    rows = [
        ("Geladenes Gewicht (kg)", f"{ev_g['cargo_weight']:.0f}", f"{ev_b['cargo_weight']:.0f}", f"{ev_cp['cargo_weight']:.0f}"),
        ("Anzahl ULDs geladen", str(ev_g["n_loaded"]), str(ev_b["n_loaded"]), str(ev_cp["n_loaded"])),
        ("Schwerpunkt-Index voll (m)", f"{ev_g['cg_full']:.2f}", f"{ev_b['cg_full']:.2f}", f"{ev_cp['cg_full']:.2f}"),
        ("Schwerpunkt-Index leer (m)", f"{ev_g['cg_empty']:.2f}", f"{ev_b['cg_empty']:.2f}", f"{ev_cp['cg_empty']:.2f}"),
        ("Zulässig", "ja" if ev_g["feasible"] else "nein", "ja" if ev_b["feasible"] else "nein", "ja" if ev_cp["feasible"] else "nein"),
    ]
    for row in rows:
        for val, w in zip(row, widths):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Messreihe (80 Instanzen dieser Zelle)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, f"H_greedy verletzt in {fmt_pct(cell['violation_rate_greedy_raw'])} der Instanzen, "
                         f"Lücke zum Optimum {fmt_num(cell['gap_greedy_pct'], 1)} %; H_balance (repariert) "
                         f"Lücke {fmt_num(cell['gap_balance_pct'], 1)} %.")
    pdf.ln(3)

    for method_label, assign in (("H_greedy (repariert)", live["assign_greedy"]),
                                  ("H_balance (repariert)", live["assign_balance"]),
                                  ("CP-SAT (Optimum)", live["assign_exact"])):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Positionsliste {method_label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(235, 235, 235)
        headers2 = ["ULD", "Position", "Hebelarm (m)", "Gewicht (kg)"]
        widths2 = [40, 40, 40, 45]
        for h, w in zip(headers2, widths2):
            pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        ulds_by_name = {u.name: u for u in live["ulds"]}
        pos_by_name = C.POS_BY_NAME
        for uld_name in sorted(assign, key=lambda n: pos_by_name[assign[n]].arm_m):
            pos_name = assign[uld_name]
            pos = pos_by_name[pos_name]
            row2 = [uld_name, pos_name, f"{pos.arm_m:.1f}", f"{ulds_by_name[uld_name].weight_kg:.1f}"]
            for val, w in zip(row2, widths2):
                pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(6)
        if not assign:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 6, "(keine ULDs geladen)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    return bytes(pdf.output())
