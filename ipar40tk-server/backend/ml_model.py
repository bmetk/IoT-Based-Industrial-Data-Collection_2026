from sklearn.ensemble import IsolationForest
import numpy as np
from sklearn.preprocessing import StandardScaler

# Anomaly detection models
WINDOW = 200
RETRAIN_INTERVAL = 200
WARMUP = 20
SMOOTHING = 10

def create_model():
    return IsolationForest(contamination=0.02)

def create_entry():
    return {
        "model": create_model(),
        "buffer": [],
        "last_state": None,
        "counter": 0,
        "warmup": 0,
        "score_history": [],
        "fitted": False,
        "scaler": StandardScaler(),
        "baseline_buffer": []
    }

models = {
    "low": create_entry(),
    "mid": create_entry(),
    "high": create_entry()
}

# RPM based state
def get_rpm_state(rpm: float) -> str:
    if rpm < 800:
        return "low"
    elif rpm < 1800:
        return "mid"
    else:
        return "high"

# Predicts anomaly score based on feature vector and RPM state
def predict(feature_vector, rpm):
    if rpm is None:
        return None

    state = get_rpm_state(rpm)
    entry = models[state]

    fv = np.asarray(feature_vector, dtype=float).flatten()

    # Handle state changes and warmup period
    if entry["last_state"] is not None and entry["last_state"] != state:
        print(f"[INFO] State change: {entry['last_state']} -> {state}")
        entry["buffer"] = []
        entry["warmup"] = 0
        entry["score_history"] = []

    entry["last_state"] = state

    score = None
    # If the score improves and is no longer highly anomalous, we can unfreeze the model to allow it to learn from new data points again
    if entry.get("freeze"):
        return float(score) if score is not None else None
    
    # Only score if model is fitted to avoid unreliable scores during warmup period
    if entry["fitted"]:
        fv_scaled = entry["scaler"].transform(fv.reshape(1, -1))
        score = entry["model"].decision_function(fv_scaled)[0]

    # If the score is not highly anomalous, we can add the feature vector to a baseline buffer which the model can learn from to adapt to normal data patterns over time
    if score is None or score > -0.05:
        entry["baseline_buffer"].append(fv)

    # If the score is highly anomalous, we can choose to freeze the model to prevent it from learning from anomalous data points which could degrade its performance
    if score is not None and score < -0.15:
        entry["freeze"] = True

    # Keep buffer size manageable to limit memory usage and ensure model trains on recent data patterns
    if len(entry["buffer"]) > WINDOW:
        entry["buffer"] = entry["buffer"][-WINDOW:]
    
    # Warmup period to allow model to learn initial patterns before scoring
    entry["warmup"] += 1
    if entry["warmup"] < WARMUP:
        return None

    # Use baseline buffer for training to adapt to new normal patterns while avoiding learning from anomalies
    X = np.vstack(entry["baseline_buffer"][-500:])

    # Retrain the model periodically to adapt to new data patterns while avoiding overfitting
    entry["counter"] += 1

    if entry["counter"] % RETRAIN_INTERVAL == 0:
        if score > -0.1:
            entry["scaler"].fit(X)
            X_scaled = entry["scaler"].transform(X)

            entry["model"].fit(X_scaled)

    # Score the current feature vector if the model is fitted
    if not entry["fitted"]:
        entry["scaler"].fit(X)
        X_scaled = entry["scaler"].transform(X)

        entry["model"].fit(X_scaled)
        entry["fitted"] = True
        return None

    fv_scaled = entry["scaler"].transform(fv.reshape(1, -1))

    score = entry["model"].decision_function(fv_scaled)[0]

    # Smooth the score using a rolling average to reduce noise and false positives
    entry["score_history"].append(score)

    if len(entry["score_history"]) > SMOOTHING:
        entry["score_history"].pop(0)

    smoothed_score = np.mean(entry["score_history"])

    return float(smoothed_score)