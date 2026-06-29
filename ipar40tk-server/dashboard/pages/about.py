# This page provides an overview of the OpenMAPS project.

import dash
from dash import dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/about")

layout = dbc.Container([

    dcc.Markdown(r"""

# OpenMAPS

OpenMAPS (Machine Analyzator and Processing System) is an Industrial IoT platform developed for machine condition monitoring, anomaly detection and predictive maintenance research.

The system combines real-time telemetry acquisition, vibration analysis, machine learning based diagnostics and web-based visualization into a single integrated architecture.

---

## 1. Project Overview

The primary objective of OpenMAPS is to demonstrate how modern Industry 4.0 technologies can be applied to monitor industrial equipment and estimate machine health in real time.

The platform continuously collects operational data from multiple sensors, processes the incoming signals, extracts diagnostic features and evaluates the machine condition using machine learning models.

Project repository:

https://github.com/bmetk/IoT-Based-Industrial-Data-Collection_2026

Main capabilities:

- Real-time MQTT telemetry collection
- Time-series storage using InfluxDB
- Vibration-based condition monitoring
- Automatic anomaly detection
- Operating state classification
- Machine health estimation
- Remaining Useful Life (RUL) prediction
- Interactive web dashboard

---

## 2. Data Acquisition

The data acquisition layer is built around a distributed ESP32-based sensor network.

Two ESP devices are responsible for collecting machine telemetry:

### ESP1

Measures:

- Spindle speed (RPM)
- Motor current
- Temperature
- System status information

### ESP2

Measures:

- Three-axis vibration signals
- MPU9250 accelerometer data
- Sensor health information

The devices communicate through MQTT and publish measurements to the central broker.                

The backend services subscribe to these topics, validate incoming messages and store the data in InfluxDB for further analysis.

---

## 3. Signal Processing and Feature Extraction

Raw vibration measurements alone are difficult to interpret directly. Therefore, OpenMAPS extracts a set of statistical and frequency-domain features from each vibration window.

For every vibration axis (X, Y and Z), a 1024-sample signal is reconstructed from eight consecutive MQTT chunks.

### Root Mean Square (RMS)

RMS represents the overall vibration energy:

$$
RMS =\sqrt{\frac{1}{N}\sum_{i=1}^{N}x_i^2}
$$

Higher RMS values generally indicate increased vibration intensity and possible mechanical degradation.

### Fast Fourier Transform (FFT)

Frequency-domain analysis is performed using the Fast Fourier Transform:

$$
X(k) = \sum_{n=0}^{N-1} x(n)e^{-j2\pi kn/N}
$$

The dominant FFT peak is used to identify characteristic vibration frequencies associated with machine operation and faults.

### Power Spectral Density (PSD)

The Power Spectral Density estimates how vibration energy is distributed across frequencies.

PSD analysis helps identify resonances, rotating imbalance and bearing-related defects.

### Current Features

Motor current measurements are transformed into:

- Mean current: 
$$ 
I_{mean}=\frac{I_1+I_2+I_3}{3} 
$$
- Current imbalance: 
$$ 
I_{imbalance}=\max(I)-\min(I) 
$$


These features provide additional information about machine loading conditions.

### Feature Vector

The final feature vector contains:

- Current imbalance
- Mean current
- RPM
- Temperature
- Vibration FFT peaks (X, Y, Z)
- Vibration RMS values (X, Y, Z)

These features form the input for the machine learning subsystem.

---

## 4. Machine Learning and Predictive Analytics

The machine learning pipeline operates on the extracted feature vectors.

### Operating State Classification

A supervised classification model is trained using labelled machine states.

The classifier predicts one of nine operating conditions:

| Speed | Load |
|---------|---------|
| Low RPM | Idle |
| Low RPM | Low Stress |
| Low RPM | High Stress |
| Mid RPM | Idle |
| Mid RPM | Low Stress |
| Mid RPM | High Stress |
| High RPM | Idle |
| High RPM | Low Stress |
| High RPM | High Stress |

The classifier also provides confidence scores for all possible states, allowing the operator to evaluate classification certainty.

### Anomaly Detection

Each operating state has its own baseline model.

Incoming feature vectors are compared against the learned baseline and an anomaly score is calculated.

Higher anomaly scores indicate larger deviations from normal machine behaviour.

### Health Indicator

The anomaly score is converted into a normalized health metric:

- 100% = healthy machine
- 0% = severe degradation

This metric provides an intuitive representation of machine condition.

### Remaining Useful Life (RUL)

The platform estimates Remaining Useful Life (RUL) using degradation trends observed in historical data.

The RUL estimate represents the predicted time remaining before the machine reaches a critical condition threshold.

### Predictive Maintenance Workflow

1. Sensor acquisition
2. MQTT transmission
3. Data storage in InfluxDB
4. Feature extraction
5. State classification
6. Anomaly detection
7. Health estimation
8. RUL prediction
9. Dashboard visualization

---

## System Architecture
The OpenMAPS architecture consists of the following components:
- **ESP32 Sensor Network**: Collects telemetry data and publishes it via MQTT.
- **MQTT Broker**: Central communication hub for sensor data.
- **Data Ingestion Service**: Subscribes to MQTT topics, validates messages and stores data in InfluxDB.
- **Feature Extraction Service**: Processes raw data to compute diagnostic features.
- **Machine Learning Service**: Performs state classification, anomaly detection and health estimation.
- **Web Dashboard**: Provides real-time visualization and user interaction.
""",mathjax=True)
], fluid=True)
