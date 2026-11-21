# esp32-geiger-weather-irradiance

Supplementary datasets, analysis scripts, and machine learning notebooks for the manuscript:

---

## Overview

This repository provides the reproducible datasets, Python scripts, Jupyter notebooks, and generated figures supporting our synchronized dual-node ESP32 IoT system for:

1. **Background Radiation & Space-Weather Correlation (`CPM_and_Solar_flare_CME/`)** — Continuous 1-second Geiger-Müller (GM) logging (`821,356` active samples across 24 daily CSV files, October 3–November 16, 2026 IST) cross-referenced against real 1-minute [NOAA GOES-18 EXIS/XRS](https://www.google.com/search?q=https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes18/l2/data/xrsf-l2-avg1m) solar X-ray flux and 3-hourly [GFZ Potsdam Kp](https://kp.gfz-potsdam.de/app/json/) geomagnetic indices.
2. **Low-Cost Solar Irradiance Estimation (`Solar_irradiance/`)** — Multiple linear regression model predicting solar irradiance (W/m²) from binary-colored aluminum plate differential temperature (`T2 − T3`), ambient temperature, relative humidity, and BH1750 light intensity (`n = 117` samples).
3. **Edge Weather Condition Classification (`Weather_Random_forest_classifier/`)** — Random Forest Classifier (`25` trees, `max_depth = 8`, `n = 2,327` samples) trained for on-device deployment (`weather.h`) on an ESP32 microcontroller.

---

## Repository Structure

```text
.
├── CPM_and_Solar_flare_CME/
│   ├── CMP_and_CME_solar_flare.py            # Aligns GM CPM with GOES-18 XRS & GFZ Kp; computes 3-hourly stats & plot
│   ├── CPM_plot.py                           # Generates active-logging radiation CPM time-series plot
│   ├── fetch_space_weather_oct_nov_2026.ipynb# Downloads GFZ Kp, NOAA GOES-18 XRS, and NASA OMNI data to Excel
│   ├── Real_Space_Weather_Oct_Nov_2026.xlsx  # Multi-sheet space-weather archive (Oct 1 – Nov 21, 2026 UTC)
│   ├── CPM_vs_Real_Space_Weather_Clean0.png  # Figure 5: CPM vs. GOES-18 XRS-B and GFZ Kp Index
│   ├── radiation_plot.png                    # Figure 3: Active-logging Geiger-Müller CPM time series
│   └── Data/
│       ├── 2026_10_03.csv                    # Daily ESP32 + RTC Geiger-Müller logs (IST)
│       ├── ...                               # (24 daily CSV files, Oct 3 – Nov 16, 2026)
│       └── 2026_11_16.csv
├── Solar_irradiance/
│   ├── Solar_irradicane_model.ipynb          # Multiple linear regression training & evaluation
│   ├── total_solar_comparison.png            # Figure 2: Estimated vs. reference solar irradiance
│   └── data/
│       └── Filtered_Train_dataset_v2.xlsx    # Combined 117-sample calibration & test dataset
└── Weather_Random_forest_classifier/
    ├── Weather_Random_forest.ipynb           # Random Forest training, evaluation & ESP32 header export
    └── Project 1 - Weather Dataset.csv       # 2,327-sample meteorological dataset (Clear, Cloudy, Rain, Snow)
```

---

## Key Results Summary

| Module | Dataset / Cadence | Key Metrics |
| :--- | :--- | :--- |
| **Solar Irradiance Model** | `117` samples (80/20 split) | `R² = 0.98`, `RMSE = 38.22 W/m²`, `MAE = 33.17 W/m²`, `MBE = 2.99 W/m²` |
| **Weather Classifier (RF)** | `2,327` samples (25 trees, depth 8) | Overall Accuracy `0.65` (Snow F1 `83.65%`, Rain `68.72%`, Clear `57.92%`, Cloudy `46.15%`) |
| **GM CPM vs. Solar X-Ray (XRS-B)** | `100` aligned 3-hour UTC bins | `Pearson r = +0.0770`, `Spearman ρ = +0.1159` (no ground-level flare response) |
| **GM CPM vs. Geomagnetic Kp** | `100` aligned 3-hour UTC bins (despiked `≤ 150 CPM`) | `Pearson r = -0.3355`, `Spearman ρ = -0.3992` (Quiet `40.08 ± 6.16`, Active `36.97 ± 2.16`, Storm `36.43 ± 1.53 CPM`) |

---

## Quick Start

### Requirements

- Python 3.9+
- Core packages: `pandas`, `numpy`, `matplotlib`, `openpyxl`, `scikit-learn`, `requests`, `xarray`, `netCDF4`

```bash
pip install pandas numpy matplotlib openpyxl scikit-learn requests xarray netCDF4
```

### Reproducing the Space-Weather & Radiation Analysis

```bash
cd CPM_and_Solar_flare_CME
python CPM_plot.py
python CMP_and_CME_solar_flare.py
```

To refresh the upstream space-weather workbook (`Real_Space_Weather_Oct_Nov_2026.xlsx`), open and run `fetch_space_weather_oct_nov_2026.ipynb` in Jupyter or Google Colab.

### Reproducing the ML Models

- **Solar Irradiance:** Run `Solar_irradiance/Solar_irradicane_model.ipynb`
- **Weather Classifier:** Run `Weather_Random_forest_classifier/Weather_Random_forest.ipynb`

---

## External Space-Weather Data Sources

- **Geomagnetic Kp Index:** Matzka et al. (2021), GFZ German Research Centre for Geosciences, `doi:10.5880/Kp.0001` — [GFZ Kp API](https://kp.gfz-potsdam.de/app/json/)
- **Solar X-Ray Flux (GOES-18 EXIS/XRS Level 2, 1-min):** [NOAA NCEI GOES-18 Archive](https://www.google.com/search?q=https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes18/l2/data/xrsf-l2-avg1m) & [NOAA SWPC Real-Time JSON](https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json)
- **Solar Wind (Optional OMNIWeb):** King & Papitashvili (2005), [NASA/GSFC SPDF CDAWeb HAPI](https://cdaweb.gsfc.nasa.gov/hapi)

---


## Contact

For questions or additional data requests, contact **Tamal Sarkar** (`tsarkar@nbu.ac.in`).
