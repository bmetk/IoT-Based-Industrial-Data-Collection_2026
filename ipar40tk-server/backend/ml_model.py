from sklearn.ensemble import IsolationForest
import numpy as np

WINDOW = 50

model = IsolationForest(contamination=0.02)

buffer = []


def predict(feature_vector):

    buffer.append(feature_vector)

    if len(buffer) < WINDOW:
        return None

    X = np.array(buffer[-WINDOW:])

    model.fit(X)

    score = model.decision_function([feature_vector])[0]

    return float(score)