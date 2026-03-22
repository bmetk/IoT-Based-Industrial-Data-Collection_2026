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
def temperature(rpm, wear):
    base = 20 + 0.015 * rpm
    noise = np.random.normal(0, 1)

    wear_effect = (wear ** 2) * 30

    return base + wear_effect + noise

# Simulate 3-phase current values based on RPM and wear state
def current(rpm, wear):
    base = 2 + 0.005 * rpm

    ia = base + np.random.normal(0, 0.3)
    ib = base + np.random.normal(0, 0.3)
    ic = base + np.random.normal(0, 0.3)

    ib += wear * 3

    return [round(ia, 2), round(ib, 2), round(ic, 2)]

# Simulate vibration signal based on RPM and wear state
def vibration(rpm, wear):
    t = np.linspace(0, 1, 128)

    # Define base frequency from RPM
    freq = rpm / 60

    base = np.sin(2 * np.pi * freq * t)

    noise = np.random.normal(0, 0.2 + (wear ** 1.5) * 0.7, len(t))

    signal = base + noise

    fault_freq = freq * 2.5
    signal += wear * np.sin(2 * np.pi * fault_freq * t)

    return signal.tolist()