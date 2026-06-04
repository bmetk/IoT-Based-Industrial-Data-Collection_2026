# This script fills missing values for the selected ".xlsx" dataset using interpolation and forward/backward filling.

import pandas as pd

FEATURE_COLUMNS = [
    "vibX_rms","vibX_fft_peak",
    "vibY_rms","vibY_fft_peak",
    "vibZ_rms","vibZ_fft_peak"
]

STATE_COLUMNS = [
    "current_mean",
    "current_imbalance",
    "rpm",
    "tempC"
]

df = pd.read_excel("high-rpm_high-stress.xlsx")

# Time index
df["_time"] = pd.to_datetime(df["_time"], utc=True)
df = df.sort_values("_time").set_index("_time")
df.index = df.index.tz_localize(None)

# Interpolation
df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].interpolate(
    method="time",
    limit=5,
    limit_direction="both"
)

# Fill
df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].ffill(limit=2)
df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].bfill(limit=2)

df[STATE_COLUMNS] = df[STATE_COLUMNS].interpolate(
    method="time",
    limit_direction="both"
)

df = df.dropna(subset=FEATURE_COLUMNS + STATE_COLUMNS)

print("Remaining Samples:", len(df))

df.to_excel("high-rpm_high-stress_filled.xlsx")
