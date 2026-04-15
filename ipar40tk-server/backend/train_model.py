import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

df = pd.read_csv("training_data.csv")

features = ["rms", "fft_peak", "energy", "current", "imbalance", "temp", "rpm"]

X = df[features].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = IsolationForest(contamination=0.02)
model.fit(X_scaled)

joblib.dump(model, "model.pkl")
joblib.dump(scaler, "scaler.pkl")