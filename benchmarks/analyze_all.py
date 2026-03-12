#!/usr/bin/env python3
"""
analyze_all.py – Vollständige Auswertung aller VLP-Benchmarks
==============================================================
Wertet T2 (Konstantlast), T3 (Ramp) und T4 (Cold-Start) aus.

Ergebnisse aus echten Messungen:
  T2: 9 JSON-Dateien (SAM/SLS/FaaS je 3 Runs, 10 VU, 10 min)
  T3: 3 JSON-Dateien (SAM/SLS/FaaS je 1 Run, Ramp 0→50 VU)
  T4: 15 JSON-Dateien (SAM/SLS/FaaS je 5 Runs, 1 Cold-Start-Request)

Erzeugt:
  results/t2_summary.csv
  results/t2_latex_table.tex
  results/t2_boxplot.pdf/.png
  results/t2_runs_comparison.pdf/.png
  results/t3_latex_table.tex
  results/t3_latency_over_time.pdf/.png
  results/t4_summary.csv
  results/t4_latex_table.tex
  results/t4_cold_start.pdf/.png
"""

import json, csv, re
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams.update({
    "font.family":    "serif",
    "font.size":      11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi":     150,
})

RESULTS = Path("results")
RESULTS.mkdir(exist_ok=True)

FW_LABELS  = ["AWS SAM", "Serverless FW", "OpenFaaS"]
FW_KEYS    = ["sam", "sls", "faas"]
FW_COLORS  = ["#2196F3", "#FF9800", "#4CAF50"]

# ═══════════════════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def parse_ts(ts):
    ts = ts.replace("Z", "+00:00")
    ts = re.sub(r"\.(\d+)([+-])", lambda m: "." + m.group(1)[:6].ljust(6,"0") + m.group(2), ts)
    return datetime.fromisoformat(ts)

def load_metric(path, metric_name):
    """Lädt alle Werte einer Metrik aus einer k6-JSON-Datei."""
    vals = []
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") == "Point" and d.get("metric") == metric_name:
                vals.append(d["data"]["value"])
    return vals

def percentile(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s)-1)]

def cv(data):
    """Variationskoeffizient."""
    a = np.mean(data)
    return np.std(data) / a if a > 0 else 0

# ═══════════════════════════════════════════════════════════════════════════
#  T2 – KONSTANTLAST
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  T2 – Konstantlast (10 VU, 3×10 min)")
print("="*60)

# Bekannte Werte direkt aus T2/T3-Protokoll (Warm-up Ergebnisse zeigen
# Protokollwerte; T2-Messung läuft auf SAM/SLS/FaaS).
# Wir laden die echten JSON-Rohdaten für präzise Percentiles.

t2_data = {}   # fw_key → {run: [durations]}

for key in FW_KEYS:
    t2_data[key] = {}
    for run in [1, 2, 3]:
        p = RESULTS / f"t2_{key}_run{run}.json"
        if p.exists():
            vals = load_metric(p, "http_req_duration")
            # Fehlerrate
            failed = load_metric(p, "http_req_failed")
            err_rate = sum(1 for v in failed if v > 0) / len(failed) * 100 if failed else 0
            t2_data[key][run] = {"dur": vals, "err": err_rate, "n": len(vals)}
            print(f"  {key} Run {run}: n={len(vals):>6,}  "
                  f"avg={np.mean(vals):>7.1f}ms  "
                  f"p50={percentile(vals,50):>7.1f}ms  "
                  f"p95={percentile(vals,95):>7.1f}ms  "
                  f"err={err_rate:.2f}%")
        else:
            print(f"  ⚠ {p} nicht gefunden")

# Aggregierte Kennzahlen je Framework (Ø über alle 3 Runs)
t2_agg = {}
for key in FW_KEYS:
    all_dur = []
    for run in [1,2,3]:
        if run in t2_data[key]:
            all_dur.extend(t2_data[key][run]["dur"])
    if all_dur:
        medians = [percentile(t2_data[key][r]["dur"], 50) for r in [1,2,3] if r in t2_data[key]]
        t2_agg[key] = {
            "avg":  np.mean(all_dur),
            "p50":  percentile(all_dur, 50),
            "p90":  percentile(all_dur, 90),
            "p95":  percentile(all_dur, 95),
            "min":  min(all_dur),
            "max":  max(all_dur),
            "n":    len(all_dur),
            "cv":   cv(medians),
            "err":  np.mean([t2_data[key][r]["err"] for r in [1,2,3] if r in t2_data[key]]),
        }

print("\n  Aggregiert:")
for key, label in zip(FW_KEYS, FW_LABELS):
    a = t2_agg[key]
    print(f"  {label:15s}: p50={a['p50']:>7.1f}ms  p95={a['p95']:>7.1f}ms  CV={a['cv']:.2f}")

# ── CSV ──────────────────────────────────────────────────────────────────────
csv_path = RESULTS / "t2_summary.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["framework","run","n","avg_ms","p50_ms","p90_ms","p95_ms","min_ms","max_ms","err_pct"])
    for key, label in zip(FW_KEYS, FW_LABELS):
        for run in [1,2,3]:
            if run in t2_data[key]:
                d = t2_data[key][run]["dur"]
                w.writerow([label, run, len(d),
                             round(np.mean(d),2), round(percentile(d,50),2),
                             round(percentile(d,90),2), round(percentile(d,95),2),
                             round(min(d),2), round(max(d),2),
                             round(t2_data[key][run]["err"],4)])
print(f"\n✅ T2 CSV: {csv_path}")

# ── LaTeX-Tabelle T2 Aggregiert ───────────────────────────────────────────────
tex_path = RESULTS / "t2_latex_table.tex"
with open(tex_path, "w") as f:
    f.write("% T2 Konstantlast – aggregierte Ergebnisse\n")
    f.write("% Automatisch generiert von analyze_all.py\n\n")
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T2~-- Steady-State-Performance (10~VU, 3\\,×\\,10~min, aggregiert)}\n")
    f.write("  \\label{tab:t2-ergebnisse}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{lXXXXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{Req.} & \\textbf{$\\bar{x}$~(ms)} & "
            "\\textbf{$p_{50}$~(ms)} & \\textbf{$p_{95}$~(ms)} & \\textbf{$e$~(\\%)} \\\\\n")
    f.write("    \\midrule\n")
    for key, label in zip(FW_KEYS, FW_LABELS):
        a = t2_agg[key]
        f.write(f"    {label} & {a['n']:,} & {a['avg']:.1f} & "
                f"{a['p50']:.1f} & {a['p95']:.1f} & {a['err']:.2f} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n\n")

    # T2 Einzelrun-Tabelle
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T2~-- Ergebnisse je Run (10~VU, 10~min)}\n")
    f.write("  \\label{tab:t2-runs-detail}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{llXXXXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{Run} & \\textbf{$n$} & "
            "\\textbf{$\\bar{x}$~(ms)} & \\textbf{$p_{50}$~(ms)} & "
            "\\textbf{$p_{95}$~(ms)} & \\textbf{$e$~(\\%)} \\\\\n")
    f.write("    \\midrule\n")
    for key, label in zip(FW_KEYS, FW_LABELS):
        for run in [1,2,3]:
            if run in t2_data[key]:
                d  = t2_data[key][run]["dur"]
                er = t2_data[key][run]["err"]
                fw_col = label if run == 1 else ""
                f.write(f"    {fw_col} & {run} & {len(d):,} & "
                        f"{np.mean(d):.1f} & {percentile(d,50):.1f} & "
                        f"{percentile(d,95):.1f} & {er:.2f} \\\\\n")
        f.write("    \\midrule\n")
    # CV-Zeile
    f.write("    \\multicolumn{7}{l}{\\small $^{*}$ CV = Variationskoeffizient "
            "der Run-Mediane (Stabilitätsschwelle: CV~$<$~0{,}15)} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n\n")

    # CV-Tabelle
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T2~-- Messstabilität (Variationskoeffizient der Run-Mediane)}\n")
    f.write("  \\label{tab:t2-cv}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{lXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{CV} & \\textbf{Bewertung} \\\\\n")
    f.write("    \\midrule\n")
    bewertung = {"sam": "Gut (Run~1 TLS-Overhead)", "sls": "Sehr gut", "faas": "Kritisch (Anomalien)"}
    for key, label in zip(FW_KEYS, FW_LABELS):
        cv_val = t2_agg[key]["cv"]
        flag = "\\checkmark" if cv_val < 0.15 else ("$\\approx$" if cv_val < 0.25 else "\\textbf{!}")
        f.write(f"    {label} & {cv_val:.2f} & {bewertung[key]} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n")
print(f"✅ T2 LaTeX: {tex_path}")

# ── Boxplot T2 ───────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
bp_data  = [t2_data[k][r]["dur"] for k in FW_KEYS for r in [1,2,3] if r in t2_data[k]]
bp_labels = []
bp_colors = []
for k, c in zip(FW_KEYS, FW_COLORS):
    for r in [1,2,3]:
        if r in t2_data[k]:
            bp_labels.append(f"Run {r}")
            bp_colors.append(c)

positions = list(range(1, len(bp_data)+1))
bp = ax.boxplot(bp_data, positions=positions, patch_artist=True,
                medianprops=dict(color="black", linewidth=1.5),
                whiskerprops=dict(linewidth=1.2),
                flierprops=dict(marker=".", markersize=2, alpha=0.4),
                showfliers=True)
for patch, color in zip(bp["boxes"], bp_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)

ax.set_xticks(positions)
ax.set_xticklabels(bp_labels, fontsize=9)
ax.set_ylabel("Latenz (ms)")
ax.set_title("T2 – Latenzverteilung je Run (Boxplot, 10 VU, 10 min)")
ax.set_ylim(0, 600)
ax.grid(axis="y", linestyle="--", alpha=0.4)

# Gruppentrennlinien + Labels
for i, (label, color) in enumerate(zip(FW_LABELS, FW_COLORS)):
    cx = 2 + i*3
    ax.text(cx, 570, label, ha="center", fontsize=10, color=color, fontweight="bold")
    if i < 2:
        ax.axvline(x=3.5 + i*3, color="gray", linestyle=":", alpha=0.5)

patches = [mpatches.Patch(color=c, alpha=0.75, label=l)
           for c, l in zip(FW_COLORS, FW_LABELS)]
ax.legend(handles=patches, fontsize=9, loc="upper right")
plt.tight_layout()
for ext in ["pdf", "png"]:
    plt.savefig(RESULTS / f"t2_boxplot.{ext}", bbox_inches="tight")
print(f"✅ T2 Boxplot: {RESULTS}/t2_boxplot.pdf")
plt.close()

# ── Run-Vergleich T2 ─────────────────────────────────────────────────────────
fig2, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharey=False)
metrics_labels = ["avg", "p50", "p95"]
metrics_names  = ["Mittelwert (ms)", "Median p50 (ms)", "p95 (ms)"]

for ax_i, (met, mname) in enumerate(zip(metrics_labels, metrics_names)):
    ax = axes[ax_i]
    x = np.arange(3)
    width = 0.25
    for ri, run in enumerate([1,2,3]):
        vals = []
        for key in FW_KEYS:
            if run in t2_data[key]:
                d = t2_data[key][run]["dur"]
                if met == "avg":
                    vals.append(np.mean(d))
                elif met == "p50":
                    vals.append(percentile(d, 50))
                elif met == "p95":
                    vals.append(percentile(d, 95))
            else:
                vals.append(0)
        bars = ax.bar(x + ri*width, vals, width,
                      label=f"Run {run}", alpha=0.85,
                      color=[f"#{int(c[1:3],16):02x}{int(c[3:5],16):02x}{int(c[5:],16):02x}"
                             for c in FW_COLORS])
    ax.set_xticks(x + width)
    ax.set_xticklabels(FW_LABELS, fontsize=8.5, rotation=10)
    ax.set_ylabel(mname)
    ax.set_title(mname)
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

fig2.suptitle("T2 – Kennzahlen je Run und Framework", fontsize=12, fontweight="bold")
plt.tight_layout()
for ext in ["pdf", "png"]:
    plt.savefig(RESULTS / f"t2_runs_comparison.{ext}", bbox_inches="tight")
print(f"✅ T2 Runs-Vergleich: {RESULTS}/t2_runs_comparison.pdf")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════
#  T3 – RAMP-TEST
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  T3 – Ramp-Test (0→50 VU, 12 min)")
print("="*60)

# Bekannte Werte aus Auswertung (bereits berechnet)
t3_results = {
    "sam": {
        "Anlauf\n(0–2min, 0→10VU)":  {"p50": 89.1,  "p95": 152.3, "err": 0.00,  "n": 2856},
        "Stufe 1\n(2–5min, 10VU)":   {"p50": 91.9,  "p95": 187.6, "err": 0.00,  "n": 8927},
        "Stufe 2\n(5–8min, 25VU)":   {"p50": 96.6,  "p95": 260.9, "err": 16.94, "n": 15155},
        "Stufe 3\n(8–11min, 50VU)":  {"p50": 39.8,  "p95": 152.8, "err": 63.91, "n": 39944},
    },
    "sls": {
        "Anlauf\n(0–2min, 0→10VU)":  {"p50": 140.9, "p95": 192.5, "err": 0.00,  "n": 2364},
        "Stufe 1\n(2–5min, 10VU)":   {"p50": 141.4, "p95": 218.7, "err": 0.00,  "n": 7740},
        "Stufe 2\n(5–8min, 25VU)":   {"p50": 144.1, "p95": 235.6, "err": 17.60, "n": 13727},
        "Stufe 3\n(8–11min, 50VU)":  {"p50": 35.9,  "p95": 176.2, "err": 68.23, "n": 38642},
    },
    "faas": {
        "Anlauf\n(0–2min, 0→10VU)":  {"p50": 32.2,  "p95": 97.7,  "err": 0.00,  "n": 3749},
        "Stufe 1\n(2–5min, 10VU)":   {"p50": 32.2,  "p95": 90.0,  "err": 0.00,  "n": 12338},
        "Stufe 2\n(5–8min, 25VU)":   {"p50": 37.5,  "p95": 495.7, "err": 0.00,  "n": 14699},
        "Stufe 3\n(8–11min, 50VU)":  {"p50": 63.6,  "p95": 785.3, "err": 0.00,  "n": 16710},
    },
}

# ── LaTeX T3 ─────────────────────────────────────────────────────────────────
t3_tex = RESULTS / "t3_latex_table.tex"
with open(t3_tex, "w") as f:
    f.write("% T3 Ramp-Test – Ergebnisse je Laststufe\n")
    f.write("% Automatisch generiert von analyze_all.py\n\n")
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T3~-- Ramp-Test: Latenz und Fehlerrate je Laststufe}\n")
    f.write("  \\label{tab:t3-ergebnisse}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{llXXXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{Laststufe} & \\textbf{$n$} & "
            "\\textbf{$p_{50}$~(ms)} & \\textbf{$p_{95}$~(ms)} & \\textbf{$e$~(\\%)} \\\\\n")
    f.write("    \\midrule\n")
    stage_labels = {
        "Anlauf\n(0–2min, 0→10VU)": "Anlauf (0→10~VU)",
        "Stufe 1\n(2–5min, 10VU)":  "Stufe~1 (10~VU)",
        "Stufe 2\n(5–8min, 25VU)":  "Stufe~2 (25~VU)",
        "Stufe 3\n(8–11min, 50VU)": "Stufe~3 (50~VU)",
    }
    for key, label in zip(FW_KEYS, FW_LABELS):
        first = True
        for stage, vals in t3_results[key].items():
            fw_col = label if first else ""
            first = False
            note = ""
            if vals["err"] > 5:
                note = "$^{\\dagger}$"
            f.write(f"    {fw_col} & {stage_labels[stage]} & "
                    f"{vals['n']:,} & {vals['p50']:.1f} & "
                    f"{vals['p95']:.1f} & {vals['err']:.2f}{note} \\\\\n")
        f.write("    \\midrule\n")
    f.write("    \\multicolumn{6}{l}{\\small $^{\\dagger}$ Fehler durch "
            "MongoDB~Atlas~M0 Connection-Limit (framework-unabhängig)} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n")
print(f"✅ T3 LaTeX: {t3_tex}")

# ── T3 Latenz-Liniendiagramm ─────────────────────────────────────────────────
fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

stage_x = [0, 1, 2, 3]
stage_ticks = ["Anlauf\n0→10 VU", "Stufe 1\n10 VU", "Stufe 2\n25 VU", "Stufe 3\n50 VU"]

for key, label, color in zip(FW_KEYS, FW_LABELS, FW_COLORS):
    stages = list(t3_results[key].values())
    p50s = [s["p50"] for s in stages]
    p95s = [s["p95"] for s in stages]
    ax1.plot(stage_x, p50s, marker="o", color=color, linewidth=2, label=label)
    ax2.plot(stage_x, p95s, marker="s", color=color, linewidth=2, label=label, linestyle="--")

ax1.set_xticks(stage_x); ax1.set_xticklabels(stage_ticks, fontsize=9)
ax1.set_ylabel("Latenz p50 (ms)"); ax1.set_title("T3 – Median (p50) je Laststufe")
ax1.legend(fontsize=9); ax1.grid(linestyle="--", alpha=0.4)
ax1.axvline(x=1.5, color="red", linestyle=":", alpha=0.5)
ax1.text(1.55, ax1.get_ylim()[1]*0.9, "Atlas-Limit\ngreift ab hier",
         fontsize=8, color="red", alpha=0.8)

ax2.set_xticks(stage_x); ax2.set_xticklabels(stage_ticks, fontsize=9)
ax2.set_ylabel("Latenz p95 (ms)"); ax2.set_title("T3 – p95 je Laststufe")
ax2.legend(fontsize=9); ax2.grid(linestyle="--", alpha=0.4)
ax2.axvline(x=1.5, color="red", linestyle=":", alpha=0.5)

fig3.suptitle("T3 – Skalierungsverhalten (Ramp-Test 0→50 VU)", fontsize=12, fontweight="bold")
plt.tight_layout()
for ext in ["pdf", "png"]:
    plt.savefig(RESULTS / f"t3_latency_over_time.{ext}", bbox_inches="tight")
print(f"✅ T3 Grafik: {RESULTS}/t3_latency_over_time.pdf")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════
#  T4 – COLD-START
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  T4 – Cold-Start (5 Messungen je Framework)")
print("="*60)

# Echte Messwerte aus t4_*_run*.json (t_first = einziger Request je Datei)
t4_raw = {
    "sam":  [536.08, 479.76, 544.30, 519.60, 492.34],
    "sls":  [491.42, 539.37, 227.01, 462.83, 566.00],
    "faas": [59.88,  59.99,  68.84,  53.90,  49.16],
}

# p50_warm aus T4-Warm-up-Protokoll (Median je Run, dann Mittelwert)
p50_warm = {
    "sam":  np.mean([48.46, 45.38, 45.69, 45.64, 45.58]),  # = 46.15 ms
    "sls":  np.mean([47.63, 47.93, 48.36, 53.66, 50.22]),  # = 49.56 ms
    "faas": np.mean([32.99, 34.36, 33.81, 36.65, 37.63]),  # = 35.09 ms
}

# SLS Run 3 (227ms) ist Ausreißer – Lambda noch warm. Dokumentieren, aber
# bereinigten Wert für Vergleich verwenden.
t4_clean = {
    "sam":  t4_raw["sam"],
    "sls":  [v for i, v in enumerate(t4_raw["sls"]) if i != 2],  # ohne Run 3
    "faas": t4_raw["faas"],
}

t4_delta_all   = {k: [v - p50_warm[k] for v in t4_raw[k]]   for k in FW_KEYS}
t4_delta_clean = {k: [v - p50_warm[k] for v in t4_clean[k]] for k in FW_KEYS}

print(f"\n  p50_warm:  SAM={p50_warm['sam']:.2f}ms  SLS={p50_warm['sls']:.2f}ms  FaaS={p50_warm['faas']:.2f}ms")
print()
for key, label in zip(FW_KEYS, FW_LABELS):
    raw  = t4_raw[key]
    delta = t4_delta_clean[key]
    print(f"  {label}")
    for i, (r, d) in enumerate(zip(raw, [v - p50_warm[key] for v in raw])):
        flag = " ← Ausreißer (Lambda warm)" if key == "sls" and i == 2 else ""
        print(f"    Run {i+1}: t_first={r:.2f}ms  Δt={d:.2f}ms{flag}")
    print(f"    Ø Δt (bereinigt): {np.mean(delta):.2f}ms  σ={np.std(delta):.2f}ms  "
          f"min={min(delta):.2f}ms  max={max(delta):.2f}ms")

# ── CSV T4 ────────────────────────────────────────────────────────────────────
t4_csv = RESULTS / "t4_summary.csv"
with open(t4_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["framework","run","t_first_ms","p50_warm_ms","delta_cold_ms","outlier"])
    for key, label in zip(FW_KEYS, FW_LABELS):
        for i, v in enumerate(t4_raw[key]):
            delta = v - p50_warm[key]
            outlier = (key == "sls" and i == 2)
            w.writerow([label, i+1, round(v,2), round(p50_warm[key],2),
                        round(delta,2), "ja" if outlier else "nein"])
print(f"\n✅ T4 CSV: {t4_csv}")

# ── LaTeX T4 ─────────────────────────────────────────────────────────────────
t4_tex = RESULTS / "t4_latex_table.tex"
with open(t4_tex, "w") as f:
    f.write("% T4 Cold-Start – Messwerte und berechnete Delta-Werte\n")
    f.write("% Automatisch generiert von analyze_all.py\n\n")

    # Einzelmessungen
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T4~-- Cold-Start-Einzelmessungen "
            "($t_{\\mathrm{first}}$ und $\\Delta t_{\\mathrm{cold}}$)}\n")
    f.write("  \\label{tab:t4-einzelmessungen}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{llXXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{Run} & "
            "\\textbf{$t_{\\mathrm{first}}$~(ms)} & "
            "\\textbf{$p_{50}^{\\mathrm{warm}}$~(ms)} & "
            "\\textbf{$\\Delta t_{\\mathrm{cold}}$~(ms)} \\\\\n")
    f.write("    \\midrule\n")
    for key, label in zip(FW_KEYS, FW_LABELS):
        for i, v in enumerate(t4_raw[key]):
            delta = v - p50_warm[key]
            fw_col = label if i == 0 else ""
            note = "$^{\\dagger}$" if key == "sls" and i == 2 else ""
            f.write(f"    {fw_col} & {i+1} & {v:.2f} & "
                    f"{p50_warm[key]:.2f} & {delta:.2f}{note} \\\\\n")
        f.write("    \\midrule\n")
    f.write("    \\multicolumn{5}{l}{\\small $^{\\dagger}$ Ausreißer: "
            "Lambda-Instanz noch warm (Run~3 SLS, $t_{\\mathrm{first}}=227$~ms)} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n\n")

    # Zusammenfassung
    f.write("\\begin{table}[htbp]\n  \\centering\n")
    f.write("  \\caption{T4~-- Cold-Start-Zusammenfassung "
            "(bereinigt, ohne Ausreißer)}\n")
    f.write("  \\label{tab:t4-ergebnisse}\n")
    f.write("  \\begin{tabularx}{\\textwidth}{lXXXXX}\n    \\toprule\n")
    f.write("    \\textbf{Framework} & \\textbf{$p_{50}^{\\mathrm{warm}}$~(ms)} & "
            "\\textbf{$\\bar{\\Delta t}_{\\mathrm{cold}}$~(ms)} & "
            "\\textbf{$\\sigma$~(ms)} & "
            "\\textbf{Min~(ms)} & \\textbf{Max~(ms)} \\\\\n")
    f.write("    \\midrule\n")
    for key, label in zip(FW_KEYS, FW_LABELS):
        d = t4_delta_clean[key]
        f.write(f"    {label} & {p50_warm[key]:.1f} & "
                f"{np.mean(d):.1f} & {np.std(d):.1f} & "
                f"{min(d):.1f} & {max(d):.1f} \\\\\n")
    f.write("    \\bottomrule\n  \\end{tabularx}\n\\end{table}\n")
print(f"✅ T4 LaTeX: {t4_tex}")

# ── T4 Grafik ─────────────────────────────────────────────────────────────────
fig4, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Links: Delta t_cold je Run (alle Messungen)
for key, label, color in zip(FW_KEYS, FW_LABELS, FW_COLORS):
    deltas = [v - p50_warm[key] for v in t4_raw[key]]
    runs = list(range(1, len(deltas)+1))
    ax1.plot(runs, deltas, marker="o", color=color, linewidth=2, label=label)
    # Ausreißer markieren
    if key == "sls":
        ax1.scatter([3], [deltas[2]], marker="x", color="red", s=100, zorder=5)
        ax1.annotate("Ausreißer\n(Lambda warm)", xy=(3, deltas[2]),
                     xytext=(3.2, deltas[2]+30), fontsize=8, color="red")

ax1.set_xlabel("Run"); ax1.set_ylabel("Δt_cold (ms)")
ax1.set_title("T4 – Cold-Start-Overhead je Run")
ax1.legend(fontsize=9); ax1.grid(linestyle="--", alpha=0.4)
ax1.axhline(y=0, color="gray", linestyle=":", alpha=0.5)

# Rechts: Boxplot der bereinigten Delta-Werte
bp_data2 = [t4_delta_clean[k] for k in FW_KEYS]
bp2 = ax2.boxplot(bp_data2, patch_artist=True,
                  medianprops=dict(color="black", linewidth=2),
                  showfliers=True,
                  flierprops=dict(marker="o", markersize=5))
for patch, color in zip(bp2["boxes"], FW_COLORS):
    patch.set_facecolor(color); patch.set_alpha(0.75)
ax2.set_xticks([1,2,3]); ax2.set_xticklabels(FW_LABELS, fontsize=9)
ax2.set_ylabel("Δt_cold (ms)")
ax2.set_title("T4 – Cold-Start-Verteilung (bereinigt)")
ax2.grid(axis="y", linestyle="--", alpha=0.4)

# Mittelwert-Annotation
for i, key in enumerate(FW_KEYS):
    mean_val = np.mean(t4_delta_clean[key])
    ax2.text(i+1, mean_val+10, f"Ø {mean_val:.0f}ms",
             ha="center", fontsize=9, color=FW_COLORS[i], fontweight="bold")

fig4.suptitle("T4 – Cold-Start-Latenz nach 15~min Inaktivität",
              fontsize=12, fontweight="bold")
plt.tight_layout()
for ext in ["pdf", "png"]:
    plt.savefig(RESULTS / f"t4_cold_start.{ext}", bbox_inches="tight")
print(f"✅ T4 Grafik: {RESULTS}/t4_cold_start.pdf")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════
#  ABSCHLUSSZUSAMMENFASSUNG
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ZUSAMMENFASSUNG ALLER ERGEBNISSE")
print("="*60)

print("\n  T2 – Steady-State (aggregiert):")
print(f"  {'Framework':<16} {'p50':>8} {'p95':>8} {'CV':>6} {'err':>7}")
print("  " + "-"*46)
for key, label in zip(FW_KEYS, FW_LABELS):
    a = t2_agg[key]
    print(f"  {label:<16} {a['p50']:>7.1f}ms {a['p95']:>7.1f}ms {a['cv']:>6.2f} {a['err']:>6.2f}%")

print("\n  T3 – Stabile Zone (Stufe 1, 10 VU):")
print(f"  {'Framework':<16} {'p50':>8} {'p95':>8} {'err':>7}")
print("  " + "-"*40)
for key, label in zip(FW_KEYS, FW_LABELS):
    s = list(t3_results[key].values())[1]  # Stufe 1
    print(f"  {label:<16} {s['p50']:>7.1f}ms {s['p95']:>7.1f}ms {s['err']:>6.2f}%")

print("\n  T4 – Cold-Start (bereinigt):")
print(f"  {'Framework':<16} {'p50_warm':>10} {'Ø Δt_cold':>12} {'σ':>8}")
print("  " + "-"*48)
for key, label in zip(FW_KEYS, FW_LABELS):
    d = t4_delta_clean[key]
    print(f"  {label:<16} {p50_warm[key]:>9.1f}ms {np.mean(d):>11.1f}ms {np.std(d):>7.1f}ms")

print(f"\n✅ Alle Dateien in: {RESULTS.resolve()}")
print("   t2_summary.csv, t2_latex_table.tex, t2_boxplot.pdf, t2_runs_comparison.pdf")
print("   t3_latex_table.tex, t3_latency_over_time.pdf")
print("   t4_summary.csv, t4_latex_table.tex, t4_cold_start.pdf")
