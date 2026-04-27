from sklearn.ensemble import IsolationForest
import numpy as np
from sklearn.preprocessing import StandardScaler
import pandas as pd
import os
from collections import deque
import numpy as np


FEATURE_COLUMNS = [
    "rms",
    "fft_peak",
    "energy",
    "current_mean",
    "imbalance",
    "temperature",
    "rpm"
]

def load_baselines(folder):
    for state in STATES:
        path = os.path.join(folder, f"{state}.xlsx")

        if not os.path.exists(path):
            raise RuntimeError(f"Missing baseline file for state: {state}")

        df = pd.read_excel(path)

        # csak feature oszlopok
        X = df[FEATURE_COLUMNS].values

        entry = models[state]

        entry["scaler"].fit(X)
        X_scaled = entry["scaler"].transform(X)

        entry["model"].fit(X_scaled)

        threshold = compute_threshold(entry["model"], entry["scaler"], X)
        entry["threshold"] = threshold

        entry["fitted"] = True
        print(f"[INFO] Loaded states: {[s for s in models if models[s]['fitted']]}")
        print(f"[INFO] Loaded baseline for {state}, samples: {len(X)}")


models = {}

STATES = [
    "low_idle", "low_medium", "low_high",
    "mid_idle", "mid_medium", "mid_high",
    "high_idle", "high_medium", "high_high"
]



def create_entry():
    return {
        "model": IsolationForest(contamination=0.02),
        "scaler": StandardScaler(),
        "fitted": False,
        "score_history": []
    }

for state in STATES:
    models[state] = create_entry()


def get_operating_state(rpm: float, current_mean: float) -> str:
    if rpm < 800:
        speed = "low"
    elif rpm < 1400:
        speed = "mid"
    else:
        speed = "high"

    # Terhelés KALIBRÁLÁST igényel!!!
    if current_mean < 2.0:
        load = "idle"
    elif current_mean < 5.0:
        load = "medium"
    else:
        load = "high"

    return f"{speed}_{load}"

def compute_threshold(model, scaler, X):
    X_scaled = scaler.transform(X)
    scores = model.decision_function(X_scaled)

    # pl. 5% legrosszabb még normál
    threshold = np.percentile(scores, 5)

    return threshold

# Predicts anomaly score based on feature vector and RPM state
SMOOTHING = 10

def predict(feature_vector, rpm, current_mean):
    if rpm is None or current_mean is None:
        return None

    state = get_operating_state(rpm, current_mean)
    entry = models.get(state)

    if entry is None or not entry["fitted"]:
        return None

    fv = np.asarray(feature_vector, dtype=float).reshape(1, -1)

    fv_scaled = entry["scaler"].transform(fv)
    raw_score = entry["model"].decision_function(fv_scaled)[0]

    # smoothing
    entry["score_history"].append(raw_score)
    if len(entry["score_history"]) > SMOOTHING:
        entry["score_history"].pop(0)

    score = float(np.mean(entry["score_history"]))

    threshold = entry["threshold"]

    is_anomaly = score < threshold
    severity = threshold - score if is_anomaly else 0

    #  RUL
    rul = update_rul(state, score)

    return {
        "score": score,
        "state": state,
        "is_anomaly": is_anomaly,
        "severity": severity,
        "rul": rul
    }

RUL_WINDOW = 100

def create_rul_entry():
    return {
        "history": deque(maxlen=RUL_WINDOW)
    }

rul_models = {state: create_rul_entry() for state in STATES}

def update_rul(state, score):
    entry = rul_models[state]
    entry["history"].append(score)

    if len(entry["history"]) < 20:
        return None

    y = np.array(entry["history"])
    x = np.arange(len(y))

    # lineáris trend
    slope, intercept = np.polyfit(x, y, 1)

    # mikor éri el a kritikus szintet?
    CRITICAL = models[state]["threshold"]

    if slope >= 0:
        return None  # nem romlik

    # y = slope*x + intercept → x = (crit - intercept)/slope
    rul = (CRITICAL - intercept) / slope

    return max(0, rul)