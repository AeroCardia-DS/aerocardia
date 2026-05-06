import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import glob

# ── Load all summary CSVs from Outputs folder ─────────────────────────────────
summary_files = glob.glob("Outputs/**/recording_summary.csv", recursive=True) + \
                glob.glob("Outputs/recording_comparison.csv") + \
                glob.glob("Outputs/recording_summary.csv")

if not summary_files:
    print("No summary files found! Run analyze_tcc_v2.py first to generate data.")
    exit()

# Combine all summaries into one dataframe
dfs = []
for f in set(summary_files):
    try:
        dfs.append(pd.read_csv(f))
    except:
        pass

if not dfs:
    print("Could not load any summary files.")
    exit()

df = pd.concat(dfs, ignore_index=True).drop_duplicates()
df = df.sort_values(["Patient", "Session"]).reset_index(drop=True)

print("=" * 60)
print("COMPARISON DASHBOARD")
print("=" * 60)
print(f"Loaded {len(df)} recording(s) across {df['Patient'].nunique()} patient(s)\n")
print(df[["Patient", "Session", "Duration (s)", "Avg HR (bpm)", "Avg SpO2 (%)",
          "Breathing Rate", "Data Quality (%)", "Critical Alerts", "Warnings"]].to_string(index=False))

# ── Color helpers ─────────────────────────────────────────────────────────────
def alert_color(row):
    if row["Critical Alerts"] > 0: return "red"
    if row["Warnings"] > 0: return "orange"
    return "steelblue"

colors = [alert_color(row) for _, row in df.iterrows()]
labels = [f"{row['Patient']}\n{row['Session']}" for _, row in df.iterrows()]
x = np.arange(len(df))
width = 0.6

# ── Figure ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 2, figsize=(16, 18))
fig.suptitle("AeroCardia TCC — Multi-Recording Comparison Dashboard",
             fontsize=14, fontweight="bold")
fig.subplots_adjust(hspace=0.6, wspace=0.35, top=0.93)

# Legend for alert colors
legend_patches = [
    mpatches.Patch(color="steelblue", label="No alerts"),
    mpatches.Patch(color="orange",    label="Warnings"),
    mpatches.Patch(color="red",       label="Critical alerts"),
]
fig.legend(handles=legend_patches, loc="upper right", fontsize=9, framealpha=0.8)

# 1. Average Heart Rate
ax = axes[0, 0]
bars = ax.bar(x, df["Avg HR (bpm)"], color=colors, width=width, zorder=3)
ax.axhline(50,  color="orange", linestyle="--", linewidth=0.8, label="Low warning (50)")
ax.axhline(80,  color="orange", linestyle="--", linewidth=0.8, label="High warning (80)")
ax.axhline(100, color="red",    linestyle=":",  linewidth=0.8, label="Critical (100)")
ax.axhspan(50, 80, alpha=0.08, color="green", zorder=0)
ax.set_title("Average Heart Rate", fontweight="bold")
ax.set_ylabel("bpm")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, df["Avg HR (bpm)"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{val:.0f}", ha="center", va="bottom", fontsize=8)

# 2. Average SpO2
ax = axes[0, 1]
bars = ax.bar(x, df["Avg SpO2 (%)"], color=colors, width=width, zorder=3)
ax.axhline(95, color="orange", linestyle="--", linewidth=0.8, label="Warning (95%)")
ax.axhline(90, color="red",    linestyle=":",  linewidth=0.8, label="Critical (90%)")
ax.axhspan(95, 100, alpha=0.08, color="green", zorder=0)
ax.set_title("Average SpO2", fontweight="bold")
ax.set_ylabel("%")
ax.set_ylim(85, 102)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, df["Avg SpO2 (%)"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
            f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

# 3. Breathing Rate
ax = axes[1, 0]
br = df["Breathing Rate"].fillna(0)
br_colors = ["red" if v > 25 or v < 8 else "orange" if v > 20 or v < 12 else "steelblue" for v in br]
bars = ax.bar(x, br, color=br_colors, width=width, zorder=3)
ax.axhline(12, color="orange", linestyle="--", linewidth=0.8, label="Normal low (12)")
ax.axhline(20, color="orange", linestyle="--", linewidth=0.8, label="Normal high (20)")
ax.axhline(25, color="red",    linestyle=":",  linewidth=0.8, label="Critical (25)")
ax.axhspan(12, 20, alpha=0.08, color="green", zorder=0)
ax.set_title("Breathing Rate", fontweight="bold")
ax.set_ylabel("breaths/min")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, br):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{val:.0f}", ha="center", va="bottom", fontsize=8)
    else:
        ax.text(bar.get_x() + bar.get_width()/2, 0.5,
                "N/A", ha="center", va="bottom", fontsize=8, color="gray")

# 4. Data Quality
ax = axes[1, 1]
dq_colors = ["green" if v >= 90 else "orange" if v >= 70 else "red" for v in df["Data Quality (%)"]]
bars = ax.bar(x, df["Data Quality (%)"], color=dq_colors, width=width, zorder=3)
ax.axhline(90, color="green",  linestyle="--", linewidth=0.8, label="Good (90%)")
ax.axhline(70, color="orange", linestyle="--", linewidth=0.8, label="Acceptable (70%)")
ax.set_title("Data Quality Score", fontweight="bold")
ax.set_ylabel("%")
ax.set_ylim(0, 105)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, df["Data Quality (%)"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{val:.0f}%", ha="center", va="bottom", fontsize=8)

# 5. Recording Duration
ax = axes[2, 0]
dur_colors = ["red" if v < 30 else "orange" if v < 120 else "green" for v in df["Duration (s)"]]
bars = ax.bar(x, df["Duration (s)"], color=dur_colors, width=width, zorder=3)
ax.axhline(30,  color="red",    linestyle=":",  linewidth=0.8, label="Min useful (30s)")
ax.axhline(120, color="green",  linestyle="--", linewidth=0.8, label="HRV minimum (120s)")
ax.set_title("Recording Duration", fontweight="bold")
ax.set_ylabel("seconds")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, df["Duration (s)"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{val:.0f}s", ha="center", va="bottom", fontsize=8)

# 6. Alerts & Warnings Count
ax = axes[2, 1]
bar_width = 0.3
bars1 = ax.bar(x - bar_width/2, df["Critical Alerts"], width=bar_width,
               color="red", label="Critical Alerts", zorder=3)
bars2 = ax.bar(x + bar_width/2, df["Warnings"], width=bar_width,
               color="orange", label="Warnings", zorder=3)
ax.set_title("Alerts & Warnings per Recording", fontweight="bold")
ax.set_ylabel("Count")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars1, df["Critical Alerts"]):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                str(int(val)), ha="center", va="bottom", fontsize=8)
for bar, val in zip(bars2, df["Warnings"]):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                str(int(val)), ha="center", va="bottom", fontsize=8)

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs("Outputs", exist_ok=True)
out_path = "Outputs/comparison_dashboard.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nDashboard saved to {out_path}")
plt.show()
print("\nDone!")
