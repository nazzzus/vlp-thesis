#!/usr/bin/env python3
"""
analyze_t4.py – T4 Cold-Start Auswertung
VLP Serverless Framework Vergleich – Bachelorarbeit

Ausführung:
    pip install matplotlib numpy
    python3 analyze_t4.py

Ergebnisse werden gespeichert in: results/figures/
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ── Konfiguration ──────────────────────────────────────────────────────────────
RESULTS_DIR = Path("results")
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# Farben (konsistent für alle Diagramme)
COLORS = {
    "SAM":     "#2196F3",   # Blau
    "SLS":     "#4CAF50",   # Grün
    "OpenFaaS":"#FF9800",   # Orange
}

# ── Rohdaten ───────────────────────────────────────────────────────────────────

# t_first: gemessen von k6 (http_req_duration des einzelnen Cold-Start-Requests)
T_FIRST = {
    "SAM":      [536.08, 479.76, 544.30, 519.60, 492.34],
    "SLS":      [491.42, 539.37, 227.01, 462.83, 566.00],
    "OpenFaaS": [ 59.88,  59.99,  68.84,  53.90,  49.16],
}

# initDuration: aus AWS CloudWatch (nur Lambda, OpenFaaS = None)
INIT_DURATION = {
    "SAM":      [214.03, 218.18, 243.33, 216.35, 217.09],
    "SLS":      [218.12, 259.57, 216.34, 214.29, 256.59],
    "OpenFaaS": [None, None, None, None, None],
}

# p50_warm: Platzhalter – wird nach T2 befüllt
# Sobald T2-Ergebnisse vorliegen, hier eintragen:
P50_WARM = {
    "SAM":      None,   # z.B. 45.2
    "SLS":      None,   # z.B. 47.8
    "OpenFaaS": None,   # z.B. 28.3
}

FRAMEWORKS = ["SAM", "SLS", "OpenFaaS"]

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────

def stats(values):
    """Berechnet Kennzahlen für eine Liste von Werten."""
    arr = np.array(values)
    return {
        "mean": np.mean(arr),
        "median": np.median(arr),
        "std": np.std(arr, ddof=1),
        "min": np.min(arr),
        "max": np.max(arr),
        "cv": np.std(arr, ddof=1) / np.mean(arr),
        "n": len(arr),
    }

def delta_cold(t_first_list, p50_warm):
    """Berechnet ∆tcold = t_first - p50_warm."""
    if p50_warm is None:
        return None
    return [t - p50_warm for t in t_first_list]

# ── Auswertung ─────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "="*65)
    print("  VLP – T4 Cold-Start Auswertung")
    print("="*65)

    for fw in FRAMEWORKS:
        t = T_FIRST[fw]
        s = stats(t)
        init = [x for x in INIT_DURATION[fw] if x is not None]

        print(f"\n{'─'*40}")
        print(f"  {fw}")
        print(f"{'─'*40}")
        print(f"  t_first  (ms):")
        print(f"    Werte:    {[round(x,2) for x in t]}")
        print(f"    Ø:        {s['mean']:.2f} ms")
        print(f"    Median:   {s['median']:.2f} ms")
        print(f"    σ:        {s['std']:.2f} ms")
        print(f"    CV:       {s['cv']:.3f}  {'✅' if s['cv'] < 0.15 else '⚠️  > 0.15'}")
        print(f"    Min/Max:  {s['min']:.2f} / {s['max']:.2f} ms")

        if init:
            si = stats(init)
            print(f"  initDuration (ms):")
            print(f"    Werte:    {[round(x,2) for x in init]}")
            print(f"    Ø:        {si['mean']:.2f} ms")
            print(f"    σ:        {si['std']:.2f} ms")
        else:
            print(f"  initDuration: n/a (kein Scale-to-Zero)")

        if P50_WARM[fw] is not None:
            dc = delta_cold(t, P50_WARM[fw])
            print(f"  ∆tcold = t_first − p50_warm ({P50_WARM[fw]} ms):")
            print(f"    Werte:    {[round(x,2) for x in dc]}")
            print(f"    Ø:        {np.mean(dc):.2f} ms")
        else:
            print(f"  ∆tcold: ⏳ nach T2 berechnen (p50_warm fehlt noch)")

    print("\n" + "="*65)

# ── Diagramm 1: Balkendiagramm t_first ────────────────────────────────────────

def plot_t_first_bar():
    fig, ax = plt.subplots(figsize=(9, 5))

    means  = [np.mean(T_FIRST[fw]) for fw in FRAMEWORKS]
    stds   = [np.std(T_FIRST[fw], ddof=1) for fw in FRAMEWORKS]
    colors = [COLORS[fw] for fw in FRAMEWORKS]
    x      = np.arange(len(FRAMEWORKS))

    bars = ax.bar(x, means, yerr=stds, capsize=6,
                  color=colors, alpha=0.85, width=0.5,
                  error_kw={"linewidth": 1.5, "ecolor": "black"})

    # Werte über den Balken
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + std + 8,
                f"{mean:.1f} ms",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(["AWS SAM", "Serverless FW", "OpenFaaS"], fontsize=11)
    ax.set_ylabel("t_first – Antwortzeit (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start: Mittlere Antwortzeit (t_first) ± σ\n"
                 "je Framework, n=5 Wiederholungen", fontsize=12)
    ax.set_ylim(0, max(means) * 1.35)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    path = FIGURES_DIR / "t4_t_first_bar.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ Gespeichert: {path}")
    plt.close()

# ── Diagramm 2: Boxplot t_first ───────────────────────────────────────────────

def plot_t_first_boxplot():
    fig, ax = plt.subplots(figsize=(9, 5))

    data   = [T_FIRST[fw] for fw in FRAMEWORKS]
    labels = ["AWS SAM", "Serverless FW", "OpenFaaS"]
    colors = [COLORS[fw] for fw in FRAMEWORKS]

    bp = ax.boxplot(data, patch_artist=True, notch=False,
                    medianprops={"color": "black", "linewidth": 2},
                    whiskerprops={"linewidth": 1.5},
                    capprops={"linewidth": 1.5},
                    flierprops={"marker": "o", "markersize": 5})

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    # Einzelne Datenpunkte einzeichnen
    for i, (fw, color) in enumerate(zip(FRAMEWORKS, colors), start=1):
        y = T_FIRST[fw]
        x = np.random.normal(i, 0.04, size=len(y))
        ax.scatter(x, y, color=color, alpha=0.9, zorder=3, s=40,
                   edgecolors="black", linewidths=0.5)

    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("t_first – Antwortzeit (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start: Verteilung der Antwortzeiten (t_first)\n"
                 "je Framework, n=5 Wiederholungen", fontsize=12)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    path = FIGURES_DIR / "t4_t_first_boxplot.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ Gespeichert: {path}")
    plt.close()

# ── Diagramm 3: initDuration Balken (nur Lambda) ──────────────────────────────

def plot_init_duration_bar():
    fig, ax = plt.subplots(figsize=(7, 5))

    lambda_fws = ["SAM", "SLS"]
    means  = [np.mean(INIT_DURATION[fw]) for fw in lambda_fws]
    stds   = [np.std(INIT_DURATION[fw], ddof=1) for fw in lambda_fws]
    colors = [COLORS[fw] for fw in lambda_fws]
    x      = np.arange(len(lambda_fws))

    bars = ax.bar(x, means, yerr=stds, capsize=6,
                  color=colors, alpha=0.85, width=0.4,
                  error_kw={"linewidth": 1.5, "ecolor": "black"})

    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + std + 3,
                f"{mean:.1f} ms",
                ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(["AWS SAM", "Serverless FW"], fontsize=11)
    ax.set_ylabel("initDuration (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start: Lambda-Initialisierungszeit (initDuration) ± σ\n"
                 "AWS CloudWatch REPORT, n=5 Wiederholungen", fontsize=12)
    ax.set_ylim(0, max(means) * 1.4)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    # OpenFaaS als Anmerkung
    ax.text(0.98, 0.95,
            "OpenFaaS: n/a\n(kein Scale-to-Zero)",
            transform=ax.transAxes,
            ha="right", va="top", fontsize=9,
            color=COLORS["OpenFaaS"],
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=COLORS["OpenFaaS"], alpha=0.8))

    plt.tight_layout()
    path = FIGURES_DIR / "t4_init_duration_bar.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ Gespeichert: {path}")
    plt.close()

# ── Diagramm 4: Streudiagramm t_first pro Run ─────────────────────────────────

def plot_t_first_scatter():
    fig, ax = plt.subplots(figsize=(9, 5))

    runs = [1, 2, 3, 4, 5]
    offsets = {"SAM": -0.15, "SLS": 0.0, "OpenFaaS": 0.15}

    for fw in FRAMEWORKS:
        x = [r + offsets[fw] for r in runs]
        ax.scatter(x, T_FIRST[fw], color=COLORS[fw],
                   s=80, zorder=3, label=fw,
                   edgecolors="black", linewidths=0.5)
        ax.plot(x, T_FIRST[fw], color=COLORS[fw],
                linewidth=1, alpha=0.4, linestyle="--")

    ax.set_xticks(runs)
    ax.set_xticklabels([f"Run {r}" for r in runs], fontsize=10)
    ax.set_ylabel("t_first – Antwortzeit (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start: t_first je Run und Framework", fontsize=12)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    path = FIGURES_DIR / "t4_t_first_scatter.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ Gespeichert: {path}")
    plt.close()

# ── LaTeX-Tabelle generieren ───────────────────────────────────────────────────

def generate_latex_table():
    lines = []
    lines.append("% Tabelle T4 Cold-Start – automatisch generiert von analyze_t4.py")
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{T4 Cold-Start-Messungen: Antwortzeit (t\_first) und Lambda-Initialisierungszeit (initDuration), n=5 Wiederholungen je Framework}")
    lines.append(r"\label{tab:t4_results}")
    lines.append(r"\begin{tabular}{lrrrrr}")
    lines.append(r"\toprule")
    lines.append(r"Framework & $\bar{x}$ t\_first & $\sigma$ t\_first & $\bar{x}$ initDuration & $\sigma$ initDuration & CV \\")
    lines.append(r" & (ms) & (ms) & (ms) & (ms) & \\")
    lines.append(r"\midrule")

    for fw in FRAMEWORKS:
        t = T_FIRST[fw]
        st = stats(t)
        init = [x for x in INIT_DURATION[fw] if x is not None]

        if init:
            si = stats(init)
            init_mean = f"{si['mean']:.2f}"
            init_std  = f"{si['std']:.2f}"
        else:
            init_mean = r"n/a"
            init_std  = r"n/a"

        fw_label = {"SAM": "AWS SAM", "SLS": "Serverless FW", "OpenFaaS": "OpenFaaS"}[fw]
        cv_flag  = r"\checkmark" if st["cv"] < 0.15 else r"$\uparrow$"

        lines.append(
            f"{fw_label} & {st['mean']:.2f} & {st['std']:.2f} & "
            f"{init_mean} & {init_std} & {st['cv']:.3f} {cv_flag} \\\\"
        )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    latex = "\n".join(lines)
    path  = RESULTS_DIR / "t4_table.tex"
    with open(path, "w") as f:
        f.write(latex)
    print(f"  ✅ LaTeX-Tabelle: {path}")
    print("\n" + latex)

# ── Hauptprogramm ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔍 Berechne Kennzahlen...")
    print_summary()

    print("\n📊 Erstelle Diagramme...")
    plot_t_first_bar()
    plot_t_first_boxplot()
    plot_init_duration_bar()
    plot_t_first_scatter()

    print("\n📄 Generiere LaTeX-Tabelle...")
    generate_latex_table()

    print("\n✅ Auswertung abgeschlossen.")
    print(f"   Diagramme: {FIGURES_DIR}/")
    print(f"   Tabelle:   {RESULTS_DIR}/t4_table.tex")
    print("\n⏳ Sobald T2-Ergebnisse vorliegen:")
    print("   P50_WARM in analyze_t4.py befüllen → ∆tcold wird berechnet")
