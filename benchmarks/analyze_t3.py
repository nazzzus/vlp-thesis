#!/usr/bin/env python3
"""
analyze_t3.py – T3 Ramp-Test Auswertung
Alle drei Frameworks, mit p50 / p95 / p99 je Laststufe.
Erzeugt: results/figures/t3_latency_over_time.pdf

Ausführung:
    python3 analyze_t3.py
"""

import json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
FIGURES_DIR = Path("results/figures")
FIGURES_DIR.mkdir(exist_ok=True)

STAGES = [
    ("Anlauf  (0→10 VU,  0– 2 min)", 0,  2),
    ("Stufe 1 (10 VU,    2– 5 min)", 2,  5),
    ("Stufe 2 (20 VU,    5– 8 min)", 5,  8),
    ("Stufe 3 (30 VU,    8–11 min)", 8, 11),
]
STAGE_LABELS = ["Anlauf\n0→10 VU", "Stufe 1\n10 VU", "Stufe 2\n20 VU", "Stufe 3\n30 VU"]

FRAMEWORKS = [
    ("SAM",      "t3_sam.json"),
    ("SLS",      "t3_sls.json"),
    ("OpenFaaS", "t3_faas.json"),
]

COLORS = {
    "SAM":      "#2196F3",
    "SLS":      "#4CAF50",
    "OpenFaaS": "#FF9800",
}

def load_durations(filepath):
    points = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (obj.get("metric") == "http_req_duration"
                    and obj.get("type") == "Point"):
                points.append((obj["data"]["time"], obj["data"]["value"]))
    return points

def parse_time(ts):
    from datetime import datetime
    import re
    ts = re.sub(r'(\.\d+)([+-]\d{2}:\d{2})$',
                lambda m: m.group(1).ljust(7, '0') + m.group(2), ts)
    ts = re.sub(r'([+-])(\d{2}):(\d{2})$', r'\1\2\3', ts)
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp()
    except ValueError:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp()

def analyze(filepath):
    raw = load_durations(filepath)
    if not raw:
        print(f"  ⚠️  Keine Daten in {filepath}")
        return None

    times  = [parse_time(t) for t, _ in raw]
    values = [v for _, v in raw]
    t0     = times[0]
    offsets_min = [(t - t0) / 60.0 for t in times]

    print(f"\n  Gesamt: {len(values):,} Requests | Dauer: {offsets_min[-1]:.1f} min")
    print(f"  {'Stufe':<38} {'n':>6}  {'p50':>7}  {'p95':>7}  {'p99':>7}")
    print(f"  {'-'*38} {'-'*6}  {'-'*7}  {'-'*7}  {'-'*7}")

    stage_results = []
    for label, t_start, t_end in STAGES:
        bucket = [v for v, m in zip(values, offsets_min)
                  if t_start <= m < t_end]
        if not bucket:
            print(f"  {label:<38} {'–':>6}")
            stage_results.append((None, None, None))
            continue
        arr = np.array(bucket)
        p50 = np.percentile(arr, 50)
        p95 = np.percentile(arr, 95)
        p99 = np.percentile(arr, 99)
        print(f"  {label:<38} {len(bucket):>6,}  "
              f"{p50:>6.1f}ms  {p95:>6.1f}ms  {p99:>6.1f}ms")
        stage_results.append((p50, p95, p99))
    return stage_results

# ── Konsolenausgabe ───────────────────────────────────────────────────────────
print("=" * 65)
print("  T3 Ramp-Test Auswertung – SAM | SLS | OpenFaaS")
print("=" * 65)

all_results = {}
for fw_name, filename in FRAMEWORKS:
    filepath = RESULTS_DIR / filename
    print(f"\n── T3 {fw_name} {'─' * (50 - len(fw_name))}")
    if not filepath.exists():
        print(f"  ❌  Datei nicht gefunden: {filepath}")
        continue
    result = analyze(filepath)
    if result:
        all_results[fw_name] = result

print("\n" + "=" * 65)

# ── Plot ──────────────────────────────────────────────────────────────────────
if not all_results:
    print("⚠️  Keine Daten für Plot.")
else:
    plt.rcParams.update({
        "font.family": "serif", "font.size": 11,
        "axes.titlesize": 12, "axes.labelsize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    x = np.arange(len(STAGES))

    for fw_name, results in all_results.items():
        p50s = [r[0] for r in results]
        p95s = [r[1] for r in results]
        color = COLORS[fw_name]
        ax1.plot(x, p50s, "o-",  color=color, linewidth=2, markersize=7, label=fw_name)
        ax2.plot(x, p95s, "s--", color=color, linewidth=2, markersize=7, label=fw_name)

    for ax, title, ylabel in [
        (ax1, "T3 – Median (p50) je Laststufe",        "p50 Latenz (ms)"),
        (ax2, "T3 – 95. Perzentil (p95) je Laststufe", "p95 Latenz (ms)"),
    ]:
        ax.set_xticks(x)
        ax.set_xticklabels(STAGE_LABELS, fontsize=9)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.set_ylim(bottom=0)

    fig.suptitle("T3 Ramp-Test (0→30 VU, 12 min) – Latenz je Laststufe",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()

    pdf_path = FIGURES_DIR / "t3_latency_over_time.pdf"
    png_path = FIGURES_DIR / "t3_latency_over_time.png"
    plt.savefig(pdf_path, bbox_inches="tight", format="pdf")
    plt.savefig(png_path, bbox_inches="tight", format="png", dpi=150)
    plt.close()
    print(f"✅ PDF: {pdf_path}")
    print(f"✅ PNG: {png_path}")