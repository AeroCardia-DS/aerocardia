## Overview
Exploratory analysis of AeroCardia wearable device recordings. I built an automated analysis script to handle data quality checks, anomaly flagging, visualization, and health summaries across both data formats.

Cross-Dataset Findings
1. Two Different Data Formats

Client001 and Client002 data came in completely different CSV formats with different column names and structures. Any analysis pipeline needs to handle both — and it raises a question about data standardization across devices.

Recommendation: Standardize data format and column naming conventions across all devices and clients.

2. O2 Consistently Below Normal

O2% reads below normal across most recordings. Reasoning?

Recommendation: Review O2 sensor placement guidelines.

3. Erroneous Data at Recording Start

Heart rate spikes at the start of recordings (up to 120 bpm) before dropping to a stable range — consistent with device placement movement, confirmed by the IMU data. Similar artifacts may occur at recording end.

Recommendation: Flag and exclude the first and last 5-10 seconds (more if it was already included). Worth adding a method to catch mid-recording data drops too, since those skew averages and make data unusable.

4. Activity Context Missing from Raw Data

No activity label exists in the raw data files. Thresholds differ substantially between rest and exercise — a 120 bpm heart rate is a warning at rest but normal during a step test. Without activity labels, alerts generate false positives.

Recommendation: Add activity labels to data exports or establish a file naming convention.

5. Baseline Standardization Needed

The same thresholds are applied across all subjects. Meaningful interpretation requires baselines per age, gender, and health status.

Recommendation: Define subject-specific baselines for personalized alert accuracy.

6. Client Data Access and Alert Timeliness

Do clients receive their data and alerts immediately after recording? For a home warning device, timeliness is critical.

Recommendation: Confirm real-time or near-real-time alerting is in place for critical biometrics, when ready. 

7. Activity Selection and Recording Duration

How were activities and recording durations chosen? Some activities may generate more useful data than others.

Recommendation: Test minimum recording durations per activity for accuracy. Worth evaluating whether all activities are clinically necessary to save client time.

8. Recording Duration Too Short for HRV

Client001's recording is only 36 seconds. HRV SDNN calculation requires a minimum of 120 seconds of clean data (Task Force ESC/NASPE 1996).

Recommendation: Extend minimum recording duration to at least 120 seconds across all sessions.