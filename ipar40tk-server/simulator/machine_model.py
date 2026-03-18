import random
import numpy as np

def temperature():
    if random.random() < 0.03:  # 3% hiba
        return random.uniform(80, 120)  # túlmelegedés
    return round(random.uniform(15, 77), 2)

def rpm():
    if random.random() < 0.03:  # 3% hiba
        return random.randint(2900, 5000) # túl magas fordulatszám
    return random.randint(56, 2900)

def current():
    if random.random() < 0.03:  # 3% hiba
        return [round(random.uniform(16, 30), 2) for _ in range(3)]  # túl magas áram
    return [round(random.uniform(1, 16), 2) for _ in range(3)]

def vibration():

    base = np.sin(np.linspace(0, 100, 128))

    noise = np.random.normal(0, 0.2, 128)

    vib = base + noise
    if random.random() < 0.03:  # 3% hiba
        vib += np.random.normal(0, 1.0, 128)  # nagy zaj
    return vib.tolist()