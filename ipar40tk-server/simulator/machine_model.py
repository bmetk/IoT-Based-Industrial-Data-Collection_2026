import json
import numpy as np

# Simulate RPM values based on machine mode
def get_rpm_value(mode):
    if mode == "low":
        return np.random.normal(500, 10)
    elif mode == "medium":
        return np.random.normal(1200, 20)
    else:
        return np.random.normal(2000, 30)

# Simulate temperature values based on RPM and wear state
def temperature(rpm, wear, load):
    base = 20 + 0.01 * rpm

    if load == "high":
        base += 15
    elif load == "medium":
        base += 7

    wear_effect = (wear ** 2) * 25

    noise = np.random.normal(0, 0.5)

    return base + wear_effect + noise

# Simulate 3-phase current values based on RPM and wear state
def current(rpm, wear, load, fault=None):
    base = 1.0 + 0.0025 * rpm

    if load == "idle":
        load_factor = 0.5
    elif load == "medium":
        load_factor = 1.0
    else:
        load_factor = 1.8

    base *= load_factor

    ia = base + np.random.normal(0, 0.2)
    ib = base + np.random.normal(0, 0.2)
    ic = base + np.random.normal(0, 0.2)

    # imbalance wear miatt
    if fault == "imbalance":
        ib += wear * 3

    if fault == "looseness":
        ia += np.random.normal(0, wear)
        ib += np.random.normal(0, wear)
        ic += np.random.normal(0, wear)

    return [round(ia, 2), round(ib, 2), round(ic, 2)]

# Simulate vibration signal based on RPM and wear state
def vibration(rpm, wear, load, fault=None, n=1024):
    t = np.linspace(0, 1, n)
    freq = (rpm / 60) * np.random.normal(1.0, 0.01)
    fault_intensity = wear if fault else 0
    base = 1.5 * np.sin(2 * np.pi * freq * t)

    noise = np.random.normal(0, 0.05 + wear * 0.3, n)

    signal = base + noise

    if fault == "imbalance":
        signal += 2.0 * np.sin(2 * np.pi * freq * t)

    elif fault == "misalignment":
        signal += 1.5 * np.sin(2 * np.pi * 2 * freq * t)

    elif fault == "bearing":
        signal += fault_intensity * 1.2 * np.sin(2 * np.pi * 3.5 * freq * t)

    elif fault == "looseness":
        signal += 0.8 * np.sin(2 * np.pi * 0.5 * freq * t)

    if load == "high":
        signal *= 1.5
    elif load == "medium":
        signal *= 1.2

    # wear általános hatás
    signal += wear * 0.5 * np.sin(2 * np.pi * freq * t)

    return signal.tolist()