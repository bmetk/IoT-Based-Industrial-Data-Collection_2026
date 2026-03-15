import random
import numpy as np

def temperature():

    return round(random.uniform(25, 65), 2)

def rpm():

    return random.randint(500, 2200)

def current():

    return round(random.uniform(1, 6), 2)

def vibration():

    base = np.sin(np.linspace(0, 20, 128))

    noise = np.random.normal(0, 0.2, 128)

    vib = base + noise

    return vib.tolist()