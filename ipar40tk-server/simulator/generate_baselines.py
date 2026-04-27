import pandas as pd
import numpy as np
import os
import machine_model as model

STATES = [
    "low_idle", "low_medium", "low_high",
    "mid_idle", "mid_medium", "mid_high",
    "high_idle", "high_medium", "high_high"
]

SAMPLES_PER_STATE = 2000

OUTPUT_DIR = "baselines"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_state(state):
    speed, load = state.split("_")
    return speed, load


def generate_sample(speed, load):
    rpm = model.get_rpm_value(speed)

    wear = np.random.uniform(0.0, 0.05)

    temp = model.temperature(rpm, wear, load)
    currents = model.current(rpm, wear, load, fault=None)

    current_mean = np.mean(currents)
    imbalance = max(currents) - min(currents)

    vib = np.array(model.vibration(rpm, wear, load, fault=None))

    rms = np.sqrt(np.mean(vib ** 2))
    fft_peak = np.max(np.abs(np.fft.rfft(vib)))
    energy = np.sum(np.abs(np.fft.rfft(vib)) ** 2)

    return {
        "rms": rms,
        "fft_peak": fft_peak,
        "energy": energy,
        "current_mean": current_mean,
        "imbalance": imbalance,
        "temperature": temp,
        "rpm": rpm
    }


for state in STATES:
    speed, load = parse_state(state)

    print(f"[INFO] Generating {state}...")

    data = [generate_sample(speed, load) for _ in range(SAMPLES_PER_STATE)]

    df = pd.DataFrame(data)

    path = os.path.join(OUTPUT_DIR, f"{state}.xlsx")
    df.to_excel(path, index=False)

print("[DONE] Baselines generated.")
