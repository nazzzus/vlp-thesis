#!/usr/bin/env python3
"""
analyze_t2.py – T2 Konstantlast Auswertung
Erzeugt:
  - Konsolentabelle mit Kennzahlen
  - results/t2_summary.csv
  - results/t2_boxplot.pdf  (thesis-ready, LaTeX-kompatibel)
  - results/t2_latex_table.tex
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import csv

# ── Konfiguration ──────────────────────────────────────────────────────────────
RESULTS_DIR = Path("results")
OUTPUT_DIR  = Path("results")

FRAMEWORKS = {
    "SAM":     ["t2_sam_run1.json",  "t2_sam_run2.json",  "t2_sam_run3.json"],
    "SLS":     ["t2_sls_run1.json",  "t2_sls_run2.json",  "t2_sls_run3.json"],
    "OpenFaaS":["t2_faas_run1.json", "t2_faas_run2.json", "t2_faas_run3.json"],
}

COLORS = {
    "SAM":      "#2196F3",
    "SLS":      "#FF9800",
    "OpenFaaS": "#4CAF50",
}

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────
def load_durations(filepath, method=None):
    """Liest alle http_req_duration Werte aus einer k6 JSON-Datei."""
    durations = []
    path = RESULTS_DIR / filepath
    if not path.exists():
        print(f"  ⚠️  Datei nicht gefunden: {path}", file=sys.stderr)
        return durations
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
                if (d.get("type") == "Point"
                        and d.get("metric") == "http_req_duration"):
                    tags = d["data"].get("tags", {})
                    # Nur erfolgreiche Requests
                    if tags.get("expected_response") != "true":
                        continue
                    if method and tags.get("method") != method:
                        continue
                    val = d["data"]["value"]
                    # Ausreißer > 30s ignorieren (Timeouts/Anomalien)
                    if val < 30000:
                        durations.append(val)
            except (json.JSONDecodeError, KeyError):
                pass
    return durations

def stats(data):
    """Berechnet Kennzahlen für eine Liste von Latenzen (ms)."""
    if not data:
        return {}
    a = np.array(data)
    return {
        "n":    len(a),
        "avg":  np.mean(a),
        "med":  np.median(a),
        "p90":  np.percentile(a, 90),
        "p95":  np.percentile(a, 95),
        "p99":  np.percentile(a, 99),
        "min":  np.min(a),
        "max":  np.max(a),
        "std":  np.std(a),
    }

# ── Daten laden ────────────────────────────────────────────────────────────────
print("Lade Rohdaten...")
all_data   = {}   # fw -> alle Messungen (alle 3 Runs kombiniert)
run_data   = {}   # fw -> [run1_data, run2_data, run3_data]
get_data   = {}   # fw -> GET-Latenzen
post_data  = {}   # fw -> POST-Latenzen

for fw, files in FRAMEWORKS.items():
    combined = []
    runs     = []
    gets     = []
    posts    = []
    for f in files:
        d_all  = load_durations(f)
        d_get  = load_durations(f, method="GET")
        d_post = load_durations(f, method="POST")
        combined.extend(d_all)
        runs.append(d_all)
        gets.extend(d_get)
        posts.extend(d_post)
        print(f"  {fw} {f}: {len(d_all)} Messpunkte")
    all_data[fw]  = combined
    run_data[fw]  = runs
    get_data[fw]  = gets
    post_data[fw] = posts

# ── Konsolentabelle ────────────────────────────────────────────────────────────
print("\n" + "═"*70)
print(f"{'Framework':<12} {'n':>7} {'avg':>8} {'med':>8} {'p90':>8} {'p95':>8} {'p99':>8}")
print("─"*70)
summary_rows = []
for fw in ["SAM", "SLS", "OpenFaaS"]:
    s = stats(all_data[fw])
    if s:
        print(f"{fw:<12} {s['n']:>7} {s['avg']:>7.1f}ms {s['med']:>7.1f}ms "
              f"{s['p90']:>7.1f}ms {s['p95']:>7.1f}ms {s['p99']:>7.1f}ms")
        summary_rows.append({
            "framework": fw,
            **{k: round(v, 2) for k, v in s.items()}
        })
print("═"*70)

# GET vs POST
print(f"\n{'Framework':<12} {'GET avg':>10} {'GET p95':>10} {'POST avg':>10} {'POST p95':>10}")
print("─"*55)
for fw in ["SAM", "SLS", "OpenFaaS"]:
    sg = stats(get_data[fw])
    sp = stats(post_data[fw])
    if sg and sp:
        print(f"{fw:<12} {sg['avg']:>9.1f}ms {sg['p95']:>9.1f}ms "
              f"{sp['avg']:>9.1f}ms {sp['p95']:>9.1f}ms")

# ── CSV speichern ──────────────────────────────────────────────────────────────
csv_path = OUTPUT_DIR / "t2_summary.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["framework","n","avg","med","p90","p95","p99","min","max","std"])
    writer.writeheader()
    writer.writerows(summary_rows)
print(f"\n✅ CSV gespeichert: {csv_path}")

# ── Boxplot ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":     "serif",
    "font.size":       11,
    "axes.titlesize":  12,
    "axes.labelsize":  11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi":      150,
})

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

def make_boxplot(ax, data_dict, title, ylabel="Latenz (ms)"):
    fw_names = ["SAM", "SLS", "OpenFaaS"]
    data     = [data_dict[fw] for fw in fw_names]
    colors   = [COLORS[fw] for fw in fw_names]

    bp = ax.boxplot(
        data,
        patch_artist=True,
        notch=False,
        showfliers=True,
        flierprops=dict(marker="o", markersize=2, alpha=0.3),
        medianprops=dict(color="black", linewidth=2),
        whiskerprops=dict(linewidth=1.2),
        capprops=dict(linewidth=1.2),
        widths=0.5,
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    # p95-Linie als Annotation
    for i, (fw, d) in enumerate(zip(fw_names, data), 1):
        if d:
            p95 = np.percentile(d, 95)
            ax.hlines(p95, i-0.35, i+0.35, colors="red",
                      linewidths=1.0, linestyles="--", alpha=0.7)

    ax.set_xticks(range(1, len(fw_names)+1))
    ax.set_xticklabels(fw_names)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_ylim(bottom=0)

    # Legende für p95
    p95_line = mpatches.Patch(color="red", alpha=0.7, label="p95")
    ax.legend(handles=[p95_line], fontsize=9, loc="upper left")

make_boxplot(axes[0], all_data,  "T2 – Gesamtlatenz (alle Requests)")
make_boxplot(axes[1], get_data,  "T2 – GET /vehicles Latenz")

fig.suptitle("T2 Konstantlast (10 VUs, 3×10 min) – Latenzverteilung je Framework",
             fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()

plot_path = OUTPUT_DIR / "t2_boxplot.pdf"
plt.savefig(plot_path, bbox_inches="tight", format="pdf")
print(f"✅ Boxplot gespeichert: {plot_path}")

# Auch als PNG für schnelle Vorschau
png_path = OUTPUT_DIR / "t2_boxplot.png"
plt.savefig(png_path, bbox_inches="tight", format="png", dpi=150)
print(f"✅ PNG gespeichert: {png_path}")
plt.close()

# ── Run-Vergleich Plot (Stabilität) ───────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(10, 5))

x = np.arange(3)
width = 0.25
labels = ["Run 1", "Run 2", "Run 3"]

for i, fw in enumerate(["SAM", "SLS", "OpenFaaS"]):
    avgs = [stats(r)["avg"] if r else 0 for r in run_data[fw]]
    p95s = [stats(r)["p95"] if r else 0 for r in run_data[fw]]
    bars = ax2.bar(x + i*width, avgs, width, label=f"{fw} (avg)",
                   color=COLORS[fw], alpha=0.8)
    ax2.plot(x + i*width, p95s, "o--", color=COLORS[fw],
             linewidth=1.5, markersize=5, label=f"{fw} (p95)")

ax2.set_xticks(x + width)
ax2.set_xticklabels(labels)
ax2.set_ylabel("Latenz (ms)")
ax2.set_title("T2 – Avg & p95 Latenz je Run und Framework")
ax2.legend(ncol=2, fontsize=9)
ax2.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()

run_plot_path = OUTPUT_DIR / "t2_runs_comparison.pdf"
plt.savefig(run_plot_path, bbox_inches="tight", format="pdf")
run_png_path  = OUTPUT_DIR / "t2_runs_comparison.png"
plt.savefig(run_png_path,  bbox_inches="tight", format="png", dpi=150)
print(f"✅ Run-Vergleich gespeichert: {run_plot_path}")
plt.close()

# ── LaTeX-Tabelle ──────────────────────────────────────────────────────────────
latex_path = OUTPUT_DIR / "t2_latex_table.tex"

def fmt(v):
    return f"{v:.1f}"

with open(latex_path, "w") as f:
    f.write("% T2 Konstantlast – Latenz-Kennzahlen\n")
    f.write("% Automatisch generiert von analyze_t2.py\n\n")
    f.write("\\begin{table}[htbp]\n")
    f.write("  \\centering\n")
    f.write("  \\caption{T2 Konstantlast: Latenz-Kennzahlen je Framework (alle Requests, 10 VUs, 3$\\times$10\\,min)}\n")
    f.write("  \\label{tab:t2_latenz}\n")
    f.write("  \\begin{tabular}{lrrrrrrr}\n")
    f.write("    \\toprule\n")
    f.write("    Framework & $n$ & Avg (ms) & Median (ms) & p90 (ms) & p95 (ms) & p99 (ms) & Std (ms) \\\\\n")
    f.write("    \\midrule\n")
    for fw in ["SAM", "SLS", "OpenFaaS"]:
        s = stats(all_data[fw])
        if s:
            f.write(f"    {fw} & {s['n']:,} & {fmt(s['avg'])} & {fmt(s['med'])} & "
                    f"{fmt(s['p90'])} & {fmt(s['p95'])} & {fmt(s['p99'])} & {fmt(s['std'])} \\\\\n")
    f.write("    \\bottomrule\n")
    f.write("  \\end{tabular}\n")
    f.write("\\end{table}\n\n")

    # GET vs POST Tabelle
    f.write("% T2 – GET vs POST Latenz\n\n")
    f.write("\\begin{table}[htbp]\n")
    f.write("  \\centering\n")
    f.write("  \\caption{T2 Konstantlast: GET vs.\\ POST Latenz je Framework}\n")
    f.write("  \\label{tab:t2_get_post}\n")
    f.write("  \\begin{tabular}{lrrrr}\n")
    f.write("    \\toprule\n")
    f.write("    Framework & GET avg (ms) & GET p95 (ms) & POST avg (ms) & POST p95 (ms) \\\\\n")
    f.write("    \\midrule\n")
    for fw in ["SAM", "SLS", "OpenFaaS"]:
        sg = stats(get_data[fw])
        sp = stats(post_data[fw])
        if sg and sp:
            f.write(f"    {fw} & {fmt(sg['avg'])} & {fmt(sg['p95'])} & "
                    f"{fmt(sp['avg'])} & {fmt(sp['p95'])} \\\\\n")
    f.write("    \\bottomrule\n")
    f.write("  \\end{tabular}\n")
    f.write("\\end{table}\n")

print(f"✅ LaTeX-Tabellen gespeichert: {latex_path}")
print("\n✅ T2-Auswertung abgeschlossen.")
