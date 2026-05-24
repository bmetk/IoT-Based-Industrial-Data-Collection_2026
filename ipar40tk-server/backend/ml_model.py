from sklearn.ensemble import IsolationForest, RandomForestClassifier
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import pandas as pd
import os
from collections import deque, Counter
import numpy as np

state_clf = None

STATE_HISTORY_SIZE = 10

state_history = deque(maxlen=STATE_HISTORY_SIZE)

current_stable_state = None

transition_counter = 0

TRANSITION_REQUIRED = 5

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
        print(df[FEATURE_COLUMNS].dtypes)
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
        df = df.iloc[5:].reset_index(drop=True)

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

    print("\n=== FEATURE IMPORTANCE ===")

    for feature, importance in sorted(zip(FEATURE_COLUMNS, clf.feature_importances_), key=lambda x: x[1], reverse=True):
        print(f"{feature}: {importance:.4f}")
    pred = clf.predict(X)

    print(classification_report(y, pred))
    sample = df[df["state"]=="mid-rpm_idle_filled"]

    print(sample[FEATURE_COLUMNS].mean())
    return clf

def smooth_state(predicted_state):

    global current_stable_state
    global transition_counter

    state_history.append(predicted_state)

    # Majority vote
    majority_state = Counter(state_history).most_common(1)[0][0]

    # First initialization
    if current_stable_state is None:
        current_stable_state = majority_state
        return current_stable_state

    # Same state -> stable
    if majority_state == current_stable_state:
        transition_counter = 0
        return current_stable_state

    # Different state candidate
    transition_counter += 1

    # Accept transition only after repeated confirmations
    if transition_counter >= TRANSITION_REQUIRED:

        print(f"[STATE CHANGE] {current_stable_state} -> {majority_state}")

        current_stable_state = majority_state
        transition_counter = 0

    return current_stable_state

# Predicts anomaly score based on feature vector and RPM state
SMOOTHING = 10

def predict(feature_vector):
    global state_clf

    if state_clf is None:
        print("[ERROR] state_clf not initialized")
        return None
    
    fv = np.asarray(feature_vector, dtype=float).reshape(1, -1)

    # CLASSIFIER PREDICTION
    probs = state_clf.predict_proba(fv)[0]
    for cls, prob in zip(state_clf.classes_, probs):
        print(cls, round(prob, 3))
    classes = state_clf.classes_
    best_idx = np.argmax(probs)
    predicted_state = classes[best_idx]
    confidence = probs[best_idx]

    print(f"[CLASSIFIER] state={predicted_state} confidence={confidence:.3f}")

    # LOW CONFIDENCE HANDLING
    CONFIDENCE_THRESHOLD = 0.60
    if confidence < CONFIDENCE_THRESHOLD:

        print(f"[CLASSIFIER] LOW CONFIDENCE ({confidence:.3f})")

        # keep previous stable state if exists
        if current_stable_state is not None:
            predicted_state = current_stable_state

    # STATE SMOOTHING
    state = smooth_state(predicted_state)

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
    rul, health = update_rul(state, score)

    return {
        "score": score,
        "state": state,
        "is_anomaly": is_anomaly,
        "severity": severity,
        "rul": rul,
        "health": round(health * 100, 1),
    }

# ============================================================
# RUL MODEL
# ============================================================

MAX_RUL_HOURS = 3500

RUL_WINDOW = 100

def create_rul_entry():
    return {
        "history": deque(maxlen=RUL_WINDOW),

        # accumulated degradation
        "wear": 0.0,

        # current estimated health
        "health": 1.0,

        # smoothed degradation rate
        "degradation_rate": 0.0
    }

rul_models = { state: create_rul_entry() for state in STATES}

def normalize_score(state, score):

    threshold = models[state]["threshold"]

    # baseline healthy score reference
    healthy_ref = 0.10

    # normalize into 0..1
    normalized = (score - threshold) / (healthy_ref - threshold)

    return np.clip(normalized, 0.0, 1.0)


def update_rul(state, score):

    entry = rul_models[state]

    entry["history"].append(score)

    if len(entry["history"]) < 10:
        return MAX_RUL_HOURS, entry["health"]

    # --------------------------------------------------------
    # HEALTH INDEX
    # --------------------------------------------------------

    health = normalize_score(state, score)

    # smooth health
    prev_health = entry["health"]

    smoothed_health = (
        0.9 * prev_health +
        0.1 * health
    )

    entry["health"] = smoothed_health

    # --------------------------------------------------------
    # DEGRADATION
    # --------------------------------------------------------

    degradation = max(0.0, prev_health - smoothed_health)

    # exponential smoothing
    entry["degradation_rate"] = (
        0.95 * entry["degradation_rate"] +
        0.05 * degradation
    )

    deg_rate = entry["degradation_rate"]

    # accumulate wear
    entry["wear"] += deg_rate

    # --------------------------------------------------------
    # RUL ESTIMATION
    # --------------------------------------------------------

    estimated_used_life = entry["wear"] * MAX_RUL_HOURS

    rul = MAX_RUL_HOURS - estimated_used_life

    # anomaly accelerates degradation
    if score < models[state]["threshold"]:
        rul *= 0.97

    rul = np.clip(rul, 0, MAX_RUL_HOURS)

    return round(float(rul), 1), round(float(entry["health"]), 3)