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
    "vibration": {
        "model": IsolationForest(contamination=0.02),
        "buffer": []
    }
}


def predict(feature_vector, model_key):
    entry = models[model_key]

    fv = np.asarray(feature_vector).reshape(1, -1)

    entry["buffer"].append(fv[0])

    if len(entry["buffer"]) < WINDOW:
        return None

    X = np.vstack(entry["buffer"][-WINDOW:])

    entry["model"].fit(X)

    return float(entry["model"].decision_function(fv)[0])
