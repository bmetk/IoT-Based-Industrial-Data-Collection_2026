import numpy as np
import numpy.typing as npt
from scipy import signal
from scipy.fft import rfft
from influx_client import *
from ml_model import predict
import json

SAMPLING_FREQ = 1000

Array = npt.NDArray[np.float64]


def rms(vib: Array) -> float:
    vib = np.asarray(vib, dtype=float)
    return np.sqrt(np.mean(vib ** 2))


def fft_peak(vib: Array) -> float:
    vib = np.asarray(vib, dtype=float)
    windowed = vib * signal.windows.hamming(vib.size)
    spectrum = np.abs(rfft(windowed))
    return float(np.max(spectrum))


def calculate_fft(vib: Array) -> list[float]:
    """Return FFT amplitude spectrum."""
    windowed = vib * signal.windows.hamming(vib.size)

    spectrum = np.abs(rfft(windowed))
    spectrum = 2.0 / vib.size * spectrum

    return spectrum.tolist()


def calculate_rms(vib: Array) -> float:
    """Alias for RMS calculation."""
    return rms(vib)


def get_psd(vib: Array) -> tuple[list[float], list[float]]:
    """Power spectral density using periodogram."""
    f, psd = signal.periodogram(vib, fs=SAMPLING_FREQ, window="hamming")
    return f.tolist(), psd.tolist()

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
def process_message(topic: str, payload: str):

    info = parse_topic(topic)

    machine = info["machine"]
    aspect = info["aspect"]
    metric = info["metric"]

    # vibration pipeline
    if aspect == "vibration":
        vib = parse_payload(payload)

        if not vib or not isinstance(vib, list):
            return

        vib = np.asarray(vib, dtype=float)

        rms_val = rms(vib)
        fft_val = fft_peak(vib)

        write_feature(machine, "vibration_rms", rms_val)
        write_feature(machine, "vibration_fft_peak", fft_val)

        fft_vals = calculate_fft(vib)
        freqs = np.linspace(0, SAMPLING_FREQ / 2, len(fft_vals))
        # Downsample
        fft_vals = fft_vals[::4]
        freqs = freqs[::4]
        mask = freqs <= 200
        freqs = freqs[mask]
        fft_vals = np.array(fft_vals)[mask]
        idx = np.argsort(fft_vals)[-20:]
        freqs = freqs[idx]
        fft_vals = np.array(fft_vals)[idx]

        write_fft(machine, metric, freqs, fft_vals)

        score = predict([rms_val, fft_val], "vibration")

        if score is not None:
            write_prediction(machine, "vibration", score)

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

        score = predict([mean_current, max_current, imbalance], "current")

        if score is not None:
            write_prediction(machine, "current", score)

    # Scalar sensors
    else:
        value = parse_payload(payload)

        if not isinstance(value, (int, float)):
            return

        value = float(value)

        write_feature(machine, metric, value)

        score = predict([value], "scalar")

        if score is not None:
            write_prediction(machine, aspect, score)