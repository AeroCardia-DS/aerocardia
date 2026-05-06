import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from scipy.signal import find_peaks
import glob
import os
from datetime import datetime

# ── Clinical Thresholds (sourced from AeroCardia Protocol v5, Appendix A) ─────
#
# Each metric has resting thresholds. Exercise thresholds are handled separately
# via EXERCISE_THRESHOLDS below, applied when test phase is known.
#
# Priority levels from Appendix A:
#   CRITICAL  = High Priority (⚠) — established clinical guidelines, immediate attention
#   WARNING   = Moderate (◆)      — research-derived, warrants monitoring
#   INFO      = Informational (●) — useful context, not independently actionable

THRESHOLDS = {
    # ACC/AHA & ESC 2021: <50 bpm bradycardia, >100 bpm tachycardia at rest
    # Warning at >80 bpm (45% higher all-cause mortality vs <60 bpm — Aune et al. 2017)
    "Heart Rate (bpm)": {
        "low": 50, "high": 80,
        "critical_low": 40, "critical_high": 100,
        "source": "ACC/AHA Heart Failure Guidelines; ESC 2021; Aune et al. Eur J Prev Cardiol 2017"
    },

    # BTS O2 Guidelines / O'Driscoll et al. Thorax 2017
    # <95% = clinically significant hypoxaemia (HIGH PRIORITY)
    # <90% = absolute stop condition during exercise; <88% = COPD/asthma critical threshold
    "SpO2 (%)": {
        "low": 95, "high": 100,
        "critical_low": 90, "critical_high": 100,
        "source": "O'Driscoll et al. Thorax 2017; BTS O2 Guidelines; ATS/ERS Exercise Testing 2003"
    },

    # Ambient O2 — environmental reference, not a direct clinical metric
    # OSHA: <19.5% oxygen-deficient, <16% immediately dangerous
    "O2 (%)": {
        "low": 19.5, "high": 21,
        "critical_low": 16.0, "critical_high": 23.5,
        "source": "OSHA 29 CFR 1910.146 (confined space O2 standards)"
    },

    # CO2 % near sensor — proxy for end-tidal CO2
    # Exhaled air ~4-5% CO2. <3.5% suggests hyperventilation; >6% suggests hypoventilation
    # Note: CO2 near 0% at recording start is expected (device not yet in mouth)
    # Critical low set to 0 to avoid false flags during warm-up period
    # Naifeh & Kamiya Psychophysiology 1981; Laffey & Kavanagh Br J Anaesth 2002
    "CO2 (%)": {
        "low": 3.5, "high": 5.5,
        "critical_low": 0.0, "critical_high": 8.0,
        "source": "Naifeh & Kamiya Psychophysiology 1981; Laffey & Kavanagh Br J Anaesth 2002"
    },

    # Lung Volume / Tidal Volume at rest ~0.5L; deep breath up to ~6L
    # Very low tidal volume (<0.3L) suggests restricted breathing
    "Lung Volume (L)": {
        "low": 0.3, "high": 6.0,
        "critical_low": 0.1, "critical_high": 8.0,
        "source": "AeroCardia Protocol v5; standard spirometry reference ranges"
    },

    # HRV SDNN — Task Force ESC/NASPE 1996; Shaffer & Ginsberg Front Public Health 2017
    # <20 ms = very low vagal tone, autonomic dysfunction (MODERATE priority)
    # 20-50 ms = average healthy adult
    # >50 ms = good autonomic health; >100 ms = athletic
    # Note: RMSSD is preferred over SDNN per protocol but SDNN used here as available metric
    "HRV SDNN (ms)": {
        "low": 20, "high": 200,
        "critical_low": 10, "critical_high": 300,
        "source": "Task Force ESC/NASPE 1996; Shaffer & Ginsberg Front Public Health 2017"
    },

    # Ambient temperature — extreme values affect sensor accuracy
    "Ambient Temperature": {
        "low": 15, "high": 35,
        "critical_low": 10, "critical_high": 40,
        "source": "AeroCardia device operating range"
    },
}

# ── Exercise thresholds (applied during step test / active phases) ─────────────
# SpO2: <90% = absolute stop condition during any exercise (ATS/ERS 2003)
# Drop >=3% from resting baseline = exercise-induced desaturation flag (HIGH PRIORITY)
# HR: >90% of age-predicted max (220 - age) = exceeds submaximal protocol intent
EXERCISE_THRESHOLDS = {
    "SpO2 (%)": {
        "low": 92, "high": 100,
        "critical_low": 88, "critical_high": 100,
        "source": "ATS/ERS Exercise Testing Statement 2003; AeroCardia Protocol Appendix A5"
    },
    "Heart Rate (bpm)": {
        "low": 50, "high": 150,   # wider during exercise — specific max calculated from age
        "critical_low": 40, "critical_high": 170,
        "source": "AeroCardia Protocol Appendix A5 — 90% age-predicted max stop condition"
    },
}

# ── Breathing rate thresholds ──────────────────────────────────────────────────
# Fieselmann et al. J Gen Intern Med 1993: >25 br/min = tachypnoea, independent CV predictor
# AHA/ACC: <12 br/min = bradypnoea
# Critical: >25 br/min at rest = HIGH PRIORITY per AeroCardia Appendix A2
BREATHING_NORMAL   = (12, 20)   # normal resting adult range
BREATHING_WARNING  = (12, 25)   # up to 25 is moderate concern
BREATHING_CRITICAL = (8,  25)   # <8 or >25 = critical at rest

# ── Helpers ───────────────────────────────────────────────────────────────────
def add_desc(ax, text):
    ax.text(0.5, -0.40, text, transform=ax.transAxes,
            fontsize=8, ha="center", va="top", color="#333333")

def set_titled(ax, base, has_critical, has_warning):
    ax.set_title(base, color="black")
    if has_critical:
        ax.text(-0.01, 1.05, "★", transform=ax.transAxes,
                fontsize=16, color="red", va="bottom", ha="right")
    elif has_warning:
        ax.text(-0.01, 1.05, "★", transform=ax.transAxes,
                fontsize=16, color="darkorange", va="bottom", ha="right")

def shade_zones(ax, bounds, y_min, y_max):
    ax.axhspan(bounds["low"], bounds["high"], alpha=0.10, color="green", zorder=0)
    if bounds["low"] > y_min:
        ax.axhspan(max(y_min, bounds["critical_low"]), bounds["low"], alpha=0.10, color="orange", zorder=0)
    if bounds["high"] < y_max:
        ax.axhspan(bounds["high"], min(y_max, bounds["critical_high"]), alpha=0.10, color="orange", zorder=0)
    if bounds["critical_low"] > y_min:
        ax.axhspan(y_min, bounds["critical_low"], alpha=0.14, color="red", zorder=0)
    if bounds["critical_high"] < y_max:
        ax.axhspan(bounds["critical_high"], y_max, alpha=0.14, color="red", zorder=0)

def plot_segmented(ax, t, vals, bounds, warn_color="orange", crit_color="red"):
    t = np.array(t)
    v = np.array(vals)
    for i in range(len(v) - 1):
        seg_t = t[i:i+2]
        seg_v = v[i:i+2]
        mid = (seg_v[0] + seg_v[1]) / 2
        if mid < bounds["critical_low"] or mid > bounds["critical_high"]:
            color = crit_color
        elif mid < bounds["low"] or mid > bounds["high"]:
            color = warn_color
        else:
            color = "black"
        ax.plot(seg_t, seg_v, color=color, linewidth=1.8, zorder=3)

LEGEND_ELS = [
    Line2D([0],[0], color="black",  linewidth=1.5, label="Normal"),
    Line2D([0],[0], color="orange", linewidth=1.5, label="Warning"),
    Line2D([0],[0], color="red",    linewidth=1.5, label="Critical"),
]

def log(text=""):
    print(text)
    pdf_lines.append(text)

# ── Find CSVs ─────────────────────────────────────────────────────────────────
all_csvs = [f for f in glob.glob("Data/**/*.csv", recursive=True) if f not in ("Data/recording_comparison.csv", "Data/recording_summary.csv")]
seen_sizes = {}
csv_files = []
for f in sorted(all_csvs):
    size = os.path.getsize(f)
    if size not in seen_sizes:
        seen_sizes[size] = f
        csv_files.append(f)
    else:
        print(f"Skipping duplicate: {f} (same content as {seen_sizes[size]})")

if not csv_files:
    print("No CSV files found!")
    exit()

print("=" * 60)
print(f"Found {len(csv_files)} CSV file(s):")
for i, f in enumerate(csv_files, 1):
    print(f"  {i}. {f}")
print("=" * 60)

# Ask for patient ID once at the start
patient_id = input("\nEnter patient ID for this batch (or press Enter to use folder names automatically): ").strip()
if not patient_id:
    print("\nNo patient ID entered — will use subfolder names automatically.")
    auto_patient = True
else:
    auto_patient = False
    print(f"\nRunning analysis for: {patient_id}")
print(f"Found {len(csv_files)} file(s) to process\n")

all_summaries = []

# ── Analyze each file ─────────────────────────────────────────────────────────
for csv_file in csv_files:
    pdf_lines = []

    # Use subfolder name as patient ID if auto mode
    if auto_patient:
        patient_id = os.path.basename(os.path.dirname(csv_file))

    # Prompt for session/activity name only
    print(f"\nFile {csv_files.index(csv_file)+1} of {len(csv_files)}: {csv_file}")
    session_name = input("  Enter activity/session name (e.g. Resting, Step Test, Balance): ").strip() or "Session"
    session_label = f"{patient_id}_{session_name}".replace(" ", "_")

    # Create output folder
    output_dir = os.path.join("Outputs", session_label)
    os.makedirs(output_dir, exist_ok=True)
    print(f"  Saving outputs to: {output_dir}/")

    df = pd.read_csv(csv_file)

    # ── Normalize column names (handle old and new CSV formats) ───────────────
    # New format has lowercase names — map them to the expected names
    col_map = {
        "timestamp":      "Timestamp",
        "heart_rate":     "Heart Rate (bpm)",
        "lung_volume":    "Lung Volume (L)",
        "t_htu":          "Ambient Temperature",
        "h_htu":          "Ambient Humidity",
        "t_bmpa":         "Temperature BMP A (°C)",
        "p_bmpa":         "Pressure BMP A (Pa)",
        "t_bmpb":         "Temperature BMP B (°C)",
        "p_bmpb":         "Pressure BMP B (Pa)",
        "t_bmpc":         "Temperature BMP C (°C)",
        "p_bmpc":         "Pressure BMP C Ambient (Pa)",
        "o2":             "O2 (%)",
        "co2":            "CO2 (%)",
        "imu_x":          "IMU X (m/s²)",
        "imu_y":          "IMU Y (m/s²)",
        "imu_z":          "IMU Z (m/s²)",
        "ppg_ir":         "PPG IR",
        "ppg_red":        "PPG Red",
        "bmi_gyro_x":     "BMI Gyro X (°/s)",
        "bmi_gyro_y":     "BMI Gyro Y (°/s)",
        "bmi_gyro_z":     "BMI Gyro Z (°/s)",
        "ppg_spo2":       "SpO2 (%)",
        "hrv_sdnn":       "HRV SDNN (ms)",
        "bat_state":      "Battery State (%)",
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

    # Handle elapsed time — new format may not have it, so calculate from timestamp
    if "Elapsed Time (ms)" not in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        t0 = df["Timestamp"].iloc[0]
        df["Elapsed Time (ms)"] = (df["Timestamp"] - t0).dt.total_seconds() * 1000
    else:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # Calculate pressure differentials if missing but raw sensors present
    if "Pressure Diff A-C (Pa)" not in df.columns:
        if "Pressure BMP A (Pa)" in df.columns and "Pressure BMP C Ambient (Pa)" in df.columns:
            df["Pressure Diff A-C (Pa)"] = df["Pressure BMP A (Pa)"] - df["Pressure BMP C Ambient (Pa)"]
    if "Pressure Diff B-C (Pa)" not in df.columns:
        if "Pressure BMP B (Pa)" in df.columns and "Pressure BMP C Ambient (Pa)" in df.columns:
            df["Pressure Diff B-C (Pa)"] = df["Pressure BMP B (Pa)"] - df["Pressure BMP C Ambient (Pa)"]

    time_s   = df["Elapsed Time (ms)"] / 1000
    duration = time_s.iloc[-1] - time_s.iloc[0]

    log(f"TCC ANALYSIS REPORT")
    log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Patient ID: {patient_id}  |  Session: {session_name}")
    log(f"File: {csv_file}")
    log(f"{'='*60}")
    log(f"Duration: {duration:.1f}s  |  Rows: {len(df)}")

    # Time of day
    start_time = df["Timestamp"].iloc[0]
    hour = start_time.hour
    if 5 <= hour < 12:   time_of_day = "Morning"
    elif 12 <= hour < 17: time_of_day = "Afternoon"
    elif 17 <= hour < 21: time_of_day = "Evening"
    else:                  time_of_day = "Night"
    log(f"Time of day: {time_of_day} ({start_time.strftime('%H:%M')})")

    # Data quality
    log(f"\nDATA QUALITY")
    log("-" * 60)
    key_cols = ["Heart Rate (bpm)", "SpO2 (%)", "HRV SDNN (ms)", "O2 (%)", "CO2 (%)", "Lung Volume (L)"]
    quality_score = 0
    quality_total = 0
    for col in key_cols:
        if col in df.columns:
            missing   = df[col].isna().sum()
            pct_present = 100 - (missing / len(df)) * 100
            status = "OK" if pct_present >= 90 else ("PARTIAL" if pct_present >= 50 else "MISSING")
            log(f"  [{status}] {col}: {pct_present:.0f}% present ({missing} missing rows)")
            quality_score += pct_present
            quality_total += 100
    overall_quality = quality_score / quality_total * 100
    log(f"\n  Overall data quality: {overall_quality:.0f}%")

    # Motion artifacts
    df["accel_magnitude"] = np.sqrt(df["IMU X (m/s²)"]**2 + df["IMU Y (m/s²)"]**2 + df["IMU Z (m/s²)"]**2)
    df["activity"]        = df["accel_magnitude"].rolling(window=15, center=True).std().fillna(0)
    motion_artifact_mask  = df["activity"] > 0.2
    artifact_pct          = motion_artifact_mask.mean() * 100
    hr_valid              = df["Heart Rate (bpm)"].notna()
    artifact_hr_pct       = ((motion_artifact_mask & hr_valid).sum() / hr_valid.sum() * 100) if hr_valid.sum() > 0 else 0

    log(f"\nMOTION ARTIFACTS")
    log("-" * 60)
    log(f"  High motion periods: {artifact_pct:.1f}% of recording")
    log(f"  Heart rate during high motion: {artifact_hr_pct:.1f}% (potentially unreliable)")

    # Anomaly flags
    log(f"\nANOMALY FLAGS")
    log("-" * 60)
    alerts   = []
    warnings = []

    for col, bounds in THRESHOLDS.items():
        if col not in df.columns: continue
        data = df[col].dropna()
        if len(data) == 0: continue
        if (data < bounds["critical_low"]).sum() > 0:
            alerts.append(f"CRITICAL: {col} dropped below {bounds['critical_low']} ({(data < bounds['critical_low']).sum()} readings)")
        if (data > bounds["critical_high"]).sum() > 0:
            alerts.append(f"CRITICAL: {col} exceeded {bounds['critical_high']} ({(data > bounds['critical_high']).sum()} readings)")
        warn_low  = ((data < bounds["low"])  & (data >= bounds["critical_low"])).sum()
        warn_high = ((data > bounds["high"]) & (data <= bounds["critical_high"])).sum()
        if warn_low  > 0: warnings.append(f"WARNING: {col} below normal ({warn_low} readings below {bounds['low']})")
        if warn_high > 0: warnings.append(f"WARNING: {col} above normal ({warn_high} readings above {bounds['high']})")

    # Breathing rate
    if "Pressure Diff A-C (Pa)" in df.columns:
        pressure = df["Pressure Diff A-C (Pa)"].values
        peaks, _ = find_peaks(pressure, distance=20)
    else:
        pressure = np.zeros(len(df))
        peaks = []
        log("  Note: Pressure differential not available — breathing rate cannot be calculated.")

    if len(peaks) >= 2:
        breaths_per_min = len(peaks) / (duration / 60)
        if breaths_per_min < BREATHING_CRITICAL[0] or breaths_per_min > BREATHING_WARNING[1]:
            alerts.append(f"CRITICAL: Breathing rate {breaths_per_min:.1f} breaths/min at rest (normal 12-20, critical >25 — Fieselmann et al. 1993)")
        elif breaths_per_min < BREATHING_NORMAL[0] or breaths_per_min > BREATHING_NORMAL[1]:
            warnings.append(f"WARNING: Breathing rate {breaths_per_min:.1f} breaths/min (normal: {BREATHING_NORMAL[0]}-{BREATHING_NORMAL[1]})")
    else:
        breaths_per_min = 0

    for a in alerts:   log(f"  !! {a}")
    for w in warnings: log(f"  -- {w}")
    if not alerts and not warnings:
        log("  OK - No anomalies detected")

    # Duration
    log(f"\nRECORDING DURATION")
    log("-" * 60)
    if duration < 30:
        log(f"  SHORT ({duration:.0f}s) - may not capture full cardiopulmonary picture")
    elif duration < 120:
        log(f"  OK - Adequate ({duration:.0f}s) — confirm minimum duration with Riipen")
    else:
        log(f"  OK - Good length ({duration:.0f}s)")

    # Posture & activity labels
    df["accel_mag_smooth"] = df["accel_magnitude"].rolling(window=10, center=True).mean().fillna(1)
    df["z_ratio"]          = df["IMU Z (m/s²)"].rolling(window=10, center=True).mean().fillna(0) / df["accel_mag_smooth"]
    df["posture"]          = df["z_ratio"].apply(lambda z: "Upright" if z > 0.85 else ("Leaning" if z > 0.5 else ("Reclined" if z > -0.3 else "Inverted")))
    df["activity_label"]   = df["activity"].apply(lambda v: "Still" if v < 0.05 else ("Light Movement" if v < 0.2 else "Active"))
    dominant_posture       = df["posture"].value_counts().idxmax()
    dominant_activity      = df["activity_label"].value_counts().idxmax()
    avg_hr                 = df["Heart Rate (bpm)"].mean()
    avg_spo2               = df["SpO2 (%)"].mean()

    # Health summary
    log(f"\nHEALTH SUMMARY")
    log("-" * 60)

    if avg_hr < 50:
        hr_summary = f"Averaged {avg_hr:.0f} bpm — low, possibly high fitness level or bradycardia. Monitor across sessions."
    elif avg_hr <= 100:
        hr_summary = f"Averaged {avg_hr:.0f} bpm — within normal resting range."
    else:
        hr_summary = f"Averaged {avg_hr:.0f} bpm — elevated. Could reflect exertion, stress, or underlying condition."
    log(f"  Heart Rate:    {hr_summary}")

    if avg_spo2 >= 95:
        spo2_summary = f"Averaged {avg_spo2:.1f}% — healthy oxygenation throughout recording."
    elif avg_spo2 >= 90:
        spo2_summary = f"Averaged {avg_spo2:.1f}% — warning range. Supplemental oxygen worth discussing with clinician."
    else:
        spo2_summary = f"Averaged {avg_spo2:.1f}% — critically low. Warrants immediate clinical attention."
    log(f"  SpO2:          {spo2_summary}")

    hrv_data = df["HRV SDNN (ms)"].dropna()
    if len(hrv_data) > 0:
        avg_hrv = hrv_data.mean()
        if avg_hrv >= 50:
            hrv_summary = f"Averaged {avg_hrv:.0f} ms — good heart rate variability, suggests healthy autonomic function."
        elif avg_hrv >= 20:
            hrv_summary = f"Averaged {avg_hrv:.0f} ms — low-normal HRV, may indicate stress or fatigue."
        else:
            hrv_summary = f"Averaged {avg_hrv:.0f} ms — very low HRV. Worth flagging for clinical review."
        log(f"  HRV SDNN:      {hrv_summary}")
    else:
        log(f"  HRV SDNN:      No data captured — sensor may not be active or recording too short.")

    co2_data = df["CO2 (%)"].dropna()
    if len(co2_data) > 0:
        avg_co2 = co2_data.mean()
        if avg_co2 <= 5.0:
            co2_summary = f"Averaged {avg_co2:.2f}% — within normal exhaled CO2 range."
        else:
            co2_summary = f"Averaged {avg_co2:.2f}% — elevated. May indicate hypoventilation or sensor proximity to face."
        log(f"  CO2:           {co2_summary}")
    else:
        log(f"  CO2:           No data captured.")

    lv_data = df["Lung Volume (L)"].dropna()
    if len(lv_data) > 0:
        avg_lv = lv_data.mean()
        log(f"  Lung Volume:   Averaged {avg_lv:.2f}L during recording.")
    else:
        log(f"  Lung Volume:   No data captured.")

    if breaths_per_min > 0:
        if BREATHING_NORMAL[0] <= breaths_per_min <= BREATHING_NORMAL[1]:
            br_summary = f"~{breaths_per_min:.0f} breaths/min — within normal adult range of 12-20."
        elif breaths_per_min > BREATHING_NORMAL[1]:
            br_summary = f"~{breaths_per_min:.0f} breaths/min — slightly elevated. Could reflect mild exertion or anxiety."
        else:
            br_summary = f"~{breaths_per_min:.0f} breaths/min — below normal range. May warrant review."
    else:
        br_summary = "Could not be reliably calculated from this recording."
    log(f"  Breathing:     {br_summary}")

    log(f"  Activity:      Person was {dominant_activity.lower()} for the majority of the recording.")
    log(f"  Posture:       Person was predominantly {dominant_posture.lower()} during the session.")
    log(f"  Time of Day:   Recording taken in the {time_of_day.lower()}.")

    if not alerts and not warnings:
        overall = "All readings appear within normal ranges. No immediate concerns identified."
    elif alerts:
        overall = f"{len(alerts)} critical alert(s) flagged — review with a clinician before next session."
    else:
        overall = f"{len(warnings)} warning(s) noted, no critical thresholds breached. Monitor across future sessions."
    log(f"\n  Overall:       {overall}")

    all_summaries.append({
        "File": csv_file, "Patient": patient_id, "Session": session_name,
        "Time of Day": time_of_day, "Duration (s)": round(duration, 1),
        "Avg HR (bpm)": round(avg_hr, 1), "Avg SpO2 (%)": round(avg_spo2, 1),
        "Breathing Rate": round(breaths_per_min, 1),
        "Data Quality (%)": round(overall_quality, 1),
        "Motion Artifacts (%)": round(artifact_pct, 1),
        "Critical Alerts": len(alerts), "Warnings": len(warnings),
    })

    # ── CHART 1: Vitals ───────────────────────────────────────────────────────
    fig1, axes1 = plt.subplots(3, 2, figsize=(14, 20))
    fig1.subplots_adjust(top=0.93, hspace=1.1)

    banner_text = None
    if alerts:
        banner_text = (f"!! {len(alerts)} CRITICAL ALERT(S) - REVIEW REQUIRED", "red", "white")
    elif warnings:
        banner_text = (f"!! {len(warnings)} WARNING(S) - monitor closely", "orange", "black")
    if banner_text:
        fig1.text(0.5, 0.978, banner_text[0], ha="center", fontsize=11, color=banner_text[2],
                 bbox=dict(boxstyle="round", facecolor=banner_text[1], alpha=0.8))
    fig1.text(0.5, 0.950, f"Vitals — {patient_id} / {session_name}", ha="center", fontsize=13, fontweight="bold")

    # 1. Heart Rate
    ax = axes1[0, 0]
    hr = df["Heart Rate (bpm)"].dropna()
    b  = THRESHOLDS["Heart Rate (bpm)"]
    hc = (hr < b["critical_low"]).any() or (hr > b["critical_high"]).any()
    hw = (hr < b["low"]).any() or (hr > b["high"]).any()
    y0, y1 = min(30, hr.min()-5), max(140, hr.max()+5)
    shade_zones(ax, b, y0, y1)
    for i in df[motion_artifact_mask].index:
        ax.axvspan(time_s.iloc[max(0,i-1)], time_s.iloc[min(len(df)-1,i+1)], alpha=0.15, color="gray", zorder=1)
    plot_segmented(ax, time_s[hr.index].values, hr.values, b)
    ax.set_ylim(y0, y1)
    set_titled(ax, "Heart Rate (gray = motion artifact)", hc, hw)
    ax.set_ylabel("bpm"); ax.set_xlabel("Time (s)")
    ax.legend(handles=LEGEND_ELS, fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Beats per minute. Normal 50-100 bpm.\nBlack = normal, orange = warning, red = critical. Gray = motion artifact.")

    # 2. SpO2
    ax = axes1[0, 1]
    spo2 = df["SpO2 (%)"].dropna()
    b    = THRESHOLDS["SpO2 (%)"]
    hc   = (spo2 < b["critical_low"]).any()
    hw   = (spo2 < b["low"]).any()
    shade_zones(ax, b, 84, 101)
    plot_segmented(ax, time_s[spo2.index].values, spo2.values, b)
    ax.set_ylim(84, 101)
    set_titled(ax, "SpO2 - Blood Oxygen Saturation", hc, hw)
    ax.set_ylabel("%"); ax.set_xlabel("Time (s)")
    ax.legend(handles=LEGEND_ELS, fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "% of blood carrying oxygen. Normal 95-100%.\nBlack = normal, orange = warning, red = critical.")

    # 3. HRV SDNN
    ax = axes1[1, 0]
    hrv = df["HRV SDNN (ms)"].dropna()
    if len(hrv) > 0:
        b  = THRESHOLDS["HRV SDNN (ms)"]
        hc = (hrv < b["critical_low"]).any() or (hrv > b["critical_high"]).any()
        hw = (hrv < b["low"]).any() or (hrv > b["high"]).any()
        y0, y1 = 0, max(250, hrv.max()+20)
        shade_zones(ax, b, y0, y1)
        plot_segmented(ax, time_s[hrv.index].values, hrv.values, b)
        ax.set_ylim(y0, y1)
        set_titled(ax, "HRV SDNN", hc, hw)
        ax.legend(handles=LEGEND_ELS, fontsize=7)
    else:
        ax.text(0.5, 0.5, "No HRV data in this recording", ha="center", va="center",
                transform=ax.transAxes, color="gray", fontsize=10)
        ax.set_title("HRV SDNN", color="black")
    ax.set_ylabel("ms"); ax.set_xlabel("Time (s)"); ax.grid(True, alpha=0.3)
    add_desc(ax, "Heart rate variability. Higher = healthier autonomic function.\nLow values may indicate stress, fatigue, or cardiovascular issues.")

    # 4. CO2
    ax = axes1[1, 1]
    co2 = df["CO2 (%)"].dropna()
    if len(co2) > 0:
        b  = THRESHOLDS["CO2 (%)"]
        hc = (co2 > b["critical_high"]).any()
        hw = (co2 > b["high"]).any()
        y0, y1 = 0, max(10, co2.max()+1)
        shade_zones(ax, b, y0, y1)
        plot_segmented(ax, time_s[co2.index].values, co2.values, b)
        ax.set_ylim(y0, y1)
        set_titled(ax, "CO2 (%)", hc, hw)
        ax.legend(handles=LEGEND_ELS, fontsize=7)
    else:
        ax.text(0.5, 0.5, "No CO2 data in this recording", ha="center", va="center",
                transform=ax.transAxes, color="gray", fontsize=10)
        ax.set_title("CO2 (%)", color="black")
    ax.set_ylabel("%"); ax.set_xlabel("Time (s)"); ax.grid(True, alpha=0.3)
    add_desc(ax, "CO2 % near sensor. Elevated values may indicate hypoventilation\nor sensor positioned close to exhaled breath.")

    # 5. Lung Volume
    ax = axes1[2, 0]
    lv = df["Lung Volume (L)"].dropna()
    if len(lv) > 0:
        b  = THRESHOLDS["Lung Volume (L)"]
        hc = (lv < b["critical_low"]).any() or (lv > b["critical_high"]).any()
        hw = (lv < b["low"]).any() or (lv > b["high"]).any()
        y0, y1 = 0, max(8, lv.max()+0.5)
        shade_zones(ax, b, y0, y1)
        plot_segmented(ax, time_s[lv.index].values, lv.values, b)
        ax.set_ylim(y0, y1)
        set_titled(ax, "Lung Volume (L)", hc, hw)
        ax.legend(handles=LEGEND_ELS, fontsize=7)
    else:
        ax.text(0.5, 0.5, "No Lung Volume data in this recording", ha="center", va="center",
                transform=ax.transAxes, color="gray", fontsize=10)
        ax.set_title("Lung Volume (L)", color="black")
    ax.set_ylabel("Liters"); ax.set_xlabel("Time (s)"); ax.grid(True, alpha=0.3)
    add_desc(ax, "Volume of air moved during breathing. Tidal volume ~0.5L at rest,\ndeep breaths up to 6L. Low values may indicate restricted breathing.")

    # 6. Ambient O2
    ax = axes1[2, 1]
    b   = THRESHOLDS["O2 (%)"]
    o2  = df["O2 (%)"]
    hc  = (o2 < b["critical_low"]).any() or (o2 > b["critical_high"]).any()
    hw  = (o2 < b["low"]).any() or (o2 > b["high"]).any()
    shade_zones(ax, b, 17, 22)
    plot_segmented(ax, time_s.values, o2.values, b)
    ax.set_ylim(17, 22)
    set_titled(ax, "Ambient O2 (%)", hc, hw)
    ax.set_ylabel("%"); ax.set_xlabel("Time (s)")
    ax.legend(handles=LEGEND_ELS, fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Oxygen % in surrounding air. Normal ~20.9%.\nDips may reflect exhaled breath near sensor.")

    chart1_path = os.path.join(output_dir, f"{session_label}_vitals.png")
    fig1.savefig(chart1_path, dpi=150, bbox_inches="tight")
    log(f"\nVitals chart saved to {chart1_path}")
    plt.show()

    # ── CHART 2: Movement & Environment ───────────────────────────────────────
    fig2, axes2 = plt.subplots(3, 2, figsize=(14, 20))
    fig2.subplots_adjust(top=0.93, hspace=1.1)
    if banner_text:
        fig2.text(0.5, 0.978, banner_text[0], ha="center", fontsize=11, color=banner_text[2],
                 bbox=dict(boxstyle="round", facecolor=banner_text[1], alpha=0.8))
    fig2.text(0.5, 0.950, f"Movement & Environment — {patient_id} / {session_name}",
              ha="center", fontsize=13, fontweight="bold")

    # 1. Pressure / Breathing
    ax = axes2[0, 0]
    bw = breaths_per_min > 0 and (breaths_per_min < BREATHING_NORMAL[0] or breaths_per_min > BREATHING_NORMAL[1])
    bc = breaths_per_min > 0 and (breaths_per_min < BREATHING_CRITICAL[0] or breaths_per_min > BREATHING_CRITICAL[1])
    if "Pressure Diff A-C (Pa)" in df.columns:
        ax.plot(time_s, df["Pressure Diff A-C (Pa)"], color="purple", linewidth=1.2, label="Pressure Diff")
        if len(peaks) >= 2:
            ax.plot(time_s.iloc[peaks], pressure[peaks], "x", color="red", markersize=6, label=f"Breaths (~{breaths_per_min:.0f}/min)")
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", label="Baseline")
    else:
        ax.text(0.5, 0.5, "No pressure differential data in this recording",
                ha="center", va="center", transform=ax.transAxes, color="gray", fontsize=10)
    set_titled(ax, "Pressure Differential A-C (Breathing)", bc, bw)
    ax.set_ylabel("Pa"); ax.set_xlabel("Time (s)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Air pressure difference between airway and environment.\nEach wave = one breath. Red X = detected breath peak.")

    # 2. Activity Level
    ax = axes2[0, 1]
    ax.axhspan(0.05, 0.2, alpha=0.08, color="orange", zorder=0, label="Light movement")
    ax.axhspan(0.2,  1.0, alpha=0.10, color="red",    zorder=0, label="Active")
    ax.plot(time_s, df["activity"], color="seagreen", linewidth=1.2, zorder=3, label="Activity")
    ax.axhline(0.05, color="orange", linestyle="--", linewidth=0.8)
    ax.axhline(0.2,  color="red",    linestyle="--", linewidth=0.8)
    ax.set_title("Activity Level", color="black")
    ax.set_ylabel("Movement Intensity"); ax.set_xlabel("Time (s)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Movement intensity from accelerometer.\nWhite = still, orange = light movement, red = active.")

    # 3. Posture
    ax = axes2[1, 0]
    ax.plot(time_s, df["z_ratio"], color="teal", linewidth=1.2, label="Tilt ratio")
    ax.axhline(0.85, color="green",      linestyle="--", linewidth=1.0, label="Upright threshold")
    ax.axhline(0.5,  color="goldenrod",  linestyle="--", linewidth=1.0, label="Leaning threshold")
    ax.axhline(-0.3, color="sienna",     linestyle="--", linewidth=1.0, label="Reclined threshold")
    ax.set_title("Posture Estimate", color="black")
    ax.set_ylabel("Tilt Ratio"); ax.set_xlabel("Time (s)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Device tilt as proxy for body posture.\nAbove green = upright, between lines = leaning, below brown = reclined.")

    # 4. IMU Accelerometer
    ax = axes2[1, 1]
    ax.plot(time_s, df["IMU X (m/s²)"],       color="royalblue",      label="X (side)",    alpha=0.9, linewidth=1.2)
    ax.plot(time_s, df["IMU Y (m/s²)"],       color="darkorange",     label="Y (forward)", alpha=0.9, linewidth=1.2)
    ax.plot(time_s, df["IMU Z (m/s²)"],       color="mediumvioletred",label="Z (up/down)", alpha=0.9, linewidth=1.2)
    ax.set_title("IMU Accelerometer (Raw)", color="black")
    ax.set_ylabel("m/s²"); ax.set_xlabel("Time (s)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Raw linear movement across 3 axes.\nSpikes indicate sudden movement or device adjustment.")

    # 5. IMU Gyroscope
    ax = axes2[2, 0]
    gyro_cols = {"Gyro X": "IMU Gyro X (rad/s)", "Gyro Y": "IMU Gyro Y (rad/s)", "Gyro Z": "IMU Gyro Z (rad/s)"}
    gyro_colors = {"Gyro X": "steelblue", "Gyro Y": "tomato", "Gyro Z": "mediumseagreen"}
    found_gyro = False
    for label, col in gyro_cols.items():
        if col in df.columns:
            ax.plot(time_s, df[col], color=gyro_colors[label], label=label, alpha=0.9, linewidth=1.2)
            found_gyro = True
    if not found_gyro:
        ax.text(0.5, 0.5, "No Gyroscope data in this recording", ha="center", va="center",
                transform=ax.transAxes, color="gray", fontsize=10)
    ax.set_title("IMU Gyroscope (Raw)", color="black")
    ax.set_ylabel("rad/s"); ax.set_xlabel("Time (s)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Rotation speed across 3 axes. Measures spinning/tilting of the device.\nHelps distinguish movement types and improve posture accuracy.")

    # 6. Temperature & Humidity
    ax   = axes2[2, 1]
    ax2b = ax.twinx()
    ax.plot(time_s,  df["Ambient Temperature"], color="tomato",     linewidth=1.2, label="Temp (C)")
    ax2b.plot(time_s, df["Ambient Humidity"],   color="dodgerblue", linewidth=1.2, linestyle="--", label="Humidity (%)")
    ax.set_title("Temperature & Humidity", color="black")
    ax.set_ylabel("C", color="tomato"); ax2b.set_ylabel("%", color="dodgerblue")
    ax.set_xlabel("Time (s)")
    l1, lab1 = ax.get_legend_handles_labels()
    l2, lab2 = ax2b.get_legend_handles_labels()
    ax.legend(l1+l2, lab1+lab2, fontsize=7); ax.grid(True, alpha=0.3)
    add_desc(ax, "Ambient temperature (red) and humidity (blue) around the device.\nExtreme values may affect sensor accuracy.")

    chart2_path = os.path.join(output_dir, f"{session_label}_movement.png")
    fig2.savefig(chart2_path, dpi=150, bbox_inches="tight")
    log(f"Movement chart saved to {chart2_path}")
    plt.show()

    log(f"\n{'='*60}")
    log("CLINICAL THRESHOLD SOURCES")
    log("=" * 60)
    for metric, bounds in THRESHOLDS.items():
        log(f"  {metric}: {bounds.get('source', 'N/A')}")
    log(f"  Breathing Rate: Fieselmann et al. J Gen Intern Med 1993; AHA/ACC Vital Signs Guidelines")
    log(f"\n  Note: Thresholds apply to resting recordings.")
    log(f"  Exercise thresholds differ — see AeroCardia Protocol Appendix A5.")
    log(f"  Flags do not constitute diagnosis. Warrants clinical follow-up if persistent.")
    pdf_path = os.path.join(output_dir, f"{session_label}_report.pdf")
    with PdfPages(pdf_path) as pdf:
        lines_per_page = 55
        chunks = [pdf_lines[i:i+lines_per_page] for i in range(0, len(pdf_lines), lines_per_page)]
        for chunk in chunks:
            fig_pdf, ax_pdf = plt.subplots(figsize=(8.5, 11))
            ax_pdf.axis("off")
            ax_pdf.text(0.02, 0.98, "\n".join(chunk), transform=ax_pdf.transAxes,
                        fontsize=8, va="top", fontfamily="monospace")
            pdf.savefig(fig_pdf, bbox_inches="tight")
            plt.close(fig_pdf)
    print(f"PDF report saved to {pdf_path}")

# ── Comparison summary ────────────────────────────────────────────────────────
if len(all_summaries) > 1:
    print(f"\n{'='*60}\nMULTI-RECORDING COMPARISON\n{'='*60}")
    summary_df = pd.DataFrame(all_summaries)
    print(summary_df.to_string(index=False))
    summary_df.to_csv(os.path.join("Outputs", "recording_comparison.csv"), index=False)
    print("Comparison saved to Outputs/recording_comparison.csv")
else:
    pd.DataFrame(all_summaries).to_csv(os.path.join("Outputs", "recording_summary.csv"), index=False)

print("\nAll done!")
