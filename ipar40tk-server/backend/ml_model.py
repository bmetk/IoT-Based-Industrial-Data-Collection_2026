from sklearn.ensemble import IsolationForest, RandomForestClassifier
import numpy as np
from sklearn.preprocessing import StandardScaler
import pandas as pd
import os
from collections import deque
import numpy as np

state_clf = None
def set_state_clf(clf):
    global state_clf
    state_clf = clf

FEATURE_COLUMNS = [
    "current_imbalance",
    "current_mean",
    "rpm",
    "tempC",
    "vibX_fft_peak",
    "vibX_rms",
    "vibY_fft_peak",
    "vibY_rms",
    "vibZ_fft_peak",
    "vibZ_rms"
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
    "low-rpm_idle_filled", "low-rpm_low-stress_filled", "low-rpm_high-stress_filled",
    "mid-rpm_idle_filled", "mid-rpm_low-stress_filled", "mid-rpm_high-stress_filled",
    "high-rpm_idle_filled", "high-rpm_low-stress_filled", "high-rpm_high-stress_filled"
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
    if rpm < 550:
        speed = "low"
    elif rpm < 800:
        speed = "mid"
    else:
        speed = "high"

    if current_mean < 3.5:
        load = "idle"
    elif current_mean < 5.0:
        load = "low-stress"
    else:
        load = "high-stress"

    return f"{speed}-rpm_{load}_filled"

def compute_threshold(model, scaler, X):
    X_scaled = scaler.transform(X)
    scores = model.decision_function(X_scaled)

    # pl. 5% legrosszabb még normál
    threshold = np.percentile(scores, 5)

    return threshold

def load_training_data(folder):
    dfs = []

    for state in STATES:
        path = os.path.join(folder, f"{state}.xlsx")
        df = pd.read_excel(path)

        df["state"] = state
        dfs.append(df)

    full_df = pd.concat(dfs, ignore_index=True)
    return full_df

def train_state_classifier(df):
    X = df[FEATURE_COLUMNS].values
    y = df["state"].values

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )

    clf.fit(X, y)
    return clf

# Predicts anomaly score based on feature vector and RPM state
SMOOTHING = 10

def predict(feature_vector):
    global state_clf

    if state_clf is None:
        print("[ERROR] state_clf not initialized")
        return None
    
    fv = np.asarray(feature_vector, dtype=float).reshape(1, -1)
    state = state_clf.predict(fv)[0]

    entry = models.get(state)
    print("MODEL EXISTS:", entry is not None)
    if entry is None or not entry["fitted"]:
        return None

    fv_scaled = entry["scaler"].transform(fv)
    raw_score = entry["model"].decision_function(fv_scaled)[0]

    print(f"[PREDICT] Raw score for {state}: {raw_score}")

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

    # exponenciális smoothing trend
    trend = np.mean(np.diff(y[-10:]))

    if trend >= 0:
        return None

    CRITICAL = models[state]["threshold"]

    return max(0, (CRITICAL - y[-1]) / trend)