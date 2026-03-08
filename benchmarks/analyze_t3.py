#!/usr/bin/env python3
"""
analyze_t3.py – T3 Ramp-Test Auswertung
Erzeugt:
  - Konsolentabelle
  - results/t3_latency_over_time.pdf  (Latenzkurve über Zeit)
  - results/t3_latex_table.tex
"""

import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
OUTPUT_DIR  = Path("results")

FRAMEWORKS = {
    "SAM":      "t3_sam.json",
    "SLS":      "t3_sls.json",
    "OpenFaaS": "t3_faas.json",
}

COLORS = {
    "SAM":      "#2196F3",
    "SLS":      "#FF9800",
    "OpenFaaS": "#4CAF50",
}

plt.rcParams.update({
    "font.family":     "serif",
    "font.size":       11,
    "axes.titlesize":  12,
    "axes.labelsize":  11,
    "figure.dpi":      150,
})

def load_timeseries(filepath):
    """Lädt (timestamp_sekunden, latenz_ms, status) für alle Requests."""
    points = []
    path = RESULTS_DIR / filepath
    if not path.exists():
        print(f"  ⚠️  Nicht gefunden: {path}", file=sys.stderr)
        return points

    # Startzeit ermitteln
    start_ts = None
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
                if (d.get("type") == "Point"
                        and d.get("metric") == "http_req_duration"):
                    ts_str = d["data"]["time"]
                    # Parse ISO timestamp
                    from datetime import datetime, timezone
                    ts_str_clean = ts_str[:26].rstrip("Z")
                    if "+" in ts_str_clean:
                        ts_str_clean = ts_str_clean.split("+")[0]
                    ts = datetime.fromisoformat(ts_str_clean)
                    start_ts = ts.timestamp()
                    break
            except:
                pass
    if start_ts is None:
        return points

    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
                if (d.get("type") == "Point"
                        and d.get("metric") == "http_req_duration"):
                    tags = d["data"].get("tags", {})
                    val  = d["data"]["value"]
                    ts_str = d["data"]["time"][:26].rstrip("Z")
                    if "+" in ts_str:
                        ts_str = ts_str.split("+")[0]
                    from datetime import datetime
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    elapsed = ts - start_ts
                    success = tags.get("expected_response") == "true"
                    if val < 30000:  # Ausreißer ignorieren
                        points.append((elapsed, val, success))
            except:
                pass
    return points

def load_vus_over_time(filepath):
    """Lädt VU-Zahl über Zeit."""
    points = []
    path = RESULTS_DIR / filepath
    if not path.exists():
        return points
    start_ts = None
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("type") == "Point" and d.get("metric") == "vus":
                    ts_str = d["data"]["time"][:26].rstrip("Z")
                    if "+" in ts_str:
                        ts_str = ts_str.split("+")[0]
                    from datetime import datetime
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    if start_ts is None:
                        start_ts = ts
                    points.append((ts - start_ts, d["data"]["value"]))
            except:
                pass
    return points

# ── Daten laden ────────────────────────────────────────────────────────────────
print("Lade T3-Rohdaten...")
all_ts = {}
for fw, f in FRAMEWORKS.items():
    pts = load_timeseries(f)
    all_ts[fw] = pts
    print(f"  {fw}: {len(pts)} Messpunkte")

# ── Binning: 30s-Fenster ───────────────────────────────────────────────────────
def bin_timeseries(points, bin_size=30):
    """Gruppiert Latenzen in Zeitfenster, gibt (t_mitte, p50, p95, fehlerrate) zurück."""
    if not points:
        return [], [], [], []
    max_t = max(p[0] for p in points)
    bins  = np.arange(0, max_t + bin_size, bin_size)
    t_mid, p50s, p95s, err_rates = [], [], [], []

    for i in range(len(bins)-1):
        lo, hi = bins[i], bins[i+1]
        bucket = [p for p in points if lo <= p[0] < hi]
        if len(bucket) < 5:
            continue
        lats    = [p[1] for p in bucket]
        success = [p[2] for p in bucket]
        t_mid.append((lo + hi) / 2 / 60)  # in Minuten
        p50s.append(np.percentile(lats, 50))
        p95s.append(np.percentile(lats, 95))
        err_rates.append(1 - np.mean(success))
    return t_mid, p50s, p95s, err_rates

# ── Plot: Latenzkurve über Zeit ────────────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

ax_lat = axes[0]
ax_err = axes[1]

for fw in ["SAM", "SLS", "OpenFaaS"]:
    t_mid, p50s, p95s, err_rates = bin_timeseries(all_ts[fw], bin_size=30)
    if not t_mid:
        continue
    color = COLORS[fw]
    ax_lat.plot(t_mid, p50s, "-",  color=color, linewidth=2,   label=f"{fw} p50")
    ax_lat.plot(t_mid, p95s, "--", color=color, linewidth=1.5, label=f"{fw} p95", alpha=0.8)
    ax_err.plot(t_mid, [e*100 for e in err_rates], "-", color=color, linewidth=2, label=fw)

# VU-Verlauf als Hintergrund andeuten
ax_lat.axvline(x=2,  color="gray", linestyle=":", alpha=0.4, linewidth=1)
ax_lat.axvline(x=4,  color="gray", linestyle=":", alpha=0.4, linewidth=1)
ax_lat.axvline(x=6,  color="gray", linestyle=":", alpha=0.4, linewidth=1)
ax_lat.axvline(x=9,  color="gray", linestyle=":", alpha=0.4, linewidth=1)
ax_lat.axvline(x=11, color="gray", linestyle=":", alpha=0.4, linewidth=1)

ax_lat.set_ylabel("Latenz (ms)")
ax_lat.set_title("T3 Ramp-Test – Latenzkurve über Zeit (p50 / p95)")
ax_lat.legend(ncol=3, fontsize=9, loc="upper left")
ax_lat.grid(linestyle="--", alpha=0.4)
ax_lat.set_ylim(bottom=0)

ax_err.axhline(y=5, color="red", linestyle="--", linewidth=1, alpha=0.7, label="5%-Threshold")
ax_err.set_ylabel("Fehlerrate (%)")
ax_err.set_xlabel("Zeit (Minuten)")
ax_err.set_title("T3 – Fehlerrate über Zeit")
ax_err.legend(ncol=4, fontsize=9)
ax_err.grid(linestyle="--", alpha=0.4)
ax_err.set_ylim(0, 105)

# Ramp-Stufen annotieren
for ax in [ax_lat]:
    ax.text(1,   ax.get_ylim()[1]*0.95, "10 VU",  fontsize=8, ha="center", color="gray")
    ax.text(3,   ax.get_ylim()[1]*0.95, "20 VU",  fontsize=8, ha="center", color="gray")
    ax.text(5,   ax.get_ylim()[1]*0.95, "30 VU",  fontsize=8, ha="center", color="gray")
    ax.text(7.5, ax.get_ylim()[1]*0.95, "50 VU",  fontsize=8, ha="center", color="gray")
    ax.text(10,  ax.get_ylim()[1]*0.95, "↓ 0 VU", fontsize=8, ha="center", color="gray")

fig.suptitle("T3 Ramp-Test (0→50 VUs, 12 min) – Latenz und Fehlerrate je Framework",
             fontsize=13, fontweight="bold")
plt.tight_layout()

pdf_path = OUTPUT_DIR / "t3_latency_over_time.pdf"
plt.savefig(pdf_path, bbox_inches="tight", format="pdf")
png_path = OUTPUT_DIR / "t3_latency_over_time.png"
plt.savefig(png_path, bbox_inches="tight", format="png", dpi=150)
print(f"✅ T3-Plot gespeichert: {pdf_path}")
plt.close()

# ── Konsolentabelle: stabiler Bereich (0–10 VUs, erste 6 min) ─────────────────
print("\n" + "═"*60)
print("T3 – Stabiler Bereich (0–6 min, ≤10 VUs)")
print(f"{'Framework':<12} {'n':>6} {'avg':>8} {'p95':>8} {'Fehler':>8}")
print("─"*60)

latex_rows = []
for fw in ["SAM", "SLS", "OpenFaaS"]:
    stable = [(t, v, s) for t, v, s in all_ts[fw] if t < 360]  # erste 6 min
    if not stable:
        continue
    lats    = [p[1] for p in stable]
    success = [p[2] for p in stable]
    avg   = np.mean(lats)
    p95   = np.percentile(lats, 95)
    errate = (1 - np.mean(success)) * 100
    print(f"{fw:<12} {len(lats):>6} {avg:>7.1f}ms {p95:>7.1f}ms {errate:>7.2f}%")
    latex_rows.append((fw, len(lats), avg, p95, errate))

print("═"*60)

# ── LaTeX-Tabelle ──────────────────────────────────────────────────────────────
latex_path = OUTPUT_DIR / "t3_latex_table.tex"
with open(latex_path, "w") as f:
    f.write("% T3 Ramp-Test – Stabiler Bereich (automatisch generiert)\n\n")
    f.write("\\begin{table}[htbp]\n")
    f.write("  \\centering\n")
    f.write("  \\caption{T3 Ramp-Test: Latenz im stabilen Bereich ($\\leq$10\\,VUs, erste 6\\,min)}\n")
    f.write("  \\label{tab:t3_stabil}\n")
    f.write("  \\begin{tabular}{lrrrr}\n")
    f.write("    \\toprule\n")
    f.write("    Framework & $n$ & Avg (ms) & p95 (ms) & Fehlerrate (\\%) \\\\\n")
    f.write("    \\midrule\n")
    for fw, n, avg, p95, err in latex_rows:
        f.write(f"    {fw} & {n:,} & {avg:.1f} & {p95:.1f} & {err:.2f} \\\\\n")
    f.write("    \\bottomrule\n")
    f.write("  \\end{tabular}\n")
    f.write("\\end{table}\n")

print(f"\n✅ LaTeX-Tabelle gespeichert: {latex_path}")
print("✅ T3-Auswertung abgeschlossen.")
