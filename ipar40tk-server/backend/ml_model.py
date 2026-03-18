from sklearn.ensemble import IsolationForest
import numpy as np

WINDOW = 50

model = IsolationForest(contamination=0.02)

buffer = []

models = {
    "scalar": {
        "model": IsolationForest(contamination=0.02),
        "buffer": []
    },
    "current": {
        "model": IsolationForest(contamination=0.02),
        "buffer": []
    },
    "vibration": {
        "model": IsolationForest(contamination=0.02),
        "buffer": []
    }
}

def predict(feature_vector, model_key):
    entry = models[model_key]

    fv = np.asarray(feature_vector, dtype=float).flatten()

    if entry["buffer"]:
        expected_dim = entry["buffer"][0].shape[0]
        if fv.shape[0] != expected_dim:
            print(f"[ERROR] Shape mismatch in {model_key}: got {fv.shape}, expected {expected_dim}")
            return None

    entry["buffer"].append(fv)

    if len(entry["buffer"]) < WINDOW:
        return None

    X = np.vstack(entry["buffer"][-WINDOW:])

    if len(entry["buffer"]) == WINDOW:
        entry["model"].fit(X)

    return float(entry["model"].decision_function(fv.reshape(1, -1))[0])