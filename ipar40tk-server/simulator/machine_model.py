import numpy as np
import random

# ============================================================
# BASELINE STATES
# ============================================================

BASELINES = {

    "low-rpm_idle_filled": {

        "rpm": [
            486.69, 477.27, 480.55, 473.68, 485.22,
            515.93, 462.12, 514.37, 476.19, 466.87
        ],

        "temp": [
            26.17, 26.21, 26.23, 26.21, 26.21,
            26.21, 26.21, 26.29, 26.31, 26.35
        ],

        "current": [
            [3.33, 3.63, 3.63],
            [3.31, 3.58, 3.60],
            [3.27, 3.68, 3.47],
            [3.34, 3.62, 3.57],
            [3.32, 3.59, 3.62],
            [3.26, 3.72, 3.51],
            [3.30, 3.66, 3.71],
            [3.32, 3.62, 3.70],
            [3.25, 3.62, 3.53],
            [3.31, 3.65, 3.46]
        ],

        # ----------------------------------------------------
        # FULL RAW VIBRATION SIGNALS
        # ----------------------------------------------------

        "vibX": [
            481,-164,33,-256,-168,185,-106,454,-481,31,-174,-20,357,142,-413,-676,-422,-252,179,79,-181,-235,-96,8,-205,-110,-201,26,-203,-117,-58,-74,-180,-118,-2,-186,-179,-71,-43,-257,-126,-114,-39,-329,-33,-23,-80,-215,-168,-146,3,-113,-56,-293,64,-169,-108,-11,-408,-317,-192,71,-152,-46,-96,-351,-70,-174,-168,73,401,-111,-238,-339,429,-245,-223,517,-167,-538,-602,-452,-17,237,-93,-123,-243,-95,-137,-34,-82,-99,-68,-161,-58,-130,-123,-152,-20,-140,-165,-209,-15,-75,-216,-152,-11,29,-330,-51,-166,124,-350,13,-124,-9,-196,-241,29,-148,-165,-181,149,-396,-447,-131,-33,61
        ] * 8,

        "vibY": [
            4940,4781,4993,4874,4830,4939,5035,4766,5024,4958,4817,4881,4929,4854,4890,4847,4938,4862,4839,4820,4982,4836,4932,4885,4869,5006,4927,4787,4948,4991,4838,4892,5024,4739,4914,4911,5013,4865,4656,4945,5100,4667,4930,5021,4806,4811,4941,4952,4831,4933,5111,4878,4663,4963,4932,4922,4832,5036,4699,4970,4875,4859,4932,4929,4886,4824,5008,4921,4883,4935,4959,4871,4897,5007,4786,4891,4935,4839,4841,4959,4787,4837,5037,4806,4805,5032,4903,4883,4932,4952,4865,4861,4874,4939,4830,4917,4810,4923,4804,4948,4886,4933,4862,4863,4932,4857,4958,4972,4843,4978,4746,4971,5076,4741,4556,5116,5130,4671,4757,5018,4872,5019,4747,4932,4902,4863,4930,5024
        ] * 8,

        "vibZ": [
            4266,4289,4462,4167,4398,4344,4232,4295,4499,3958,4953,4308,4176,4338,4327,4226,4472,4351,4331,4382,4303,4250,4295,3434,4893,4522,3957,4426,4241,4635,3949,4819,4293,4527,4177,4352,4222,4469,4290,4292,4295,4375,4304,4435,4104,4347,4392,4226,4377,4322,4368,4396,4401,4234,4302,4368,4344,4252,4273,4534,4226,4219,4256,4307,4311,4225,4321,4232,4321,4250,4430,4374,4303,4310,4580,4203,4456,4541,4070,4076,4510,4481,4159,4419,4309,4453,4249,4129,3810,4158,4525,4831,4000,4398,4238,4224,4728,4600,4098,4432,4119,4478,4295,4359,4279,4217,4459,4237,4361,4283,4337,4248,4331,4384,4310,4288,4441,4232,4282,4460,4228,4283,4353,4475,4229,4198,4396,4254
        ] * 8
    }
}

# ============================================================
# HELPERS
# ============================================================

def get_state_key(rpm_mode, load):

    load_map = {
        "idle": "idle",
        "low": "low-stress",
        "medium": "low-stress",
        "high": "high-stress"
    }

    speed_map = {
        "low": "low-rpm",
        "medium": "mid-rpm",
        "mid": "mid-rpm",
        "high": "high-rpm"
    }

    speed = speed_map.get(rpm_mode, "low-rpm")
    load_state = load_map.get(load, "idle")

    return f"{speed}_{load_state}_filled"


def random_variation(value, pct=0.08):
    delta = value * pct
    return value + np.random.uniform(-delta, delta)


def apply_fault_scalar(value, fault, intensity):

    if not fault:
        return value

    if fault == "bearing":
        value *= (1 + 0.10 * intensity)

    elif fault == "imbalance":
        value *= (1 + 0.15 * intensity)

    elif fault == "misalignment":
        value *= (1 + 0.08 * intensity)

    elif fault == "looseness":
        value *= (1 + 0.20 * intensity)

    return value


# ============================================================
# RPM
# ============================================================

def get_rpm_value(rpm_mode, load="idle", wear=0.0, fault=None, fault_intensity=0.0):

    state = get_state_key(rpm_mode, load)

    baseline = BASELINES[state]

    rpm = random.choice(baseline["rpm"])

    rpm = random_variation(rpm, 0.05)

    rpm = apply_fault_scalar(rpm, fault, fault_intensity)

    rpm *= (1.0 - wear * 0.05)

    return round(rpm, 2)


# ============================================================
# TEMPERATURE
# ============================================================

def temperature(rpm_mode, wear, load, fault=None, fault_intensity=0.0):

    state = get_state_key(rpm_mode, load)

    baseline = BASELINES[state]

    temp = random.choice(baseline["temp"])

    temp = random_variation(temp, 0.03)

    temp += wear * 10

    temp = apply_fault_scalar(temp, fault, fault_intensity)

    return round(temp, 2)


# ============================================================
# CURRENT
# ============================================================

def current(rpm_mode, wear, load, fault=None, fault_intensity=0.0):

    state = get_state_key(rpm_mode, load)

    baseline = BASELINES[state]

    ia, ib, ic = random.choice(baseline["current"])

    currents = [ia, ib, ic]

    varied = []

    for c in currents:

        value = random_variation(c, 0.08)

        value += wear * 0.3

        value = apply_fault_scalar(value, fault, fault_intensity)

        varied.append(round(value, 2))

    # imbalance extra distortion
    if fault == "imbalance":
        varied[1] += fault_intensity * 0.8

    return varied


# ============================================================
# VIBRATION
# ============================================================

def vibration(
    rpm_mode,
    wear,
    load,
    axis="vibX",
    fault=None,
    fault_intensity=0.0,
    n=1024
):

    state = get_state_key(rpm_mode, load)

    baseline = BASELINES[state]

    signal = np.array(baseline[axis][:n], dtype=float)

    # random noise
    noise = np.random.normal(
        0,
        20 + wear * 50,
        size=len(signal)
    )

    signal = signal + noise

    # wear amplification
    signal *= (1.0 + wear * 0.3)

    # --------------------------------------------------------
    # FAULT MODELS
    # --------------------------------------------------------

    t = np.linspace(0, 1, len(signal))

    if fault == "imbalance":

        signal += (
            np.sin(2 * np.pi * 8 * t)
            * 200
            * fault_intensity
        )

    elif fault == "misalignment":

        signal += (
            np.sin(2 * np.pi * 16 * t)
            * 250
            * fault_intensity
        )

    elif fault == "bearing":

        spikes = np.random.normal(
            0,
            300 * fault_intensity,
            size=len(signal)
        )

        signal += spikes

    elif fault == "looseness":

        lowfreq = np.sin(2 * np.pi * 3 * t)

        signal += lowfreq * 400 * fault_intensity

    #signal = np.clip(signal, -32768, 32767)

    return signal.astype(int).tolist()