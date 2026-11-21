import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

EXCEL_FILE = "Real_Space_Weather_Oct_Nov_2026.xlsx"
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)

Y_MAX_CPM = 110.0         # Clean headroom for legend while keeping background clear
SPIKE_THRESHOLD = 150.0   # Threshold (CPM) for despiked 3-hourly statistics

# ==========================================
# 1. Load & Clean Local Geiger-Müller CPM Data (IST)
# ==========================================
files = glob.glob("Data/*.csv")
dfs = []
for f in files:
    try:
        df = pd.read_csv(f, on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df["Radiation_CPM"] = pd.to_numeric(df.get("Radiation_CPM"), errors="coerce")
        df["Source"] = f
        dfs.append(df)
    except Exception as e:
        print(f"Error reading {f}: {e}")

if not dfs:
    raise FileNotFoundError("No valid CSV files found in Data/*.csv")

cpm_data = pd.concat(dfs, ignore_index=True)
if not {"Date", "Time"}.issubset(cpm_data.columns):
    raise KeyError("CSV files must contain 'Date' and 'Time' columns.")

cpm_data["Datetime"] = pd.to_datetime(
    cpm_data["Date"].astype(str) + " " + cpm_data["Time"].astype(str),
    errors="coerce"
).dt.tz_localize(None)

cpm_data = (
    cpm_data.dropna(subset=["Datetime", "Radiation_CPM"])
    .sort_values("Datetime")
    .reset_index(drop=True)
)

# Time-aware 1-hour rolling median (min_periods=30 avoids startup drop artifacts)
cpm_data["CPM_1h_Median"] = (
    cpm_data.set_index("Datetime")["Radiation_CPM"]
    .rolling("1h", min_periods=30)
    .median()
    .to_numpy()
)

# ==========================================
# 2. Load Real Space Weather Sheets & Align to IST
# ==========================================
merged_data = cpm_data.copy()
has_solar_wind = False
sw_speed_col = None
kp_df = pd.DataFrame()
xrs_df = pd.DataFrame()

# 2a. GFZ Potsdam 3-Hourly Kp Index
try:
    kp_df = pd.read_excel(EXCEL_FILE, sheet_name="GFZ_Kp_3Hourly")
    kp_df["Datetime_UTC"] = pd.to_datetime(kp_df["Datetime_UTC"], errors="coerce").dt.tz_localize(None)
    kp_df["Datetime_IST"] = kp_df["Datetime_UTC"] + IST_OFFSET
    kp_df["Kp_Index"] = pd.to_numeric(kp_df["Kp_Index"], errors="coerce")
    kp_df = kp_df.dropna(subset=["Datetime_IST"]).sort_values("Datetime_IST")

    merged_data = pd.merge_asof(
        merged_data,
        kp_df[["Datetime_IST", "Kp_Index"]],
        left_on="Datetime",
        right_on="Datetime_IST",
        direction="backward",
        tolerance=pd.Timedelta(hours=3)
    ).drop(columns=["Datetime_IST"])
except Exception as e:
    print(f"Warning: Could not load GFZ_Kp_3Hourly: {e}")

# 2b. NOAA GOES-18 1-Minute XRS Flux
try:
    xrs_df = pd.read_excel(EXCEL_FILE, sheet_name="NOAA_GOES_XRS_1Min")
    xrs_df["Datetime_UTC"] = pd.to_datetime(xrs_df["Datetime_UTC"], errors="coerce").dt.tz_localize(None)
    xrs_df["Datetime_IST"] = xrs_df["Datetime_UTC"] + IST_OFFSET
    xrs_df["XRS_B_0.1_0.8nm_Wm2"] = pd.to_numeric(xrs_df["XRS_B_0.1_0.8nm_Wm2"], errors="coerce")
    xrs_df.loc[xrs_df["XRS_B_0.1_0.8nm_Wm2"] <= 0, "XRS_B_0.1_0.8nm_Wm2"] = np.nan
    xrs_df = xrs_df.dropna(subset=["Datetime_IST"]).sort_values("Datetime_IST")

    merged_data = pd.merge_asof(
        merged_data,
        xrs_df[["Datetime_IST", "XRS_B_0.1_0.8nm_Wm2"]],
        left_on="Datetime",
        right_on="Datetime_IST",
        direction="nearest",
        tolerance=pd.Timedelta(minutes=2)
    ).drop(columns=["Datetime_IST"])
except Exception as e:
    print(f"Warning: Could not load NOAA_GOES_XRS_1Min: {e}")

# 2c. Optional NASA OMNI Solar Wind (auto-enabled after HAPI fix)
try:
    omni_df = pd.read_excel(EXCEL_FILE, sheet_name="NASA_OMNI_SolarWind")
    if "Datetime_UTC" in omni_df.columns:
        for candidate in ["flow_speed", "V", "Solar Wind Speed (km/s)"]:
            if candidate in omni_df.columns:
                sw_speed_col = candidate
                break
        if sw_speed_col:
            omni_df["Datetime_UTC"] = pd.to_datetime(omni_df["Datetime_UTC"], errors="coerce").dt.tz_localize(None)
            omni_df["Datetime_IST"] = omni_df["Datetime_UTC"] + IST_OFFSET
            omni_df[sw_speed_col] = pd.to_numeric(omni_df[sw_speed_col], errors="coerce")
            omni_df = omni_df.dropna(subset=["Datetime_IST"]).sort_values("Datetime_IST")

            merged_data = pd.merge_asof(
                merged_data,
                omni_df[["Datetime_IST", sw_speed_col]],
                left_on="Datetime",
                right_on="Datetime_IST",
                direction="nearest",
                tolerance=pd.Timedelta(minutes=5)
            ).drop(columns=["Datetime_IST"])
            has_solar_wind = merged_data[sw_speed_col].notna().any()
except Exception as e:
    print(f"Note: NASA_OMNI_SolarWind not available yet ({e})")

# ==========================================
# 3. 3-Hourly Aggregated Statistics (Matches GFZ Kp Bins)
# ==========================================
if not kp_df.empty:
    tmp = cpm_data[["Datetime", "Radiation_CPM"]].copy()
    tmp["Bin_3H_UTC"] = (tmp["Datetime"] - IST_OFFSET).dt.floor("3h")

    agg_raw = tmp.groupby("Bin_3H_UTC").agg(
        CPM_Mean_Raw=("Radiation_CPM", "mean"),
        CPM_Median=("Radiation_CPM", "median"),
        Samples=("Radiation_CPM", "count"),
    )
    agg_clean = (
        tmp[tmp["Radiation_CPM"] <= SPIKE_THRESHOLD]
        .groupby("Bin_3H_UTC")
        .agg(CPM_Mean_Clean=("Radiation_CPM", "mean"))
    )

    bins_3h = (
        agg_raw.join(agg_clean, how="left")
        .reset_index()
        .merge(kp_df[["Datetime_UTC", "Kp_Index"]], left_on="Bin_3H_UTC", right_on="Datetime_UTC", how="inner")
    )

    if not xrs_df.empty:
        xrs_3h = (
            xrs_df.assign(Bin_3H_UTC=xrs_df["Datetime_UTC"].dt.floor("3h"))
            .groupby("Bin_3H_UTC")["XRS_B_0.1_0.8nm_Wm2"]
            .max()
            .reset_index()
        )
        bins_3h = bins_3h.merge(xrs_3h, on="Bin_3H_UTC", how="left")

    print(f"\n=== 3-HOURLY AGGREGATED CORRELATIONS (n = {len(bins_3h)} 3-hour bins) ===")
    for col, label in [("CPM_Mean_Raw", "Raw 3h Mean"), ("CPM_Mean_Clean", f"Despiked (<={SPIKE_THRESHOLD:.0f})"), ("CPM_Median", "3h Median")]:
        rp = bins_3h[col].corr(bins_3h["Kp_Index"], method="pearson")
        rs = bins_3h[col].corr(bins_3h["Kp_Index"], method="spearman")
        print(f"Kp vs {label:<22}: Pearson r = {rp:+.4f} | Spearman rho = {rs:+.4f}")

    if "XRS_B_0.1_0.8nm_Wm2" in bins_3h.columns and bins_3h["XRS_B_0.1_0.8nm_Wm2"].notna().any():
        log_xrs_3h = np.log10(bins_3h["XRS_B_0.1_0.8nm_Wm2"])
        rp = bins_3h["CPM_Mean_Clean"].corr(log_xrs_3h, method="pearson")
        rs = bins_3h["CPM_Mean_Clean"].corr(log_xrs_3h, method="spearman")
        print(f"log10(XRS-B max) vs Despiked: Pearson r = {rp:+.4f} | Spearman rho = {rs:+.4f} (n = {log_xrs_3h.notna().sum()})")

    bins_3h["Kp_Regime"] = pd.cut(
        bins_3h["Kp_Index"],
        bins=[-0.1, 3.99, 4.99, 9.5],
        labels=["Quiet (Kp < 4)", "Active (4 <= Kp < 5)", "Storm (Kp >= 5)"]
    )
    print("\n=== 3-HOURLY CPM BY GEOMAGNETIC REGIME ===")
    print(
        bins_3h.groupby("Kp_Regime", observed=False)
        .agg(
            bins_3h=("Kp_Index", "count"),
            mean_raw=("CPM_Mean_Raw", "mean"),
            mean_despiked=("CPM_Mean_Clean", "mean"),
            std_despiked=("CPM_Mean_Clean", "std"),
            median_of_medians=("CPM_Median", "median"),
        )
        .round(2)
    )

n_clipped = int((merged_data["Radiation_CPM"] > Y_MAX_CPM).sum())
print(f"\nNote for caption: {n_clipped} transient samples exceeded {Y_MAX_CPM:.0f} CPM (max = {merged_data['Radiation_CPM'].max():.1f} CPM).")

# ==========================================
# 4. Clean Publication-Ready Plot
# ==========================================
panels = []
if has_solar_wind:
    panels.append(("sw", "Solar Wind Speed (km/s)", "darkorange"))
panels.append(("xrs", "GOES-18 XRS-B Flux (W/m²)", "#D97706"))
panels.append(("kp", "GFZ Geomagnetic Kp Index", "#15803D"))

ncols = len(panels)
fig, axes = plt.subplots(nrows=1, ncols=ncols, figsize=(7.2 * ncols, 5.8), sharey=True)
if ncols == 1:
    axes = [axes]

x_index = np.arange(len(merged_data))
num_ticks = min(10, len(merged_data))
tick_positions = np.linspace(0, len(merged_data) - 1, num_ticks, dtype=int)
tick_labels = merged_data["Datetime"].iloc[tick_positions].dt.strftime("%Y-%m-%d %H:%M")
panel_letters = ["(a)", "(b)", "(c)"]

for idx, (ax, (kind, ylabel_r, color_r)) in enumerate(zip(axes, panels)):
    p_raw, = ax.plot(
        x_index, merged_data["Radiation_CPM"],
        label="Radiation CPM (raw)", color="#9333EA", alpha=0.22, linewidth=0.6
    )
    p_med, = ax.plot(
        x_index, merged_data["CPM_1h_Median"],
        label="Radiation CPM (1h median)", color="#581C87", alpha=0.95, linewidth=1.35
    )

    ax.set_ylim(0, Y_MAX_CPM)
    if idx == 0:
        ax.set_ylabel("Radiation (Counts Per Minute)", color="#581C87", fontweight="bold")
    ax.tick_params(axis="y", labelcolor="#581C87")

    ax_r = ax.twinx()
    p_sw = None

    if kind == "sw":
        p_sw, = ax_r.plot(
            x_index, merged_data[sw_speed_col],
            label="Solar Wind Speed", color=color_r, alpha=0.85, linewidth=1.0
        )
        title = f"{panel_letters[idx]} Radiation CPM vs. Solar Wind Speed\n(Active Logging Only, IST)"

    elif kind == "xrs" and "XRS_B_0.1_0.8nm_Wm2" in merged_data.columns:
        p_sw, = ax_r.plot(
            x_index, merged_data["XRS_B_0.1_0.8nm_Wm2"],
            label="GOES-18 XRS-B (0.1–0.8 nm)", color=color_r, alpha=0.85, linewidth=0.95
        )
        ax_r.set_yscale("log")
        ax_r.set_ylim(1e-7, 3e-4)
        ax_r.axhline(1e-5, color=color_r, linestyle=":", linewidth=1.1, alpha=0.85)
        title = f"{panel_letters[idx]} Radiation CPM vs. Solar X-Ray Flux\n(Active Logging Only, IST)"

    elif kind == "kp" and "Kp_Index" in merged_data.columns:
        p_sw, = ax_r.plot(
            x_index, merged_data["Kp_Index"],
            label="GFZ Kp Index", color=color_r, alpha=0.85, linewidth=1.25, drawstyle="steps-post"
        )
        ax_r.set_ylim(0, 9.5)
        ax_r.axhline(5.0, color="crimson", linestyle=":", linewidth=1.1, alpha=0.85)
        title = f"{panel_letters[idx]} Radiation CPM vs. Geomagnetic Kp Index\n(Active Logging Only, IST)"

    ax_r.set_ylabel(ylabel_r, color=color_r, fontweight="bold")
    ax_r.tick_params(axis="y", labelcolor=color_r)

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=9)
    ax.set_xlabel("Date and Time (IST)", fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, linestyle="--", alpha=0.45)

    lines = [p_raw, p_med] + ([p_sw] if p_sw is not None else [])
    ax.legend(lines, [l.get_label() for l in lines], loc="upper right", fontsize=8.8, framealpha=0.94)

plt.tight_layout()
output_png = "CPM_vs_Real_Space_Weather_Clean0.png"
plt.savefig(output_png, dpi=300, bbox_inches="tight")
print(f"Plot saved as {output_png}")