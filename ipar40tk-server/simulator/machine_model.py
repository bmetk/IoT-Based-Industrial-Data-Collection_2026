import pandas as pd
import numpy as np
import random
import json
import ast
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

BASE_PATH = Path("/app/baselines")

STATE_FILES = {
    "low-rpm_idle_filled": "low-rpm_idle_filled_simulator.xlsx",
    "mid-rpm_idle_filled": "mid-rpm_idle_filled_simulator.xlsx",
    "high-rpm_idle_filled": "high-rpm_idle_filled_simulator.xlsx",
    "low-rpm_low-stress_filled": "low-rpm_low-stress_filled_simulator.xlsx",
    "mid-rpm_low-stress_filled": "mid-rpm_low-stress_filled_simulator.xlsx",
    "high-rpm_low-stress_filled": "high-rpm_low-stress_filled_simulator.xlsx",
    "low-rpm_high-stress_filled": "low-rpm_high-stress_filled_simulator.xlsx",
    "mid-rpm_high-stress_filled": "mid-rpm_high-stress_filled_simulator.xlsx",
    "high-rpm_high-stress_filled": "high-rpm_high-stress_filled_simulator.xlsx",

}

CACHE = {}

# ============================================================
# HELPERS
# ============================================================

def get_state_key(rpm_mode, load):

    load_map = {
        "idle": "idle",
        "low": "low-stress",
        "high": "high-stress"
    }

    speed_map = {
        "low": "low-rpm",
        "medium": "mid-rpm",
        "mid": "mid-rpm",
        "high": "high-rpm"
    }

    speed = speed_map.get(rpm_mode, "low-rpm")
    load_state = load_map.get(load, "idle")

    return f"{speed}_{load_state}_filled"


def parse_amp(value):

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        return ast.literal_eval(value)

    return [0.0, 0.0, 0.0]


def parse_vibration(value):

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        return json.loads(value)

    return {"s": 0, "c": 128, "d": []}


def random_variation(value, pct=0.05):

    delta = abs(value) * pct

    return value + np.random.uniform(-delta, delta)


def apply_fault_scalar(value, fault, intensity):

    if not fault:
        return value

    if fault == "bearing":
        value *= (1 + 0.10 * intensity)

    elif fault == "imbalance":
        value *= (1 + 0.15 * intensity)

    elif fault == "misalignment":
        value *= (1 + 0.08 * intensity)

    elif fault == "looseness":
        value *= (1 + 0.20 * intensity)

    return value


# ============================================================
# LOAD BASELINE XLSX
# ============================================================

def load_state(state):

    if state in CACHE:
        return CACHE[state]

    filename = STATE_FILES.get(state)

    if filename is None:
        raise RuntimeError(f"No baseline XLSX configured for state: {state}")

    path = BASE_PATH / filename

    if not path.exists():
        raise RuntimeError(f"Missing baseline XLSX: {path}")

    df = pd.read_excel(path)

    rows = []

    last_amp = [0.0, 0.0, 0.0]
    last_rpm = 0.0
    last_temp = 0.0

    for _, row in df.iterrows():

        if pd.notna(row["amp"]):
            last_amp = parse_amp(row["amp"])

        if pd.notna(row["rpm"]):
            last_rpm = float(row["rpm"])

        if pd.notna(row["tempC"]):
            last_temp = float(row["tempC"])

        rows.append({
            "rpm": last_rpm,
            "tempC": last_temp,
            "amp": last_amp,
            "vibX": parse_vibration(row["vibX"]),
            "vibY": parse_vibration(row["vibY"]),
            "vibZ": parse_vibration(row["vibZ"]),
        })

    CACHE[state] = rows

    print(f"[SIM] Loaded baseline state: {state} rows={len(rows)}")

    return rows


def get_random_row(state):

    rows = load_state(state)

    return random.choice(rows)


# ============================================================
# RPM
# ============================================================

def get_rpm_value(
    rpm_mode,
    load="idle",
    wear=0.0,
    fault=None,
    fault_intensity=0.0
):

    state = get_state_key(rpm_mode, load)

    row = get_random_row(state)

    rpm = row["rpm"]

    rpm = random_variation(rpm, 0.03)

    rpm *= (1.0 - wear * 0.05)

    rpm = apply_fault_scalar(
        rpm,
        fault,
        fault_intensity
    )

    return round(rpm, 2)


# ============================================================
# TEMPERATURE
# ============================================================

def temperature(
    rpm_mode,
    wear,
    load,
    fault=None,
    fault_intensity=0.0
):

    state = get_state_key(rpm_mode, load)

    row = get_random_row(state)

    temp = row["tempC"]

    temp = random_variation(temp, 0.02)

    temp += wear * 10

    temp = apply_fault_scalar(
        temp,
        fault,
        fault_intensity
    )

    return round(temp, 2)


# ============================================================
# CURRENT
# ============================================================

def current(
    rpm_mode,
    wear,
    load,
    fault=None,
    fault_intensity=0.0
):

    state = get_state_key(rpm_mode, load)

    row = get_random_row(state)

    currents = row["amp"]

    out = []

    for value in currents:

        value = float(value)

        value = random_variation(value, 0.05)

        value += wear * 0.2

        value = apply_fault_scalar(
            value,
            fault,
            fault_intensity
        )

        out.append(round(value, 2))

    # imbalance extra distortion
    if fault == "imbalance":
        out[1] += fault_intensity * 0.5

    return out


# ============================================================
# VIBRATION
# ============================================================

def vibration_sequence(
    rpm_mode,
    wear,
    load,
    axis="vibX",
    fault=None,
    fault_intensity=0.0
):

    state = get_state_key(rpm_mode, load)

    rows = load_state(state)

    start = random.randint(0, len(rows) - 8)

    chunks = []

    for i in range(8):

        vib = rows[start + i][axis]

        signal = np.array(vib["d"], dtype=float)

        noise = np.random.normal(
            0,
            10 + wear * 30,
            size=len(signal)
        )

        signal += noise

        signal *= (1.0 + wear * 0.25)

        t = np.linspace(0, 1, len(signal))

        if fault == "imbalance":

            signal += (
                np.sin(2 * np.pi * 8 * t)
                * 120
                * fault_intensity
            )

        elif fault == "misalignment":

            signal += (
                np.sin(2 * np.pi * 16 * t)
                * 180
                * fault_intensity
            )

        elif fault == "bearing":

            spikes = np.random.normal(
                0,
                250 * fault_intensity,
                size=len(signal)
            )

            signal += spikes

        elif fault == "looseness":

            lowfreq = np.sin(2 * np.pi * 3 * t)

            signal += lowfreq * 220 * fault_intensity

        chunks.append({
            "s": int(vib["s"]),
            "c": int(vib["c"]),
            "d": signal.astype(int).tolist()
        })

    return chunks