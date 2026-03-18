import random
import numpy as np

def temperature():

    return round(random.uniform(15, 77), 2)

def rpm():

    return random.randint(56, 2900)

def current():

    return [round(random.uniform(1, 16), 2) for _ in range(3)]

def vibration():

    base = np.sin(np.linspace(0, 100, 128))

    noise = np.random.normal(0, 0.2, 128)

    vib = base + noise

    return vib.tolist()