# AeroCardia System Consistency & Operational Efficiency Analysis

## 📖 Project Overview
Repository for the **AeroCardia System Consistency & Operational Efficiency Project**. This collaborative academic initiative is designed to analyze physiological testing datasets to identify system performance correlations, unearth process inefficiencies, and pinpoint opportunities for operational improvements. 

By leveraging Design of Experiments (DOE) testing outcomes, our team aims to provide data-driven recommendations that optimize operations, reduce costs, and increase overall system consistency. Furthermore, this project serves as a hands-on environment for participants to enhance their skills in statistical analysis, data modeling, and cross-functional communication.

---

## 🎯 Business Context & Goals

### Project Goals
1. **Analyze** testing datasets to identify correlations and opportunities for system improvements.
2. **Provide** data-driven recommendations to optimize operations and reduce costs.
3. **Enhance** participants’ skills in statistical analysis, data modeling, and communicating results to non-technical audiences.
4. **Suggest** outcomes from our DOE tests to increase system consistency.

### Project Outcomes
* Clear identification of process inefficiencies and performance bottlenecks within the testing systems.
* Actionable, prioritized recommendations to improve operational efficiency and productivity.
* Stakeholder-ready reports and interactive visualizations that drive informed decision-making.

### Project Deliverables
* Cleaned and analyzed operational dataset with derived key performance metrics.
* Comprehensive statistical analysis report highlighting inefficiencies and root causes.
* Visualizations and dashboards illustrating key findings from the testing data.
* Final presentation with prioritized recommendations for process improvements and system calibration.

---


## 🗂️ Data Sources

This project relies on two primary files provided by the stakeholders:

1. **`AeroCardia Data Dictionary Basic.xlsx`**
   * **Description:** The planned list of features and metrics captured by the system. It details feature names, definitions, theoretical equations for calculation, and metric categories.
   * **Key Metric Categories Include:**
     * **Cardiac:** Heart Rate (HR), Heart Rate Variability (HRV), Cardiac Output (CO), Stroke Volume (SV).
     * **Pulmonary:** Alveolar Ventilation (VA), Breathing Efficiency, Dead Space Ventilation (VD), Oxygen Delivery (DO2), Respiratory Exchange Ratio (RER), VO2, VO2max.
     * **Other:** Core Body Temperature estimates, Physical Activity Level (PAL), Posture/Gait Analysis, Hydration and Metabolic Stress Correlations.

2. **`Riipen TCC Data 1.csv`**
   * **Description:** The primary testing dataset containing the raw and calculated physiological logs generated during DOE testing. This data will be cleaned, merged, and analyzed to evaluate system consistency.

---

## 📅 8-Week Project Timeline

*This project is scoped for an 8-week sprint, requiring approximately 50 hours per participant (avg. 6-7 hours/week).*

* **Week 1 – Project Kickoff & Data Understanding (5 hrs)**
  * Define project scope, KPIs, and success criteria.
  * Review datasets (`Riipen TCC Data 1.csv`), data dictionaries (`AeroCardia Data Dictionary Basic.xlsx`), and context for testing.
* **Week 2 – Data Cleaning & Integration (6 hrs)**
  * Clean and preprocess testing data. Handle missing values and outliers.
  * Integrate multiple data sources as needed (e.g., testing logs).
* **Week 3 – Exploratory Data Analysis (6 hrs)**
  * Conduct statistical analysis to identify trends, anomalies, and bottlenecks.
  * Share initial findings with the team for feedback.
* **Week 4 – Metric Development & Hypothesis Testing (6 hrs)**
  * Define key testing metrics (e.g., signal quality, hardware consistency).
  * Test hypotheses to validate the root causes of system inefficiencies.
* **Week 5 – Visualization & Reporting (7 hrs)**
  * Develop visualizations (dashboards, charts) to represent findings clearly.
  * Draft the interim report with preliminary recommendations.
* **Week 6 – Recommendation Development (6 hrs)**
  * Refine insights and translate statistical analysis into actionable business/engineering recommendations.
  * Prioritize recommendations based on impact (ROI) and feasibility.
* **Week 7 – Final Report & Documentation (7 hrs)**
  * Compile the final report including methodology, statistical analysis, and recommendations.
  * Prepare supporting documentation (like this repository) for long-term use and reproducibility.
* **Week 8 – Presentation & Handover (7 hrs)**
  * Present findings and recommendations to stakeholders.
  * Deliver the final report, visualizations, and complete documentation package.

---

## 📂 Repository Structure (Suggested)

```text
├── data/
│   ├── raw/                 # Original, immutable datasets (e.g., Riipen TCC Data 1.csv)
│   ├── processed/           # Cleaned data ready for analysis
│   └── dictionary/          # Data dictionaries (e.g., AeroCardia Data Dictionary Basic.xlsx)
├── notebooks/               # Jupyter notebooks for EDA, Hypothesis Testing, and Modeling
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda_and_correlations.ipynb
│   └── 03_doe_analysis.ipynb
├── src/                     # Reusable Python scripts (helper functions)
│   ├── data_processing.py
│   └── visual_helpers.py
├── reports/                 # Interim and Final Reports (PDF/Markdown)
│   ├── figures/             # Exported PNG/SVG charts for presentations
│   └── Final_Analysis_Report.pdf
├── requirements.txt         # Python dependencies
└── README.md                # Project overview and instructions
```

---

## 🚀 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd aerocardia-system-analysis
   ```
2. **Set up a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Standard libraries include: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `jupyter`)*

---
## 🤝 Team Guidelines
* **Collaboration:** Commit code frequently and use pull requests for major notebook changes.
* **Documentation:** Comment heavily on complex physiological calculations derived from the data dictionary.
* **Focus:** Always tie statistical findings back to the core business goal: *How does this improve system consistency or operational efficiency?*
