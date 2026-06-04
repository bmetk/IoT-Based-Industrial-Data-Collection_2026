# Feature engineering module for the IPAR40TK server backend
# Contains functions for processing raw telemetry data, extracting features, and preparing input for the ML model

import numpy as np
import numpy.typing as npt
from scipy import signal
from scipy.fft import rfft
from influx_client import *
from ml_model import predict
import json
import time

SAMPLING_FREQ = 1000

Array = npt.NDArray[np.float64]

chunk_buffers = {}
chunk_meta = {}

# Global machine state cache
machine_state = {}
machine_timestamps = {}

# State management functions to keep track of latest values and timestamps for each machine and feature
def update_state(machine, key, value):

    if machine not in machine_state:
        machine_state[machine] = {}

    if machine not in machine_timestamps:
        machine_timestamps[machine] = {}

    machine_state[machine][key] = value

    machine_timestamps[machine][key] = time.time()


def get_state(machine, key):
    return machine_state.get(machine, {}).get(key)

# RMS calculation
def rms(vib: Array) -> float:
    vib = np.asarray(vib, dtype=float)
    return np.sqrt(np.mean(vib ** 2))

# FFT peak calculation function that applies a Hamming window and returns the maximum amplitude in the spectrum
def fft_peak(vib: Array) -> float:
    vib = np.asarray(vib, dtype=float)
    windowed = vib * signal.windows.hamming(vib.size)
    spectrum = np.abs(rfft(windowed))
    return float(np.max(spectrum))

# FFT calculation function that applies a Hamming window and returns the amplitude spectrum
def calculate_fft(vib: Array) -> np.ndarray:
    windowed = vib * signal.windows.hamming(vib.size)

    spectrum = np.abs(rfft(windowed))
    spectrum = 2.0 / vib.size * spectrum

    return spectrum

# Power Spectral Density calculation function that applies a Hamming window and returns the frequencies and corresponding PSD values
def get_psd(vib: Array) -> tuple[list[float], list[float]]:
    f, psd = signal.periodogram(vib, fs=SAMPLING_FREQ, window="hamming")
    return f.tolist(), psd.tolist()

# PSD peak calculation function that applies a Hamming window and returns the maximum PSD value
def psd_peak(vib: Array) -> float:
    f, psd = signal.periodogram(vib, fs=SAMPLING_FREQ, window="hamming")
    return float(np.max(psd))

def spectral_energy(vib):
    spectrum = np.abs(rfft(vib))
    return float(np.sum(spectrum ** 2))

# Function to check if all required features for a machine are synchronized within a certain time delta
def features_are_synchronized(machine, max_delta=2.0):

    if machine not in machine_timestamps:
        return False

    timestamps = machine_timestamps[machine]

    required = [
        "current_mean",
        "current_imbalance",
        "rpm",
        "temperature",
        "vibX_rms",
        "vibY_rms",
        "vibZ_rms"
    ]

    values = []

    for key in required:

        if key not in timestamps:
            return False

        values.append(timestamps[key])

    return (max(values) - min(values)) <= max_delta

# MQTT message processing pipeline
def parse_topic(topic: str):

    parts = topic.split("/")

    return {
        "factory": parts[0],
        "machine": parts[1],
        "aspect": parts[2],
        "sensor": parts[3],
        "metric": parts[4]
    }

# Process incoming MQTT messages, extract features, and write to InfluxDB
def parse_payload(payload: str):
    try:
        data = json.loads(payload)
        return data
    except:
        return None

# Main processing function for MQTT messages
# Depending on the aspect (vibration, current, scalar), it extracts features, updates state, and calls the ML model when enough data is available
def process_message(topic: str, payload: str):

    info = parse_topic(topic)

    machine = info["machine"]
    aspect = info["aspect"]
    metric = info["metric"]
    # Vibration pipeline to handles chunked vibration data, reconstructs the signal, extracts features, and calls the ML model when all chunks are received
    if aspect == "vibration":
        data = parse_payload(payload)

        if not isinstance(data, dict):
            return

        if not all(k in data for k in ["s", "c", "d"]):
            return

        key = f"{machine}_{metric}"

        if key not in chunk_buffers:
            chunk_buffers[key] = np.zeros(1024, dtype=np.int16)
            chunk_meta[key] = np.zeros(1024, dtype=bool)

        s = data["s"]
        c = data["c"]
        d = data["d"]
        print(f"{metric}: {s}-{s+c}")

        chunk_buffers[key][s:s+c] = d
        chunk_meta[key][s:s+c] = True
        print(np.sum(chunk_meta[key]))
        

        if len(d) != c:
            return

        # If last chunk
        if np.all(chunk_meta[key]):
            vib = chunk_buffers[key]

            process_vibration(machine, metric, vib)

            del chunk_buffers[key]
            del chunk_meta[key]        

    # Current pipeline to handle current data, extract features like mean and imbalance, and update state for synchronization with vibration features
    elif aspect == "current":

        value = parse_payload(payload)

        if not isinstance(value, list) or len(value) != 3:
            return

        try:
            ia, ib, ic = [float(v) for v in value]
        except:
            return

        mean_current = np.mean([ia, ib, ic])
        max_current = np.max([ia, ib, ic])
        imbalance = max_current - min([ia, ib, ic])

        write_feature(machine, "current_a", ia)
        write_feature(machine, "current_b", ib)
        write_feature(machine, "current_c", ic)

        write_feature(machine, "current_mean", mean_current)
        write_feature(machine, "current_imbalance", imbalance)

        update_state(machine, "current_mean", mean_current)
        update_state(machine, "current_imbalance", imbalance)

    # Scalar pipeline to handle scalar metrics like RPM and temperature, write features, and update state for synchronization
    else:
        value = parse_payload(payload)

        if not isinstance(value, (int, float)):
            return

        value = float(value)

        write_feature(machine, metric, value)

        # STATE UPDATE
        if metric == "rpm":
            update_state(machine, "rpm", value)

        if metric in ["tempC", "temperature"]:
            update_state(machine, "temperature", value)

# Main function to process vibration data, extract features, and call the ML model when all required features are synchronized
def process_vibration(machine, axis, vib):
    raw_max = np.max(vib)
    raw_min = np.min(vib)

    print("RAW MAX:", raw_max)
    print("RAW MIN:", raw_min)
    vib = np.asarray(vib, dtype=float) / 500
    print("SCALED MAX:", np.max(vib))
    print("SCALED MIN:", np.min(vib))
    rms_val = rms(vib)
    fft_val = fft_peak(vib)
    psd_val = psd_peak(vib)
    energy = spectral_energy(vib)
    write_feature(machine, f"{axis}_rms", rms_val)
    write_feature(machine, f"{axis}_fft_peak", fft_val)
    write_feature(machine, f"{axis}_psd_peak", psd_val)

    update_state(machine, f"{axis}_rms", rms_val)
    update_state(machine, f"{axis}_fft_peak", fft_val)
    update_state(machine, f"{axis}_psd_peak", psd_val)

    fft_vals = calculate_fft(vib)
    freqs = np.linspace(0, SAMPLING_FREQ / 2, len(fft_vals))

    # Downsample FFT 
    #step = 4
    #fft_vals = fft_vals[::step]
    #freqs = freqs[::step]

    # Filter frequencies up to 500 Hz
    mask = freqs <= 500
    freqs = freqs[mask]
    fft_vals = fft_vals[mask]

    # Top-N frequency components
    #N = 20
    #idx = np.argsort(fft_vals)[-N:]
    #idx = idx[np.argsort(freqs[idx])]

    freqs_top = freqs#[idx]
    amps_top = fft_vals#[idx]

    write_fft(machine, axis, freqs_top, amps_top)
    
    current_imbalance = get_state(machine, "current_imbalance")
    current_mean = get_state(machine, "current_mean")
    rpm = get_state(machine, "rpm")
    tempC = get_state(machine, "temperature")
    vibX_fft_peak = get_state(machine, "vibX_fft_peak")
    vibX_rms = get_state(machine, "vibX_rms")
    vibX_psd_peak = get_state(machine, "vibX_psd_peak")
    vibY_fft_peak = get_state(machine, "vibY_fft_peak")
    vibY_rms = get_state(machine, "vibY_rms")
    vibY_psd_peak = get_state(machine, "vibY_psd_peak")
    vibZ_fft_peak = get_state(machine, "vibZ_fft_peak")
    vibZ_rms = get_state(machine, "vibZ_rms")
    vibZ_psd_peak = get_state(machine, "vibZ_psd_peak")
    print("CURRENT IMBALANCE:", current_imbalance)
    print("CURRENT MEAN:", current_mean)
    print("RPM:", rpm)
    print("TEMPERATURE:", tempC)
    print("VIBX FFT PEAK:", vibX_fft_peak)
    print("VIBX RMS:", vibX_rms)
    print("VIBX PSD PEAK:", vibX_psd_peak)
    if None in [current_imbalance, current_mean, rpm, tempC, vibX_fft_peak, vibX_rms, vibY_fft_peak, vibY_rms, vibZ_fft_peak, vibZ_rms]:
        return

    if not features_are_synchronized(machine):
        print(f"[SYNC ERROR] Feature timestamps too far apart")
        return

    feature_vector = [current_imbalance, current_mean, rpm, tempC, vibX_fft_peak, vibX_rms, vibY_fft_peak, vibY_rms, vibZ_fft_peak, vibZ_rms]

    print("FEATURE VECTOR:", feature_vector)
    print("RPM:", rpm, "CURRENT:", current_mean)
    
    # Call the ML model to get predictions based on the extracted features, and write the results back to InfluxDB
    result = predict(feature_vector)
    print("RESULT:", result)
    if result is None:
        return

    write_prediction(machine, "combined", result["score"])

    write_feature(machine, "anomaly_severity", result["severity"])
    write_feature(machine, "is_anomaly", int(result["is_anomaly"]))
    write_feature(machine, "health", result["health"])
    write_feature_state(machine, "state", result["state"])
    if result["rul"] is not None:
        write_feature(machine, "rul", result["rul"])
    write_feature_state(machine, "classifier_predicted_state", result["predicted_state"])
    write_feature(machine, "classifier_confidence", result["confidence"])
    for state_name, prob in result["state_probabilities"].items():

        write_feature(machine, f"classifier_{state_name}", prob)