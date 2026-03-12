#!/usr/bin/env python3
"""
analyze_t4.py – T4 Cold-Start Auswertung
VLP Serverless Framework Vergleich – Bachelorarbeit

Liest t4_*.json aus results/, extrahiert http_req_waiting (TTFB),
berechnet Δt_cold = t_first - p50_warm, erstellt Diagramme und LaTeX-Tabelle.

Ausführung:
    pip install matplotlib numpy
    python3 analyze_t4.py
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Konfiguration ──────────────────────────────────────────────────────────────
RESULTS_DIR = Path("results")
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

COLORS = {
    "SAM":      "#2196F3",
    "SLS":      "#4CAF50",
    "OpenFaaS": "#FF9800",
}

# p50_warm aus T2-Ergebnissen (M10, aggregiert)
P50_WARM = {
    "SAM":      48.5,
    "SLS":      53.0,
    "OpenFaaS": 35.6,
}

FRAMEWORKS = ["SAM", "SLS", "OpenFaaS"]
FW_FILES   = {"SAM": "sam", "SLS": "sls", "OpenFaaS": "faas"}
FW_LABELS  = {"SAM": "AWS SAM", "SLS": "Serverless FW", "OpenFaaS": "OpenFaaS"}
RUNS = 5

# ── JSON-Extraktion ────────────────────────────────────────────────────────────

def extract_metric(filepath, metric_name):
    """Extrahiert den ersten Point-Wert einer Metrik aus einer k6-JSON-Datei."""
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("metric") == metric_name and obj.get("type") == "Point":
                return obj["data"]["value"]
    return None

def load_t_first(fw_key):
    """Lädt http_req_waiting für alle 5 Runs eines Frameworks."""
    values = []
    for run in range(1, RUNS + 1):
        path = RESULTS_DIR / f"t4_{FW_FILES[fw_key]}_run{run}.json"
        if not path.exists():
            print(f"  ⚠️  Nicht gefunden: {path}")
            continue
        val = extract_metric(path, "http_req_waiting")
        if val is None:
            val = extract_metric(path, "http_req_duration")
        if val is not None:
            values.append(val)
        else:
            print(f"  ⚠️  Kein Messwert in {path}")
    return values

# ── Statistik ─────────────────────────────────────────────────────────────────

def stats(values):
    arr = np.array(values)
    return {
        "mean":   np.mean(arr),
        "median": np.median(arr),
        "std":    np.std(arr, ddof=1) if len(arr) > 1 else 0.0,
        "min":    np.min(arr),
        "max":    np.max(arr),
        "cv":     (np.std(arr, ddof=1) / np.mean(arr)) if len(arr) > 1 else 0.0,
        "n":      len(arr),
    }

# ── Daten laden ────────────────────────────────────────────────────────────────

T_FIRST = {}
for fw in FRAMEWORKS:
    T_FIRST[fw] = load_t_first(fw)

# Ausreißer-bereinigung: t_first < 2×p50_warm → Instanz war noch warm
T_FIRST_CLEAN = {}
OUTLIERS = {}
for fw in FRAMEWORKS:
    clean = [v for v in T_FIRST[fw] if v >= 2 * P50_WARM[fw]]
    outlier = [v for v in T_FIRST[fw] if v < 2 * P50_WARM[fw]]
    T_FIRST_CLEAN[fw] = clean
    OUTLIERS[fw] = outlier

DELTA_COLD = {fw: [v - P50_WARM[fw] for v in T_FIRST_CLEAN[fw]]
              for fw in FRAMEWORKS}

# ── Zusammenfassung ────────────────────────────────────────────────────────────

print("\n" + "="*65)
print("  VLP – T4 Cold-Start Auswertung (M10, frische JSONs)")
print("  Primärmetrik: http_req_waiting (TTFB)")
print("="*65)

for fw in FRAMEWORKS:
    t = T_FIRST[fw]
    if not t:
        print(f"\n{fw}: keine Daten")
        continue
    s = stats(t)
    p50 = P50_WARM[fw]

    print(f"\n── {fw} (p50_warm = {p50} ms) {'─'*35}")
    print(f"  {'Run':<5} {'waiting (ms)':>14} {'Δt_cold (ms)':>14}")
    print(f"  {'-'*5} {'-'*14} {'-'*14}")
    for i, v in enumerate(t, 1):
        delta = v - p50
        outlier = " ⚠️  Ausreißer" if v < 2 * p50 else ""
        print(f"  {i:<5} {v:>13.1f}ms {delta:>13.1f}ms{outlier}")

    print(f"\n  Aggregiert (n={s['n']}):")
    print(f"    Ø waiting:  {s['mean']:.1f} ms")
    print(f"    σ:          {s['std']:.1f} ms")
    print(f"    CV:         {s['cv']:.3f}  {'✅' if s['cv'] < 0.15 else '⚠️  > 0.15'}")
    print(f"    Min/Max:    {s['min']:.1f} / {s['max']:.1f} ms")

    dc = DELTA_COLD[fw]
    if dc:
        print(f"    Ø Δt_cold (bereinigt, n={len(dc)}): {np.mean(dc):.1f} ms  σ={np.std(dc):.1f} ms")
    if OUTLIERS[fw]:
        print(f"    Ausreißer: {[round(v,1) for v in OUTLIERS[fw]]}")

print("\n" + "="*65)
print("  Zusammenfassung: Δt_cold (bereinigt)")
print("="*65)
print(f"  {'Framework':<14} {'Ø Δt_cold':>10} {'σ':>8} {'Min':>8} {'Max':>8}")
print(f"  {'-'*14} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
for fw in FRAMEWORKS:
    d = DELTA_COLD[fw]
    if d:
        print(f"  {fw:<14} {np.mean(d):>9.1f}ms {np.std(d):>7.1f}ms "
              f"{min(d):>7.1f}ms {max(d):>7.1f}ms")
print("="*65)

# ── Diagramm 1: Balkendiagramm Δt_cold ────────────────────────────────────────

def plot_delta_cold_bar():
    fig, ax = plt.subplots(figsize=(9, 5))
    means  = [np.mean(DELTA_COLD[fw]) if DELTA_COLD[fw] else 0 for fw in FRAMEWORKS]
    stds   = [np.std(DELTA_COLD[fw]) if len(DELTA_COLD[fw]) > 1 else 0 for fw in FRAMEWORKS]
    colors = [COLORS[fw] for fw in FRAMEWORKS]
    x      = np.arange(len(FRAMEWORKS))

    bars = ax.bar(x, means, yerr=stds, capsize=6,
                  color=colors, alpha=0.85, width=0.5,
                  error_kw={"linewidth": 1.5, "ecolor": "black"})

    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + std + 5,
                f"{mean:.1f} ms",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([FW_LABELS[fw] for fw in FRAMEWORKS], fontsize=11)
    ax.set_ylabel("Δt_cold (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start-Overhead Δt_cold = t_first − p50_warm\n"
                 "Mittelwert ± σ, n=5 Wiederholungen (bereinigt)", fontsize=12)
    ax.set_ylim(0, max(means) * 1.35)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    path = FIGURES_DIR / "t4_cold_start.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ {path}")
    plt.close()

# ── Diagramm 2: Scatter t_first je Run ────────────────────────────────────────

def plot_t_first_scatter():
    fig, ax = plt.subplots(figsize=(9, 5))
    offsets = {"SAM": -0.15, "SLS": 0.0, "OpenFaaS": 0.15}
    runs = list(range(1, RUNS + 1))

    for fw in FRAMEWORKS:
        t = T_FIRST[fw]
        if not t:
            continue
        x = [r + offsets[fw] for r in runs[:len(t)]]
        ax.scatter(x, t, color=COLORS[fw], s=80, zorder=3,
                   label=FW_LABELS[fw], edgecolors="black", linewidths=0.5)
        ax.plot(x, t, color=COLORS[fw], linewidth=1, alpha=0.4, linestyle="--")

    ax.set_xticks(runs)
    ax.set_xticklabels([f"Run {r}" for r in runs], fontsize=10)
    ax.set_ylabel("t_first – http_req_waiting (ms)", fontsize=11)
    ax.set_title("T4 Cold-Start: t_first je Run und Framework", fontsize=12)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    path = FIGURES_DIR / "t4_t_first_scatter.pdf"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(str(path).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"  ✅ {path}")
    plt.close()

# ── LaTeX-Tabelle ──────────────────────────────────────────────────────────────

def generate_latex_table():
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{T4 -- Cold-Start-Einzelmessungen ($t_{\mathrm{first}}$ und $\Delta t_{\mathrm{cold}}$)}",
        r"\label{tab:t4-einzelmessungen}",
        r"\begin{tabularx}{\textwidth}{llXXX}",
        r"\toprule",
        r"\textbf{Framework} & \textbf{Run} & \textbf{$t_{\mathrm{first}}$~(ms)} & "
        r"\textbf{$p_{50}^{\mathrm{warm}}$~(ms)} & \textbf{$\Delta t_{\mathrm{cold}}$~(ms)} \\",
        r"\midrule",
    ]
    for fw in FRAMEWORKS:
        t = T_FIRST[fw]
        p50 = P50_WARM[fw]
        fw_label = FW_LABELS[fw].replace(" ", "~")
        for i, v in enumerate(t, 1):
            delta = v - p50
            outlier = r"$^{\dagger}$" if v < 2 * p50 else ""
            prefix = fw_label if i == 1 else ""
            lines.append(f"    {prefix} & {i}{outlier} & {v:.1f} & {p50} & {delta:.1f} \\\\")
        lines.append(r"    \midrule")

    lines += [
        r"    \multicolumn{5}{l}{\small $^{\dagger}$ Ausreißer: Lambda-Instanz noch warm; aus bereinigtem Mittelwert ausgeschlossen.} \\",
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    latex = "\n".join(lines)
    path = RESULTS_DIR / "t4_latex_table.tex"
    with open(path, "w") as f:
        f.write(latex)
    print(f"  ✅ {path}")

# ── Main ───────────────────────────────────────────────────────────────────────

print("\n📊 Erstelle Diagramme...")
plot_delta_cold_bar()
plot_t_first_scatter()

print("\n📄 Generiere LaTeX-Tabelle...")
generate_latex_table()

print("\n✅ Fertig. Diagramme in:", FIGURES_DIR)
